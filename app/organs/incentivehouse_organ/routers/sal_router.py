"""
SAL Router — Sales Invoices, Line Items & Revenue Analytics
============================================================
End-points (prefix ``/api/v1/sal``):

  GET  /invoices                    — list sales invoices (paginated, filterable)
  GET  /invoices/{id}               — single invoice with line items
  POST /invoices                    — create a new sales invoice (header)
  POST /invoices/{id}/line-items    — bulk-add line items
  GET  /line-items                  — list sales line items
  GET  /summary                     — top-level revenue / tax / status rollup
  GET  /by-event/{event_id}         — all invoices for a given event
  GET  /by-client/{client_id}       — all invoices for a given client
  GET  /by-pnr/{pnr_id}             — all line items tied to a PNR
  GET  /top-clients                 — top-N clients by revenue
  GET  /revenue-by-month            — monthly revenue series

All read paths use the async SQLAlchemy session for non-blocking I/O on
the FastAPI event loop. Writes commit and refresh so the returned object
contains the auto-generated ``id``.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_production import (
    SalesInvoice, SalesLineItem, Event,
)
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sal", tags=["SAL Sales"])


# ── Pydantic request / response models ──────────────────────────────────

class SalesInvoiceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    invoice_no: str
    invoice_date: date
    client_id: Optional[int] = None
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
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class SalesInvoiceOut(SalesInvoiceCreate):
    id: int


class SalesLineItemCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    line_no: int = 1
    item_code: Optional[str] = None
    description: Optional[str] = None
    quantity: float = 1.0
    unit_price: float = 0.0
    discount: float = 0.0
    tax_rate: float = 0.0
    line_total: float = 0.0
    cost_center: Optional[str] = None
    pnr_id: Optional[int] = None
    account_code: Optional[str] = None


class SalesLineItemOut(SalesLineItemCreate):
    id: int
    invoice_id: int


class SALSummary(BaseModel):
    total_invoices: int = 0
    total_revenue: float = 0.0
    total_tax: float = 0.0
    total_paid: float = 0.0
    total_outstanding: float = 0.0
    avg_invoice: float = 0.0
    by_status: dict = {}
    by_currency: dict = {}


# ── Helpers ────────────────────────────────────────────────────────────

def _invoice_filters(
    client_id: Optional[int], event_id: Optional[int], pnr_id: Optional[int],
    date_from: Optional[date], date_to: Optional[date],
    status_: Optional[str], currency: Optional[str], search: Optional[str],
):
    f = []
    if client_id is not None:
        f.append(SalesInvoice.client_id == client_id)
    if event_id is not None:
        f.append(SalesInvoice.event_id == event_id)
    if pnr_id is not None:
        f.append(SalesInvoice.pnr_id == pnr_id)
    if date_from:
        f.append(SalesInvoice.invoice_date >= date_from)
    if date_to:
        f.append(SalesInvoice.invoice_date <= date_to)
    if status_:
        f.append(SalesInvoice.status == status_)
    if currency:
        f.append(SalesInvoice.currency == currency)
    if search:
        f.append(or_(
            SalesInvoice.invoice_no.ilike(f"%{search}%"),
            SalesInvoice.notes.ilike(f"%{search}%"),
        ))
    return f


# ── End-points ─────────────────────────────────────────────────────────

@router.get("/invoices", response_model=PaginatedResponse[SalesInvoiceOut],
            summary="List sales invoices")
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    client_id: Annotated[Optional[int], Query()] = None,
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
    stmt = select(SalesInvoice)
    f = _invoice_filters(
        client_id, event_id, pnr_id, date_from, date_to,
        status_, currency, search,
    )
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(SalesInvoice.invoice_date), desc(SalesInvoice.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[SalesInvoiceOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/invoices/{invoice_id}", response_model= dict)
async def get_invoice(
    invoice_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    inv = (await session.execute(
        select(SalesInvoice).where(SalesInvoice.id == invoice_id)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Sales invoice not found")
    items = (await session.execute(
        select(SalesLineItem)
        .where(SalesLineItem.invoice_id == invoice_id)
        .order_by(SalesLineItem.line_no)
    )).scalars().all()
    return {
        "invoice": SalesInvoiceOut.model_validate(inv).model_dump(),
        "line_items": [SalesLineItemOut.model_validate(li).model_dump() for li in items],
        "line_count": len(items),
    }


@router.post("/invoices", response_model=SalesInvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: SalesInvoiceCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    inv = SalesInvoice(**payload.model_dump(exclude_unset=True))
    session.add(inv)
    await session.commit()
    await session.refresh(inv)
    return SalesInvoiceOut.model_validate(inv)


@router.post("/invoices/{invoice_id}/line-items",
             response_model=List[SalesLineItemOut],
             status_code=status.HTTP_201_CREATED)
async def add_line_items(
    invoice_id: int,
    items: List[SalesLineItemCreate],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    inv = (await session.execute(
        select(SalesInvoice).where(SalesInvoice.id == invoice_id)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Sales invoice not found")
    new_items = []
    for it in items:
        li = SalesLineItem(invoice_id=invoice_id, **it.model_dump(exclude_unset=True))
        session.add(li)
        new_items.append(li)
    await session.commit()
    for li in new_items:
        await session.refresh(li)
    return [SalesLineItemOut(invoice_id=invoice_id, **SalesLineItemOut.model_validate(li).model_dump())
            for li in new_items]


@router.get("/line-items", response_model=PaginatedResponse[SalesLineItemOut])
async def list_line_items(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    invoice_id: Annotated[Optional[int], Query()] = None,
    pnr_id: Annotated[Optional[int], Query()] = None,
    cost_center: Annotated[Optional[str], Query()] = None,
    account_code: Annotated[Optional[str], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(SalesLineItem)
    f = []
    if invoice_id is not None:
        f.append(SalesLineItem.invoice_id == invoice_id)
    if pnr_id is not None:
        f.append(SalesLineItem.pnr_id == pnr_id)
    if cost_center:
        f.append(SalesLineItem.cost_center == cost_center)
    if account_code:
        f.append(SalesLineItem.account_code == account_code)
    if search:
        f.append(or_(
            SalesLineItem.description.ilike(f"%{search}%"),
            SalesLineItem.item_code.ilike(f"%{search}%"),
        ))
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(SalesLineItem.invoice_id), SalesLineItem.line_no)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[SalesLineItemOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/summary", response_model=SALSummary)
async def get_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    f = []
    if date_from:
        f.append(SalesInvoice.invoice_date >= date_from)
    if date_to:
        f.append(SalesInvoice.invoice_date <= date_to)
    base = select(SalesInvoice)
    if f:
        base = base.where(and_(*f))
    head = (await session.execute(
        select(
            func.count().label("cnt"),
            func.coalesce(func.sum(SalesInvoice.total), 0).label("revenue"),
            func.coalesce(func.sum(SalesInvoice.tax_amount), 0).label("tax"),
            func.coalesce(func.sum(SalesInvoice.paid_amount), 0).label("paid"),
        )
    )).one()
    status_rows = (await session.execute(
        select(SalesInvoice.status, func.count().label("cnt"))
        .group_by(SalesInvoice.status)
    )).all()
    cur_rows = (await session.execute(
        select(SalesInvoice.currency,
               func.coalesce(func.sum(SalesInvoice.total), 0).label("amt"))
        .group_by(SalesInvoice.currency)
    )).all()
    return SALSummary(
        total_invoices=head.cnt or 0,
        total_revenue=round(head.revenue or 0, 2),
        total_tax=round(head.tax or 0, 2),
        total_paid=round(head.paid or 0, 2),
        total_outstanding=round((head.revenue or 0) - (head.paid or 0), 2),
        avg_invoice=round((head.revenue or 0) / head.cnt, 2) if head.cnt else 0.0,
        by_status={r.status: r.cnt for r in status_rows if r.status},
        by_currency={r.currency: round(r.amt or 0, 2) for r in cur_rows if r.currency},
    )


@router.get("/by-event/{event_id}", response_model=List[SalesInvoiceOut])
async def by_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rows = (await session.execute(
        select(SalesInvoice)
        .where(SalesInvoice.event_id == event_id)
        .order_by(desc(SalesInvoice.invoice_date))
    )).scalars().all()
    return [SalesInvoiceOut.model_validate(r) for r in rows]


@router.get("/by-client/{client_id}", response_model=List[SalesInvoiceOut])
async def by_client(
    client_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rows = (await session.execute(
        select(SalesInvoice)
        .where(SalesInvoice.client_id == client_id)
        .order_by(desc(SalesInvoice.invoice_date))
    )).scalars().all()
    return [SalesInvoiceOut.model_validate(r) for r in rows]


@router.get("/by-pnr/{pnr_id}", response_model=List[SalesLineItemOut])
async def by_pnr(
    pnr_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rows = (await session.execute(
        select(SalesLineItem)
        .where(SalesLineItem.pnr_id == pnr_id)
        .order_by(SalesLineItem.invoice_id, SalesLineItem.line_no)
    )).scalars().all()
    return [SalesLineItemOut.model_validate(r) for r in rows]


@router.get("/top-clients")
async def top_clients(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    stmt = (
        select(
            SalesInvoice.client_id,
            func.count().label("invoice_count"),
            func.coalesce(func.sum(SalesInvoice.total), 0).label("revenue"),
            func.coalesce(func.sum(SalesInvoice.paid_amount), 0).label("paid"),
        )
        .where(SalesInvoice.client_id.isnot(None))
        .group_by(SalesInvoice.client_id)
        .order_by(desc("revenue"))
        .limit(limit)
    )
    if date_from:
        stmt = stmt.where(SalesInvoice.invoice_date >= date_from)
    if date_to:
        stmt = stmt.where(SalesInvoice.invoice_date <= date_to)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "client_id": r.client_id,
            "invoice_count": r.invoice_count,
            "revenue": round(r.revenue or 0, 2),
            "paid": round(r.paid or 0, 2),
            "outstanding": round((r.revenue or 0) - (r.paid or 0), 2),
        } for r in rows
    ]


@router.get("/revenue-by-month")
async def revenue_by_month(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    year: Annotated[Optional[int], Query()] = None,
):
    ycol = func.strftime("%Y-%m", SalesInvoice.invoice_date) if False else None
    # Use portable date-formatting (SQLite + Postgres compatible)
    ym = func.to_char(SalesInvoice.invoice_date, "YYYY-MM").label("ym")
    stmt = (
        select(
            ym,
            func.count().label("cnt"),
            func.coalesce(func.sum(SalesInvoice.total), 0).label("revenue"),
            func.coalesce(func.sum(SalesInvoice.tax_amount), 0).label("tax"),
        )
        .group_by("ym")
        .order_by("ym")
    )
    if year:
        stmt = stmt.where(
            func.to_char(SalesInvoice.invoice_date, "YYYY") == str(year)
        )
    try:
        rows = (await session.execute(stmt)).all()
        return [
            {
                "month": r.ym,
                "invoice_count": r.cnt,
                "revenue": round(r.revenue or 0, 2),
                "tax": round(r.tax or 0, 2),
            } for r in rows if r.ym
        ]
    except Exception:
        # Fallback for SQLite (no to_char)
        rows = (await session.execute(text("""
            SELECT strftime('%Y-%m', invoice_date) AS ym,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(total), 0) AS revenue,
                   COALESCE(SUM(tax_amount), 0) AS tax
            FROM sales_invoices
            GROUP BY ym
            ORDER BY ym
        """))).all()
        return [
            {
                "month": r.ym,
                "invoice_count": r.cnt,
                "revenue": round(r.revenue or 0, 2),
                "tax": round(r.tax or 0, 2),
            } for r in rows if r.ym
        ]
