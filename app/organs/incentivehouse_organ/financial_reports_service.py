from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BnkStaging, SalStaging, PurStaging, EvnStaging, EnvStaging
from .models_production import SalesInvoice, PurchaseOrder, VendorInvoice, Event


async def trial_balance(
    session: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    """Aggregate debit/credit by account_code across all 5 staging tables."""
    stages = [
        ("BNK", BnkStaging),
        ("SAL", SalStaging),
        ("PUR", PurStaging),
        ("EVN", EvnStaging),
        ("ENV", EnvStaging),
    ]
    rows: list[dict] = []
    for module, model in stages:
        stmt = select(
            model.account_code,
            func.coalesce(func.sum(model.debit_amount), 0).label("total_debit"),
            func.coalesce(func.sum(model.credit_amount), 0).label("total_credit"),
        )
        filters = []
        if date_from:
            filters.append(model.transaction_date >= date_from.isoformat())
        if date_to:
            filters.append(model.transaction_date <= date_to.isoformat())
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.group_by(model.account_code)
        result = await session.execute(stmt)
        for code, debit, credit in result:
            rows.append({
                "account_code": code,
                "account_name": code,
                "debit": float(debit),
                "credit": float(credit),
                "balance": round(float(debit) - float(credit), 2),
                "module": module,
            })
    return rows


async def profit_and_loss(
    session: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Compute revenue vs expenses from staging + production tables."""
    rev_debit, rev_credit = await _module_totals(session, SalStaging, date_from, date_to)
    exp_debit, exp_credit = await _module_totals(session, PurStaging, date_from, date_to)

    sales_total = 0.0
    stmt = select(func.coalesce(func.sum(SalesInvoice.total), 0))
    filters = []
    if date_from:
        filters.append(SalesInvoice.invoice_date >= date_from)
    if date_to:
        filters.append(SalesInvoice.invoice_date <= date_to)
    if filters:
        stmt = stmt.where(*filters)
    sales_total = float((await session.execute(stmt)).scalar() or 0)

    purchase_total = 0.0
    stmt = select(func.coalesce(func.sum(PurchaseOrder.total), 0))
    filters = []
    if date_from:
        filters.append(PurchaseOrder.po_date >= date_from)
    if date_to:
        filters.append(PurchaseOrder.po_date <= date_to)
    if filters:
        stmt = stmt.where(*filters)
    purchase_total = float((await session.execute(stmt)).scalar() or 0)

    event_revenue = 0.0
    stmt = select(func.coalesce(func.sum(Event.gross_sales), 0))
    filters = []
    if date_from:
        filters.append(Event.event_date >= date_from)
    if date_to:
        filters.append(Event.event_date <= date_to)
    if filters:
        stmt = stmt.where(*filters)
    event_revenue = float((await session.execute(stmt)).scalar() or 0)

    gross_revenue = sales_total + event_revenue
    gross_profit = gross_revenue - purchase_total

    return {
        "period": {"from": date_from.isoformat() if date_from else "all", "to": date_to.isoformat() if date_to else "all"},
        "revenue": {"sales_invoices": sales_total, "event_revenue": event_revenue, "total_revenue": round(gross_revenue, 2)},
        "expenses": {"purchases": purchase_total, "total_expenses": round(purchase_total, 2)},
        "gross_profit": round(gross_profit, 2),
        "profit_margin": round((gross_profit / gross_revenue * 100), 2) if gross_revenue else 0,
    }


async def balance_sheet(
    session: AsyncSession,
    as_of_date: Optional[date] = None,
) -> dict:
    """Compute assets, liabilities, equity from staging + production tables."""
    as_of = as_of_date or date.today()

    assets = 0.0
    stmt = select(func.coalesce(func.sum(SalesInvoice.total - SalesInvoice.paid_amount), 0))
    stmt = stmt.where(SalesInvoice.status.in_(["OPEN", "PARTIAL"]))
    assets += float((await session.execute(stmt)).scalar() or 0)

    stmt = select(func.coalesce(func.sum(BnkStaging.debit_amount - BnkStaging.credit_amount), 0))
    stmt = stmt.where(BnkStaging.transaction_date <= as_of.isoformat())
    assets += float((await session.execute(stmt)).scalar() or 0)

    liabilities = 0.0
    stmt = select(func.coalesce(func.sum(VendorInvoice.total - VendorInvoice.paid_amount), 0))
    stmt = stmt.where(VendorInvoice.status.in_(["OPEN", "PARTIAL"]))
    liabilities += float((await session.execute(stmt)).scalar() or 0)

    equity = 0.0
    stmt = select(func.coalesce(func.sum(PurStaging.debit_amount - PurStaging.credit_amount), 0))
    equity += float((await session.execute(stmt)).scalar() or 0)
    stmt = select(func.coalesce(func.sum(SalStaging.credit_amount - SalStaging.debit_amount), 0))
    equity += float((await session.execute(stmt)).scalar() or 0)

    return {
        "as_of_date": as_of.isoformat(),
        "assets": {"accounts_receivable": round(assets, 2), "cash_and_bank": 0, "total_assets": round(assets, 2)},
        "liabilities": {"accounts_payable": round(liabilities, 2), "total_liabilities": round(liabilities, 2)},
        "equity": {"retained_earnings": round(equity, 2), "total_equity": round(equity, 2)},
        "total_liabilities_equity": round(liabilities + equity, 2),
    }


async def cash_flow(
    session: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Operating / Investing / Financing cash flow from staging tables."""
    op_in = 0.0
    stmt = select(func.coalesce(func.sum(SalStaging.credit_amount), 0))
    filters = [SalStaging.credit_amount > 0]
    if date_from:
        filters.append(SalStaging.transaction_date >= date_from.isoformat())
    if date_to:
        filters.append(SalStaging.transaction_date <= date_to.isoformat())
    stmt = stmt.where(*filters)
    op_in = float((await session.execute(stmt)).scalar() or 0)

    op_out = 0.0
    stmt = select(func.coalesce(func.sum(PurStaging.debit_amount), 0))
    filters = [PurStaging.debit_amount > 0]
    if date_from:
        filters.append(PurStaging.transaction_date >= date_from.isoformat())
    if date_to:
        filters.append(PurStaging.transaction_date <= date_to.isoformat())
    stmt = stmt.where(*filters)
    op_out = float((await session.execute(stmt)).scalar() or 0)

    bnk_net = 0.0
    stmt = select(func.coalesce(func.sum(BnkStaging.debit_amount - BnkStaging.credit_amount), 0))
    filters = []
    if date_from:
        filters.append(BnkStaging.transaction_date >= date_from.isoformat())
    if date_to:
        filters.append(BnkStaging.transaction_date <= date_to.isoformat())
    if filters:
        stmt = stmt.where(*filters)
    bnk_net = float((await session.execute(stmt)).scalar() or 0)

    return {
        "period": {"from": date_from.isoformat() if date_from else "all", "to": date_to.isoformat() if date_to else "all"},
        "operating": {"cash_in": round(op_in, 2), "cash_out": round(op_out, 2), "net": round(op_in - op_out, 2)},
        "investing": {"description": "Bank transactions (net)", "net": round(bnk_net, 2)},
        "financing": {"description": "Not computed from staging data", "net": 0},
        "net_change": round((op_in - op_out) + bnk_net, 2),
    }


async def _module_totals(
    session: AsyncSession,
    model,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[float, float]:
    stmt = select(
        func.coalesce(func.sum(model.debit_amount), 0),
        func.coalesce(func.sum(model.credit_amount), 0),
    )
    filters = []
    if date_from:
        filters.append(model.transaction_date >= date_from.isoformat())
    if date_to:
        filters.append(model.transaction_date <= date_to.isoformat())
    if filters:
        stmt = stmt.where(*filters)
    result = await session.execute(stmt)
    row = result.one()
    return float(row[0] or 0), float(row[1] or 0)


def to_csv(data: Any, filename: str = "report.csv") -> tuple[str, str]:
    output = io.StringIO()
    writer = csv.writer(output)

    if isinstance(data, dict):
        writer.writerow(data.keys())
        writer.writerow(data.values())
    elif isinstance(data, list) and data:
        writer.writerow(data[0].keys())
        for row in data:
            writer.writerow(row.values())
    return output.getvalue(), filename
