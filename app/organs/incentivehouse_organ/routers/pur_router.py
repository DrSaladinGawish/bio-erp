"""
PUR Router — Purchase Orders, Vendor Invoices & Procurement Metrics
====================================================================
End-points (prefix ``/api/v1/pur``):

  GET  /orders                     — list purchase orders (paginated)
  GET  /orders/{id}                — single PO with vendor-invoice summary
  POST /orders                     — create a new purchase order
  GET  /invoices                   — list vendor invoices
  GET  /invoices/{id}              — single vendor invoice
  POST /invoices                   — create a vendor invoice
  GET  /summary                    — PO / invoice / spend rollup
  GET  /by-event/{event_id}        — all POs + invoices for a given event
  GET  /by-vendor/{vendor_id}      — all POs + invoices for a given vendor
  GET  /top-vendors                — top-N vendors by spend
  GET  /spend-by-month             — monthly spend series
  GET  /aging-report               — vendor-invoice aging buckets
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_production import (
    PurchaseOrder, VendorInvoice, Vendor,
)
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pur", tags=["PUR Purchase"])


# ── Pydantic models ────────────────────────────────────────────────────

class PurchaseOrderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    po_no: str
    po_date: date
    vendor_id: Optional[int] = None
    event_id: Optional[int] = None
    pnr_id: Optional[int] = None
    currency: str = "EGP"
    exchange_rate: float = 1.0
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    status: str = "OPEN"
    expected_delivery: Optional[date] = None
    notes: Optional[str] = None


class PurchaseOrderOut(PurchaseOrderCreate):
    id: int


class VendorInvoiceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    invoice_no: str
    invoice_date: date
    vendor_id: Optional[int] = None
    po_id: Optional[int] = None
    event_id: Optional[int] = None
    pnr_id: Optional[int] = None
    currency: str = "EGP"
    exchange_rate: float = 1.0
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    paid_amount: float = 0.0
    status: str = "OPEN"
    due_date: Optional[date] = None
    notes: Optional[str] = None


class VendorInvoiceOut(VendorInvoiceCreate):
    id: int


class PURSummary(BaseModel):
    total_pos: int = 0
    total_vendor_invoices: int = 0
    total_po_value: float = 0.0
    total_invoiced: float = 0.0
    total_paid: float = 0.0
    total_outstanding: float = 0.0
    avg_po: float = 0.0
    by_po_status: dict = {}
    by_invoice_status: dict = {}
    by_currency: dict = {}


# ── Helpers ────────────────────────────────────────────────────────────

def _po_filters(vendor_id, event_id, pnr_id, date_from, date_to, status_, currency, search):
    f = []
    if vendor_id is not None:
        f.append(PurchaseOrder.vendor_id == vendor_id)
    if event_id is not None:
        f.append(PurchaseOrder.event_id == event_id)
    if pnr_id is not None:
        f.append(PurchaseOrder.pnr_id == pnr_id)
    if date_from:
        f.append(PurchaseOrder.po_date >= date_from)
    if date_to:
        f.append(PurchaseOrder.po_date <= date_to)
    if status_:
        f.append(PurchaseOrder.status == status_)
    if currency:
        f.append(PurchaseOrder.currency == currency)
    if search:
        f.append(or_(
            PurchaseOrder.po_no.ilike(f"%{search}%"),
            PurchaseOrder.notes.ilike(f"%{search}%"),
        ))
    return f


def _vi_filters(vendor_id, event_id, pnr_id, po_id, date_from, date_to, status_, currency, search):
    f = []
    if vendor_id is not None:
        f.append(VendorInvoice.vendor_id == vendor_id)
    if event_id is not None:
        f.append(VendorInvoice.event_id == event_id)
    if pnr_id is not None:
        f.append(VendorInvoice.pnr_id == pnr_id)
    if po_id is not None:
        f.append(VendorInvoice.po_id == po_id)
    if date_from:
        f.append(VendorInvoice.invoice_date >= date_from)
    if date_to:
        f.append(VendorInvoice.invoice_date <= date_to)
    if status_:
        f.append(VendorInvoice.status == status_)
    if currency:
        f.append(VendorInvoice.currency == currency)
    if search:
        f.append(or_(
            VendorInvoice.invoice_no.ilike(f"%{search}%"),
            VendorInvoice.notes.ilike(f"%{search}%"),
        ))
    return f


# ── End-points ─────────────────────────────────────────────────────────

@router.get("/orders", response_model=PaginatedResponse[PurchaseOrderOut])
async def list_orders(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    vendor_id: Annotated[Optional[int], Query()] = None,
    event_id: Annotated[Optional[int], Query()] = None,
    pnr_id: Annotated[Optional[int], Query()] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    currency: Annotated[Optional[str], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(PurchaseOrder)
    f = _po_filters(vendor_id, event_id, pnr_id, date_from, date_to,
                    status_, currency, search)
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(PurchaseOrder.po_date), desc(PurchaseOrder.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[PurchaseOrderOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/orders/{po_id}", response_model=dict)
async def get_order(
    po_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    po = (await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id)
    )).scalar_one_or_none()
    if not po:
        raise HTTPException(404, "Purchase order not found")
    invoices = (await session.execute(
        select(VendorInvoice).where(VendorInvoice.po_id == po_id)
    )).scalars().all()
    invoiced_total = sum(i.total or 0 for i in invoices)
    return {
        "po": PurchaseOrderOut.model_validate(po).model_dump(),
        "vendor_invoices": [VendorInvoiceOut.model_validate(i).model_dump() for i in invoices],
        "invoice_count": len(invoices),
        "invoiced_total": round(invoiced_total, 2),
        "outstanding": round((po.total or 0) - invoiced_total, 2),
    }


@router.post("/orders", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: PurchaseOrderCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    po = PurchaseOrder(**payload.model_dump(exclude_unset=True))
    session.add(po)
    await session.commit()
    await session.refresh(po)
    return PurchaseOrderOut.model_validate(po)


@router.get("/invoices", response_model=PaginatedResponse[VendorInvoiceOut])
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    vendor_id: Annotated[Optional[int], Query()] = None,
    event_id: Annotated[Optional[int], Query()] = None,
    pnr_id: Annotated[Optional[int], Query()] = None,
    po_id: Annotated[Optional[int], Query()] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    currency: Annotated[Optional[str], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(VendorInvoice)
    f = _vi_filters(vendor_id, event_id, pnr_id, po_id, date_from, date_to,
                    status_, currency, search)
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(VendorInvoice.invoice_date), desc(VendorInvoice.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[VendorInvoiceOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/invoices/{invoice_id}", response_model=VendorInvoiceOut)
async def get_invoice(
    invoice_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    inv = (await session.execute(
        select(VendorInvoice).where(VendorInvoice.id == invoice_id)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Vendor invoice not found")
    return VendorInvoiceOut.model_validate(inv)


@router.post("/invoices", response_model=VendorInvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: VendorInvoiceCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    inv = VendorInvoice(**payload.model_dump(exclude_unset=True))
    session.add(inv)
    await session.commit()
    await session.refresh(inv)
    return VendorInvoiceOut.model_validate(inv)


@router.get("/summary", response_model=PURSummary)
async def get_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    po_f = []
    if date_from:
        po_f.append(PurchaseOrder.po_date >= date_from)
    if date_to:
        po_f.append(PurchaseOrder.po_date <= date_to)
    po_base = select(PurchaseOrder)
    if po_f:
        po_base = po_base.where(and_(*po_f))
    po_head = (await session.execute(
        select(
            func.count().label("cnt"),
            func.coalesce(func.sum(PurchaseOrder.total), 0).label("amt"),
        ).select_from(po_base.subquery())
    )).one()
    vi_f = []
    if date_from:
        vi_f.append(VendorInvoice.invoice_date >= date_from)
    if date_to:
        vi_f.append(VendorInvoice.invoice_date <= date_to)
    vi_base = select(VendorInvoice)
    if vi_f:
        vi_base = vi_base.where(and_(*vi_f))
    vi_head = (await session.execute(
        select(
            func.count().label("cnt"),
            func.coalesce(func.sum(VendorInvoice.total), 0).label("amt"),
            func.coalesce(func.sum(VendorInvoice.paid_amount), 0).label("paid"),
        ).select_from(vi_base.subquery())
    )).one()
    po_status_rows = (await session.execute(
        select(PurchaseOrder.status, func.count().label("cnt"))
        .group_by(PurchaseOrder.status)
    )).all()
    vi_status_rows = (await session.execute(
        select(VendorInvoice.status, func.count().label("cnt"))
        .group_by(VendorInvoice.status)
    )).all()
    cur_rows = (await session.execute(
        select(VendorInvoice.currency,
               func.coalesce(func.sum(VendorInvoice.total), 0).label("amt"))
        .group_by(VendorInvoice.currency)
    )).all()
    return PURSummary(
        total_pos=po_head.cnt or 0,
        total_vendor_invoices=vi_head.cnt or 0,
        total_po_value=round(po_head.amt or 0, 2),
        total_invoiced=round(vi_head.amt or 0, 2),
        total_paid=round(vi_head.paid or 0, 2),
        total_outstanding=round((vi_head.amt or 0) - (vi_head.paid or 0), 2),
        avg_po=round((po_head.amt or 0) / po_head.cnt, 2) if po_head.cnt else 0.0,
        by_po_status={r.status: r.cnt for r in po_status_rows if r.status},
        by_invoice_status={r.status: r.cnt for r in vi_status_rows if r.status},
        by_currency={r.currency: round(r.amt or 0, 2) for r in cur_rows if r.currency},
    )


@router.get("/by-event/{event_id}")
async def by_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    pos = (await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.event_id == event_id)
    )).scalars().all()
    invoices = (await session.execute(
        select(VendorInvoice).where(VendorInvoice.event_id == event_id)
    )).scalars().all()
    return {
        "event_id": event_id,
        "purchase_orders": [PurchaseOrderOut.model_validate(p).model_dump() for p in pos],
        "vendor_invoices": [VendorInvoiceOut.model_validate(i).model_dump() for i in invoices],
        "po_count": len(pos),
        "invoice_count": len(invoices),
        "po_total": round(sum(p.total or 0 for p in pos), 2),
        "invoice_total": round(sum(i.total or 0 for i in invoices), 2),
    }


@router.get("/by-vendor/{vendor_id}")
async def by_vendor(
    vendor_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    pos = (await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.vendor_id == vendor_id)
    )).scalars().all()
    invoices = (await session.execute(
        select(VendorInvoice).where(VendorInvoice.vendor_id == vendor_id)
    )).scalars().all()
    return {
        "vendor_id": vendor_id,
        "purchase_orders": [PurchaseOrderOut.model_validate(p).model_dump() for p in pos],
        "vendor_invoices": [VendorInvoiceOut.model_validate(i).model_dump() for i in invoices],
        "po_count": len(pos),
        "invoice_count": len(invoices),
        "po_total": round(sum(p.total or 0 for p in pos), 2),
        "invoice_total": round(sum(i.total or 0 for i in invoices), 2),
    }


@router.get("/top-vendors")
async def top_vendors(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    stmt = (
        select(
            VendorInvoice.vendor_id,
            func.count().label("invoice_count"),
            func.coalesce(func.sum(VendorInvoice.total), 0).label("spend"),
            func.coalesce(func.sum(VendorInvoice.paid_amount), 0).label("paid"),
        )
        .where(VendorInvoice.vendor_id.isnot(None))
        .group_by(VendorInvoice.vendor_id)
        .order_by(desc("spend"))
        .limit(limit)
    )
    if date_from:
        stmt = stmt.where(VendorInvoice.invoice_date >= date_from)
    if date_to:
        stmt = stmt.where(VendorInvoice.invoice_date <= date_to)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "vendor_id": r.vendor_id,
            "invoice_count": r.invoice_count,
            "spend": round(r.spend or 0, 2),
            "paid": round(r.paid or 0, 2),
            "outstanding": round((r.spend or 0) - (r.paid or 0), 2),
        } for r in rows
    ]


@router.get("/spend-by-month")
async def spend_by_month(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    year: Annotated[Optional[int], Query()] = None,
):
    """Monthly vendor-spend series. Uses to_char on Postgres, strftime on SQLite."""
    try:
        ym = func.to_char(VendorInvoice.invoice_date, "YYYY-MM").label("ym")
        stmt = (
            select(
                ym,
                func.count().label("cnt"),
                func.coalesce(func.sum(VendorInvoice.total), 0).label("spend"),
                func.coalesce(func.sum(VendorInvoice.tax_amount), 0).label("tax"),
            )
            .group_by("ym")
            .order_by("ym")
        )
        if year:
            stmt = stmt.where(
                func.to_char(VendorInvoice.invoice_date, "YYYY") == str(year)
            )
        rows = (await session.execute(stmt)).all()
        return [
            {
                "month": r.ym,
                "invoice_count": r.cnt,
                "spend": round(r.spend or 0, 2),
                "tax": round(r.tax or 0, 2),
            } for r in rows if r.ym
        ]
    except Exception:
        rows = (await session.execute(text("""
            SELECT strftime('%Y-%m', invoice_date) AS ym,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(total), 0) AS spend,
                   COALESCE(SUM(tax_amount), 0) AS tax
            FROM vendor_invoices
            GROUP BY ym
            ORDER BY ym
        """))).all()
        return [
            {
                "month": r.ym,
                "invoice_count": r.cnt,
                "spend": round(r.spend or 0, 2),
                "tax": round(r.tax or 0, 2),
            } for r in rows if r.ym
        ]


@router.get("/aging-report")
async def aging_report(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    as_of: Annotated[Optional[date], Query()] = None,
):
    """Vendor-invoice aging buckets (0-30 / 31-60 / 61-90 / 90+)."""
    from datetime import datetime as _dt
    cutoff = as_of or _dt.utcnow().date()
    rows = (await session.execute(
        select(VendorInvoice).where(
            and_(
                VendorInvoice.status.in_(["OPEN", "PARTIAL"]),
                VendorInvoice.due_date.isnot(None),
            )
        )
    )).scalars().all()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    counts = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    total = 0.0
    for inv in rows:
        if not inv.due_date:
            continue
        days_past = (cutoff - inv.due_date).days
        outstanding = (inv.total or 0) - (inv.paid_amount or 0)
        if outstanding <= 0:
            continue
        total += outstanding
        if days_past <= 30:
            buckets["0-30"] += outstanding; counts["0-30"] += 1
        elif days_past <= 60:
            buckets["31-60"] += outstanding; counts["31-60"] += 1
        elif days_past <= 90:
            buckets["61-90"] += outstanding; counts["61-90"] += 1
        else:
            buckets["90+"] += outstanding; counts["90+"] += 1
    return {
        "as_of": cutoff.isoformat(),
        "total_outstanding": round(total, 2),
        "buckets": {k: round(v, 2) for k, v in buckets.items()},
        "counts": counts,
    }
