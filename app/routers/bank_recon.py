from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models import (
    BankReconciliation,
    BankImportSession,
    BankStaging,
    BankUnmatched,
    BankAccount,
)

router = APIRouter(prefix="/api/v1/bank-reconciliation", tags=["Bank Reconciliation"])


class ReconciliationCreate(BaseModel):
    bank_account_id: int
    statement_balance: float
    system_balance: float


class MatchPayload(BaseModel):
    notes: str | None = None


@router.get("/accounts")
async def list_bank_accounts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.read")),
):
    result = await db.execute(select(BankAccount).where(BankAccount.is_active))
    return [
        {
            "id": a.id,
            "account_name": a.account_name,
            "bank_name": a.bank_name,
            "account_number": a.account_number,
            "currency": a.currency,
            "current_balance": a.current_balance,
        }
        for a in result.scalars().all()
    ]


@router.get("/sessions")
async def list_import_sessions(
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.read")),
):
    query = (
        select(BankImportSession)
        .order_by(BankImportSession.import_date.desc())
        .limit(limit)
    )
    if status:
        query = query.where(BankImportSession.status == status)
    result = await db.execute(query)
    sessions = result.scalars().all()
    data = []
    for s in sessions:
        ba = await db.get(BankAccount, s.bank_account_id) if s.bank_account_id else None
        data.append({
            "id": s.id,
            "bank_account": ba.account_name if ba else None,
            "file_name": s.file_name,
            "total_transactions": s.total_transactions,
            "matched_count": s.matched_count,
            "unmatched_count": s.unmatched_count,
            "status": s.status,
            "import_date": s.import_date.isoformat() if s.import_date else None,
        })
    return data


@router.get("/sessions/{session_id}/transactions")
async def list_session_transactions(
    session_id: int,
    matched: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.read")),
):
    sess = await db.get(BankImportSession, session_id)
    if not sess:
        raise HTTPException(404, detail="Import session not found")

    base_filter = BankStaging.session_id == session_id
    query = select(BankStaging).where(base_filter)
    count_query = select(func.count()).select_from(BankStaging).where(base_filter)

    if matched is not None:
        query = query.where(BankStaging.is_matched == matched)
        count_query = count_query.where(BankStaging.is_matched == matched)

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(BankStaging.transaction_date.desc())
        .offset(offset)
        .limit(page_size)
    )
    return {
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": t.id,
                "transaction_date": t.transaction_date.isoformat()
                if t.transaction_date
                else None,
                "description": t.description,
                "debit_amount": t.debit_amount,
                "credit_amount": t.credit_amount,
                "reference": t.reference,
                "is_matched": t.is_matched,
            }
            for t in result.scalars().all()
        ],
    }


@router.get("/reconciliations")
async def list_reconciliations(
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.read")),
):
    query = (
        select(BankReconciliation)
        .order_by(BankReconciliation.session_date.desc())
        .limit(limit)
    )
    if status:
        query = query.where(BankReconciliation.status == status)
    result = await db.execute(query)
    return [
        {
            "id": r.id,
            "session_date": r.session_date.isoformat() if r.session_date else None,
            "bank_account_id": r.bank_account_id,
            "statement_balance": r.statement_balance,
            "system_balance": r.system_balance,
            "difference": r.difference,
            "status": r.status,
        }
        for r in result.scalars().all()
    ]


@router.post("/reconciliations")
async def create_reconciliation(
    req: ReconciliationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.create")),
):
    if not await db.get(BankAccount, req.bank_account_id):
        raise HTTPException(404, detail="Bank account not found")

    difference = round(req.statement_balance - req.system_balance, 2)
    recon = BankReconciliation(
        bank_account_id=req.bank_account_id,
        statement_balance=req.statement_balance,
        system_balance=req.system_balance,
        difference=difference,
        status="IN_PROGRESS",
    )
    db.add(recon)
    await db.commit()
    await db.refresh(recon)
    return {
        "id": recon.id,
        "session_date": recon.session_date.isoformat() if recon.session_date else None,
        "bank_account_id": recon.bank_account_id,
        "statement_balance": recon.statement_balance,
        "system_balance": recon.system_balance,
        "difference": recon.difference,
        "status": recon.status,
    }


