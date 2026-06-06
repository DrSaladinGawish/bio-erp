"""
dashboard.py
Real-time dashboard data API for IHE-ERP.
Returns 9 KPIs (revenue, expenses, PNRs, bank balance, etc.) and
monthly series for charts. Supports date-range filters: 7D/30D/90D/YTD/Custom.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.db import get_db

logger = logging.getLogger("incentivehouse_organ.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# Allowed table names for safe SQL (whitelist to prevent injection)
_TABLES = {
    "sales": "sales_invoice",
    "purchases": "purchase_voucher",
    "bank": "bank_transaction",
    "pnr": "pnr_master",
    "events": "events",
}


def _resolve_range(range_: str, start: Optional[str], end: Optional[str]) -> dict:
    today = datetime.now().date()
    end_d = today
    if range_ == "7D":
        start_d = today - timedelta(days=7)
    elif range_ == "30D":
        start_d = today - timedelta(days=30)
    elif range_ == "90D":
        start_d = today - timedelta(days=90)
    elif range_ == "YTD":
        start_d = datetime(today.year, 1, 1).date()
    elif range_ == "CUSTOM" and start and end:
        try:
            start_d = datetime.strptime(start, "%Y-%m-%d").date()
            end_d = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            start_d = today - timedelta(days=30)
    else:
        start_d = datetime(today.year, 1, 1).date()
    return {"start": start_d.isoformat(), "end": end_d.isoformat()}


def _safe_sum(db: Session, table: str, col: str, where: str = "1=1") -> float:
    if table not in _TABLES.values():
        return 0.0
    try:
        row = db.execute(text(
            f"SELECT COALESCE(SUM({col}), 0) FROM {table} WHERE {where}"
        )).fetchone()
        return float(row[0] or 0) if row else 0.0
    except Exception as exc:
        logger.debug("_safe_sum(%s.%s) failed: %s", table, col, exc)
        return 0.0


def _safe_count(db: Session, table: str, where: str = "1=1") -> int:
    if table not in _TABLES.values():
        return 0
    try:
        return int(db.execute(text(
            f"SELECT COUNT(*) FROM {table} WHERE {where}"
        )).scalar() or 0)
    except Exception as exc:
        logger.debug("_safe_count(%s) failed: %s", table, exc)
        return 0


def _monthly_series(db: Session, table: str, date_col: str, amount_col: str,
                    start: str, end: str) -> list:
    try:
        rows = db.execute(text(
            f"SELECT MONTH({date_col}) as m, COALESCE(SUM({amount_col}), 0) "
            f"FROM {table} "
            f"WHERE {date_col} >= :start AND {date_col} <= :end "
            f"GROUP BY MONTH({date_col})"
        ), {"start": start, "end": end}).fetchall()
        m = {int(r[0]): float(r[1] or 0) for r in rows}
        return [round(m.get(mo, 0.0), 2) for mo in range(1, 13)]
    except Exception as exc:
        logger.debug("_monthly_series(%s) failed: %s", table, exc)
        return [0.0] * 12


@router.get("/data")
def dashboard_data(
    range: str = Query("YTD"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return all 9 KPIs + monthly series for the selected range.

    Range values: 7D, 30D, 90D, YTD, Custom (case-insensitive).
    Anything else returns 422.
    """
    range_clean = range.upper()
    if range_clean not in ("7D", "30D", "90D", "YTD", "CUSTOM"):
        raise HTTPException(status_code=422, detail=f"Invalid range: {range}")
    rng = _resolve_range(range_clean, start, end)
    s, e = rng["start"], rng["end"]
    sales_where = f"invoice_date >= '{s}' AND invoice_date <= '{e}'"
    pur_where = f"voucher_date >= '{s}' AND voucher_date <= '{e}'"
    bank_where = f"transaction_date >= '{s}' AND transaction_date <= '{e}'"

    total_revenue = _safe_sum(db, _TABLES["sales"], "total_amount", sales_where)
    total_expenses = _safe_sum(db, _TABLES["purchases"], "total_amount", pur_where)
    active_pnrs = _safe_count(
        db, _TABLES["pnr"],
        "status IN ('CONFIRMED','IN_PROGRESS','OPEN')"
    )
    bank_balance = _safe_sum(db, _TABLES["bank"], "amount", bank_where)
    pending_invoices = _safe_count(db, _TABLES["sales"], "status = 'PENDING'")
    total_vendors = _safe_count(db, "vendors")
    total_clients = _safe_count(db, "clients")

    revenu_by_month = _monthly_series(
        db, _TABLES["sales"], "invoice_date", "total_amount", s, e
    )
    expenses_by_month = _monthly_series(
        db, _TABLES["purchases"], "voucher_date", "total_amount", s, e
    )

    return {
        "range": range_clean,
        "start_date": s,
        "end_date": e,
        "total_revenue": round(total_revenue, 2),
        "total_expenses": round(total_expenses, 2),
        "net_profit": round(total_revenue - total_expenses, 2),
        "active_pnrs": active_pnrs,
        "bank_balance": round(bank_balance, 2),
        "pending_invoices": pending_invoices,
        "total_vendors": total_vendors,
        "total_clients": total_clients,
        "revenue_by_month": revenu_by_month,
        "expenses_by_month": expenses_by_month,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/export")
def dashboard_export(
    range: str = Query("YTD"),
    format: str = Query("json"),
    db: Session = Depends(get_db),
):
    """Export dashboard data as JSON or real PDF (IHE-ERP v2.3.5+)."""
    from fastapi.responses import Response
    fmt = format.lower()
    if fmt not in ("json", "pdf"):
        raise HTTPException(status_code=422, detail=f"Invalid format: {format}")
    data = dashboard_data(range=range, db=db)
    if fmt == "pdf":
        try:
            from app.organs.incentivehouse_organ.intelligence.pdf_generator import (
                generate_dashboard_pdf,
            )
            pdf_bytes = generate_dashboard_pdf(data, range)
            filename = (
                f"dashboard_{range}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                },
            )
        except Exception as exc:
            logger.warning("PDF generation failed: %s", exc)
            return {
                "format": "pdf",
                "status": "error",
                "message": f"PDF generation failed: {exc}",
                "data": data,
            }
    return {"format": "json", "data": data}
