"""
bnk_router.py — Banking router for IncentiveHouse-ERP
Full CRUD + running balance + reconciliation + statement import
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BankTransaction, BankAccount, User
from ..schemas.bnk_schemas import (
    BankTransactionCreate, BankTransactionUpdate, BankTransactionOut,
    BankTransactionListOut, BankBalanceOut, ReconciliationResult,
)
from ..services.bnk_service import BankingService
from ..auth import get_current_user, require_role
from ..templates import templates

router = APIRouter(prefix="/banking", tags=["banking"])


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    txn_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    svc = BankingService(db)
    txns, total = svc.list_transactions(
        account_id=account_id, date_from=date_from, date_to=date_to,
        txn_type=txn_type, page=page, per_page=per_page,
    )
    accounts = db.execute(select(BankAccount).order_by(BankAccount.account_name)).scalars().all()
    balances = {a.id: svc.get_balance(a.id) for a in accounts}
    return templates.TemplateResponse("banking_list.html", {
        "request": request, "transactions": txns, "accounts": accounts,
        "balances": balances, "account_id": account_id,
        "date_from": date_from, "date_to": date_to,
        "page": page, "per_page": per_page, "total": total,
        "current_user": current_user,
    })


@router.get("/api", response_model=BankTransactionListOut)
async def api_list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    svc = BankingService(db)
    txns, total = svc.list_transactions(
        account_id=account_id, date_from=date_from, date_to=date_to,
        page=page, per_page=per_page,
    )
    return {"items": txns, "total": total, "page": page, "per_page": per_page}


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/api", response_model=BankTransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: BankTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = BankingService(db)
    txn = svc.create(data, created_by=current_user.id)
    return txn


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/api/{id}", response_model=BankTransactionOut)
async def get_transaction(id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return BankingService(db).get_or_404(id)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/api/{id}", response_model=BankTransactionOut)
async def update_transaction(
    id: int,
    data: BankTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = BankingService(db)
    txn = svc.get_or_404(id)
    if txn.is_reconciled:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Reconciled transactions cannot be modified")
    return svc.update(txn, data, updated_by=current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/api/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    svc = BankingService(db)
    txn = svc.get_or_404(id)
    if txn.is_reconciled:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Reconciled transactions cannot be deleted")
    svc.delete(txn)


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/api/balance/{account_id}", response_model=BankBalanceOut)
async def get_balance(
    account_id: int,
    as_of: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc     = BankingService(db)
    account = db.get(BankAccount, account_id)
    if not account:
        raise HTTPException(404, "Bank account not found")
    balance = svc.get_balance(account_id, as_of=as_of)
    return {
        "account_id":   account_id,
        "account_name": account.account_name,
        "balance":      balance,
        "as_of":        as_of or date.today(),
        "currency":     account.currency_code,
    }


@router.get("/api/balances/all")
async def all_balances(
    as_of: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc      = BankingService(db)
    accounts = db.execute(select(BankAccount)).scalars().all()
    return [
        {
            "account_id":   a.id,
            "account_name": a.account_name,
            "account_number": a.account_number,
            "balance":      svc.get_balance(a.id, as_of=as_of),
            "currency":     a.currency_code,
        }
        for a in accounts
    ]


# ─────────────────────────────────────────────────────────────────────────────
# RECONCILIATION
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/api/reconcile/{account_id}", response_model=ReconciliationResult)
async def reconcile(
    account_id: int,
    statement_balance: Decimal = Query(...),
    statement_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("accountant", "manager", "admin")),
):
    svc = BankingService(db)
    return svc.reconcile(
        account_id=account_id,
        statement_balance=statement_balance,
        statement_date=statement_date,
        reconciled_by=current_user.id,
    )


@router.post("/api/reconcile/{account_id}/mark")
async def mark_reconciled(
    account_id: int,
    transaction_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("accountant", "manager", "admin")),
):
    svc = BankingService(db)
    count = svc.mark_reconciled(account_id, transaction_ids, user=current_user)
    return {"reconciled_count": count}


# ─────────────────────────────────────────────────────────────────────────────
# STATEMENT IMPORT
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/api/import/{account_id}")
async def import_statement(
    account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("accountant", "manager", "admin")),
):
    """Import bank statement CSV/OFX file and create transactions."""
    svc = BankingService(db)
    content = await file.read()
    result = svc.import_statement(
        account_id=account_id,
        content=content,
        filename=file.filename,
        imported_by=current_user.id,
    )
    return {
        "imported": result.imported_count,
        "skipped":  result.skipped_count,
        "errors":   result.errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RUNNING BALANCE (for statement view)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/api/statement/{account_id}")
async def get_statement(
    account_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns transactions with running balance column."""
    svc = BankingService(db)
    return svc.get_statement_with_running_balance(
        account_id=account_id, date_from=date_from, date_to=date_to
    )