@router.get("/reconciliations/{recon_id}")
async def get_reconciliation(
    recon_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.read")),
):
    recon = await db.get(BankReconciliation, recon_id)
    if not recon:
        raise HTTPException(404, detail="Reconciliation not found")
    return {
        "id": recon.id,
        "session_date": recon.session_date.isoformat() if recon.session_date else None,
        "bank_account_id": recon.bank_account_id,
        "statement_balance": recon.statement_balance,
        "system_balance": recon.system_balance,
        "difference": recon.difference,
        "status": recon.status,
        "created_at": recon.created_at.isoformat() if recon.created_at else None,
    }


@router.post("/reconciliations/{recon_id}/approve")
async def approve_reconciliation(
    recon_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.approve")),
):
    recon = await db.get(BankReconciliation, recon_id)
    if not recon:
        raise HTTPException(404, detail="Reconciliation not found")
    if recon.status != "IN_PROGRESS":
        raise HTTPException(
            400, detail=f"Cannot approve. Current status: {recon.status}"
        )
    recon.status = "APPROVED"
    await db.commit()
    return {"id": recon.id, "status": "APPROVED"}


@router.post("/sessions/{session_id}/match/{staging_id}")
async def match_transaction(
    session_id: int,
    staging_id: int,
    payload: MatchPayload | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.match")),
):
    staging = await db.get(BankStaging, staging_id)
    if not staging or staging.session_id != session_id:
        raise HTTPException(404, detail="Transaction not found in this session")
    if staging.is_matched:
        raise HTTPException(400, detail="Transaction already matched")

    staging.is_matched = True
    sess = await db.get(BankImportSession, session_id)
    if sess:
        sess.matched_count = (sess.matched_count or 0) + 1
        sess.unmatched_count = max(0, (sess.unmatched_count or 0) - 1)
        if sess.matched_count >= sess.total_transactions:
            sess.status = "MATCHED"

    await db.commit()
    return {"id": staging.id, "is_matched": True}


@router.post("/sessions/{session_id}/unmatch/{staging_id}")
async def unmatch_transaction(
    session_id: int,
    staging_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.match")),
):
    staging = await db.get(BankStaging, staging_id)
    if not staging or staging.session_id != session_id:
        raise HTTPException(404, detail="Transaction not found in this session")
    if not staging.is_matched:
        raise HTTPException(400, detail="Transaction is not matched")

    staging.is_matched = False
    sess = await db.get(BankImportSession, session_id)
    if sess:
        sess.matched_count = max(0, (sess.matched_count or 0) - 1)
        sess.unmatched_count = (sess.unmatched_count or 0) + 1
        sess.status = "PARTIAL"

    await db.commit()
    return {"id": staging.id, "is_matched": False}


@router.get("/stats")
async def get_bank_recon_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("bank_reconciliation.read")),
):
    total_sessions = await db.scalar(select(func.count(BankImportSession.id)))
    total_txns = await db.scalar(select(func.count(BankStaging.id)))
    matched = await db.scalar(
        select(func.count(BankStaging.id)).where(BankStaging.is_matched)
    )
    unmatched = await db.scalar(
        select(func.count(BankStaging.id)).where(BankStaging.is_matched == False)
    )
    total_recons = await db.scalar(select(func.count(BankReconciliation.id)))
    approved_recons = await db.scalar(
        select(func.count(BankReconciliation.id)).where(
            BankReconciliation.status == "APPROVED"
        )
    )
    total_diff = await db.scalar(
        select(func.coalesce(func.sum(BankReconciliation.difference), 0))
    )

    return {
        "total_import_sessions": total_sessions or 0,
        "total_transactions": total_txns or 0,
        "matched_transactions": matched or 0,
        "unmatched_transactions": unmatched or 0,
        "match_rate": round((matched or 0) / (total_txns or 1) * 100, 2),
        "total_reconciliations": total_recons or 0,
        "approved_reconciliations": approved_recons or 0,
        "total_difference_egp": round(total_diff or 0, 2),
    }
