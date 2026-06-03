"""
BNK Router — Bank Reconciliation & Transaction API
IncentiveHouse ERP | Bio-ERP Organ Module
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import BNKTransaction
from ..schemas import (
    BNKTransactionCreate,
    BNKTransactionOut,
    BNKTransactionList,
    BNKDashboardSummary,
    BNKAccountSummary,
    BNKReconciliationStatus,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/bnk", tags=["BNK Bank Reconciliation"])


def _build_txn_query(
    account: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    txn_type: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    search: str | None = None,
    sub_ledger_code: str | None = None,
    pnr_id: int | None = None,
    is_reconciled: bool | None = None,
):
    stmt = select(BNKTransaction)
    filters = []
    if account:
        filters.append(BNKTransaction.account_code.ilike(f"%{account}%"))
    if date_from:
        filters.append(BNKTransaction.txn_date >= date_from)
    if date_to:
        filters.append(BNKTransaction.txn_date <= date_to)
    if txn_type:
        filters.append(BNKTransaction.txn_type.ilike(f"%{txn_type}%"))
    if min_amount is not None:
        filters.append(BNKTransaction.amount >= min_amount)
    if max_amount is not None:
        filters.append(BNKTransaction.amount <= max_amount)
    if sub_ledger_code:
        filters.append(BNKTransaction.sub_ledger_code == sub_ledger_code)
    if pnr_id is not None:
        filters.append(BNKTransaction.pnr_id == pnr_id)
    if is_reconciled is not None:
        filters.append(BNKTransaction.is_reconciled == is_reconciled)
    if search:
        search_filter = or_(
            BNKTransaction.description.ilike(f"%{search}%"),
            BNKTransaction.reference_no.ilike(f"%{search}%"),
            BNKTransaction.counterparty.ilike(f"%{search}%"),
            BNKTransaction.account_code.ilike(f"%{search}%"),
        )
        filters.append(search_filter)
    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt.order_by(desc(BNKTransaction.txn_date), desc(BNKTransaction.id))


@router.get(
    "/transactions",
    response_model=PaginatedResponse[BNKTransactionOut],
    summary="List bank transactions",
)
async def list_transactions(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    account: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    txn_type: Annotated[str | None, Query()] = None,
    min_amount: Annotated[float | None, Query()] = None,
    max_amount: Annotated[float | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    sub_ledger_code: Annotated[str | None, Query()] = None,
    pnr_id: Annotated[int | None, Query()] = None,
    is_reconciled: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = _build_txn_query(
        account, date_from, date_to, txn_type,
        min_amount, max_amount, search,
        sub_ledger_code, pnr_id, is_reconciled,
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[BNKTransactionOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/transactions/{transaction_id}", response_model=BNKTransactionOut)
async def get_transaction(
    transaction_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    result = await session.execute(
        select(BNKTransaction).where(BNKTransaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return BNKTransactionOut.model_validate(txn)


@router.post("/transactions", response_model=BNKTransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: BNKTransactionCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    txn = BNKTransaction(**payload.model_dump(exclude_unset=True))
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    return BNKTransactionOut.model_validate(txn)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    result = await session.execute(
        select(BNKTransaction).where(BNKTransaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await session.delete(txn)
    await session.commit()


@router.get("/accounts", response_model=list[BNKAccountSummary])
async def list_accounts(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    stmt = select(
        BNKTransaction.account_code,
        BNKTransaction.currency_code,
        func.count().label("txn_count"),
        func.sum(BNKTransaction.debit_amount).label("total_debit"),
        func.sum(BNKTransaction.credit_amount).label("total_credit"),
        func.sum(BNKTransaction.credit_amount - BNKTransaction.debit_amount).label("net_balance"),
        func.max(BNKTransaction.txn_date).label("last_txn_date"),
    ).group_by(BNKTransaction.account_code, BNKTransaction.currency_code
    ).order_by(BNKTransaction.account_code)
    rows = (await session.execute(stmt)).all()
    return [
        BNKAccountSummary(
            account_code=r.account_code,
            currency_code=r.currency_code or "EGP",
            txn_count=r.txn_count or 0,
            total_debit=round(r.total_debit or 0, 2),
            total_credit=round(r.total_credit or 0, 2),
            net_balance=round(r.net_balance or 0, 2),
            last_txn_date=r.last_txn_date,
        ) for r in rows if r.account_code
    ]


@router.get("/summary", response_model=BNKDashboardSummary)
async def get_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    stmt = select(
        func.count().label("total_count"),
        func.sum(BNKTransaction.debit_amount).label("total_debit"),
        func.sum(BNKTransaction.credit_amount).label("total_credit"),
        func.sum(BNKTransaction.credit_amount - BNKTransaction.debit_amount).label("net"),
        func.count().filter(BNKTransaction.is_reconciled == 1).label("reconciled_count"),
    )
    row = (await session.execute(stmt)).one()
    acct_r = await session.execute(
        select(BNKTransaction.account_code, func.count().label("cnt"))
        .group_by(BNKTransaction.account_code).order_by(desc("cnt"))
    )
    by_account = {r.account_code: r.cnt for r in acct_r.all() if r.account_code}
    type_r = await session.execute(
        select(BNKTransaction.txn_type, func.count().label("cnt"))
        .group_by(BNKTransaction.txn_type).order_by(desc("cnt"))
    )
    by_type = {r.txn_type: r.cnt for r in type_r.all() if r.txn_type}
    return BNKDashboardSummary(
        total_count=row.total_count or 0,
        total_debit=round(row.total_debit or 0, 2),
        total_credit=round(row.total_credit or 0, 2),
        net_balance=round(row.net or 0, 2),
        reconciled_count=row.reconciled_count or 0,
        unreconciled_count=(row.total_count or 0) - (row.reconciled_count or 0),
        by_account=by_account,
        by_type=by_type,
    )


@router.get("/reconciliation/status", response_model=BNKReconciliationStatus)
async def get_reconciliation_status(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    account: Annotated[str | None, Query()] = None,
):
    filters = []
    if account:
        filters.append(BNKTransaction.account_code == account)
    stmt = select(
        BNKTransaction.account_code,
        func.count().label("total"),
        func.count().filter(BNKTransaction.is_reconciled == 1).label("matched"),
        func.count().filter(BNKTransaction.is_reconciled == 0).label("unmatched"),
        func.count().filter(BNKTransaction.is_flagged == 1).label("flagged"),
        func.sum(BNKTransaction.debit_amount).label("debit"),
        func.sum(BNKTransaction.credit_amount).label("credit"),
    ).group_by(BNKTransaction.account_code)
    if filters:
        stmt = stmt.where(and_(*filters))
    rows = (await session.execute(stmt)).all()
    accounts = [
        {
            "account_code": r.account_code,
            "total": r.total,
            "matched": r.matched,
            "unmatched": r.unmatched,
            "flagged": r.flagged,
            "debit": round(r.debit or 0, 2),
            "credit": round(r.credit or 0, 2),
        } for r in rows if r.account_code
    ]
    total = sum(a["total"] for a in accounts)
    matched = sum(a["matched"] for a in accounts)
    return BNKReconciliationStatus(
        accounts=accounts,
        total=total,
        matched=matched,
        unmatched=total - matched,
        flagged=sum(a["flagged"] for a in accounts),
        match_rate=round(matched / total * 100, 2) if total else 0.0,
    )
