from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..financial_reports_service import (
    balance_sheet,
    cash_flow,
    profit_and_loss,
    to_csv,
    trial_balance,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/financial-reports", tags=["Financial Reports"])


@router.get("/trial-balance")
async def get_trial_balance(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    rows = await trial_balance(session, date_from, date_to)
    total_debit = sum(r["debit"] for r in rows)
    total_credit = sum(r["credit"] for r in rows)
    return {"data": rows, "total_debit": round(total_debit, 2), "total_credit": round(total_credit, 2), "count": len(rows)}


@router.get("/trial-balance/export")
async def export_trial_balance(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    format: str = "csv",
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    rows = await trial_balance(session, date_from, date_to)
    content, filename = to_csv(rows, "trial_balance.csv")
    return PlainTextResponse(content, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/profit-loss")
async def get_profit_loss(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    return await profit_and_loss(session, date_from, date_to)


@router.get("/profit-loss/export")
async def export_profit_loss(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    format: str = "csv",
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    data = await profit_and_loss(session, date_from, date_to)
    content, filename = to_csv(data, "profit_loss.csv")
    return PlainTextResponse(content, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/balance-sheet")
async def get_balance_sheet(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    as_of_date: Annotated[Optional[date], Query()] = None,
):
    return await balance_sheet(session, as_of_date)


@router.get("/balance-sheet/export")
async def export_balance_sheet(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    format: str = "csv",
    as_of_date: Annotated[Optional[date], Query()] = None,
):
    data = await balance_sheet(session, as_of_date)
    content, filename = to_csv(data, "balance_sheet.csv")
    return PlainTextResponse(content, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/cash-flow")
async def get_cash_flow(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    return await cash_flow(session, date_from, date_to)


@router.get("/cash-flow/export")
async def export_cash_flow(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    format: str = "csv",
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    data = await cash_flow(session, date_from, date_to)
    content, filename = to_csv(data, "cash_flow.csv")
    return PlainTextResponse(content, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/summary")
async def reports_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    tb = await trial_balance(session)
    pl = await profit_and_loss(session)
    bs = await balance_sheet(session)
    cf = await cash_flow(session)
    return {"trial_balance": {"accounts": len(tb), "total_debit": sum(r["debit"] for r in tb), "total_credit": sum(r["credit"] for r in tb)}, "profit_loss": pl, "balance_sheet": bs, "cash_flow": cf}
