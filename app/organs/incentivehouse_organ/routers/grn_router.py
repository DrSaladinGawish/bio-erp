"""
GRN Router — Goods Receipt Notes
================================
End-points (prefix ``/api/v1/grn``):

  GET  /receipts                 — list GRN headers (paginated, filterable)
  GET  /receipts/{id}            — single GRN with its line items
  POST /receipts                 — create a new GRN header
  GET  /receipts/{id}/lines      — line items for a GRN
  POST /receipts/{id}/lines      — add a line to an existing GRN
  POST /receipts/{id}/post       — post the GRN (DRAFT → POSTED, sets status)
  GET  /summary                  — GRN rollup (count, value, by status)
  GET  /by-po/{po_id}            — find the GRN(s) for a given PO

Table layout:
  grn_headers  — header  (grn_no, po_id, vendor_id, event_id, status, totals)
  grn_lines    — lines   (grn_id, ordered_qty, received_qty, rejected_qty, cost)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models_empty_modules import GrnHeader, GrnLine
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/grn", tags=["GRN Goods Receipt"])


# ── Pydantic models ────────────────────────────────────────────────────


class GrnHeaderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    grn_no: str
    grn_date: date
    po_id: Optional[int] = None
    vendor_id: Optional[int] = None
    event_id: Optional[int] = None
    pnr_id: Optional[int] = None
    warehouse: Optional[str] = "MAIN"
    received_by: Optional[str] = None
    inspection_status: Optional[str] = "PENDING"
    currency: Optional[str] = "EGP"
    notes: Optional[str] = None


class GrnHeaderOut(GrnHeaderCreate):
    id: int
    total_qty: float = 0.0
    total_value: float = 0.0
    status: str = "DRAFT"


class GrnLineCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    line_no: Optional[int] = None
    item_code: Optional[str] = None
    description: Optional[str] = None
    ordered_qty: float = 0.0
    received_qty: float = 0.0
    rejected_qty: float = 0.0
    uom: str = "EA"
    unit_cost: float = 0.0
    account_code: Optional[str] = None
    cost_center: Optional[str] = None
    notes: Optional[str] = None


class GrnLineOut(GrnLineCreate):
    id: int
    grn_id: int
    line_total: float = 0.0


class GrnSummary(BaseModel):
    total_grns: int = 0
    draft: int = 0
    posted: int = 0
    cancelled: int = 0
    total_received_qty: float = 0.0
    total_value: float = 0.0
    by_status: dict = {}
    by_warehouse: dict = {}


# ── End-points ─────────────────────────────────────────────────────────


@router.get("/receipts", response_model=PaginatedResponse[GrnHeaderOut])
async def list_grn(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    po_id: Annotated[Optional[int], Query()] = None,
    vendor_id: Annotated[Optional[int], Query()] = None,
    event_id: Annotated[Optional[int], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    """List Goods Receipt Note headers, paginated and filterable."""
    stmt = select(GrnHeader)
    f = []
    if po_id is not None:
        f.append(GrnHeader.po_id == po_id)
    if vendor_id is not None:
        f.append(GrnHeader.vendor_id == vendor_id)
    if event_id is not None:
        f.append(GrnHeader.event_id == event_id)
    if status_:
        f.append(GrnHeader.status == status_)
    if date_from:
        f.append(GrnHeader.grn_date >= date_from)
    if date_to:
        f.append(GrnHeader.grn_date <= date_to)
    if search:
        f.append(
            or_(
                GrnHeader.grn_no.ilike(f"%{search}%"),
                GrnHeader.notes.ilike(f"%{search}%"),
            )
        )
    if f:
        stmt = stmt.where(and_(*f))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(desc(GrnHeader.grn_date), desc(GrnHeader.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[GrnHeaderOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/receipts/{grn_id}", response_model=dict)
async def get_grn(
    grn_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Fetch a single GRN header plus its line items."""
    stmt = select(GrnHeader).options(selectinload(GrnHeader.id)).where(GrnHeader.id == grn_id)
    grn = (await session.execute(stmt)).scalars().first()
    if not grn:
        raise HTTPException(status_code=404, detail=f"GRN {grn_id} not found")
    line_stmt = select(GrnLine).where(GrnLine.grn_id == grn_id).order_by(GrnLine.line_no, GrnLine.id)
    lines = (await session.execute(line_stmt)).scalars().all()
    return {
        "header": GrnHeaderOut.model_validate(grn).model_dump(),
        "lines": [GrnLineOut.model_validate(l).model_dump() for l in lines],
    }


@router.post("/receipts", response_model=GrnHeaderOut, status_code=status.HTTP_201_CREATED)
async def create_grn(
    payload: GrnHeaderCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Create a new GRN header (status starts as DRAFT)."""
    grn = GrnHeader(**payload.model_dump())
    session.add(grn)
    await session.commit()
    await session.refresh(grn)
    return GrnHeaderOut.model_validate(grn)


@router.get("/receipts/{grn_id}/lines", response_model=List[GrnLineOut])
async def list_grn_lines(
    grn_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Return all line items for a GRN."""
    # verify header exists
    exists = (await session.execute(select(func.count()).select_from(GrnHeader).where(GrnHeader.id == grn_id))).scalar() or 0
    if not exists:
        raise HTTPException(status_code=404, detail=f"GRN {grn_id} not found")
    stmt = select(GrnLine).where(GrnLine.grn_id == grn_id).order_by(GrnLine.line_no, GrnLine.id)
    rows = (await session.execute(stmt)).scalars().all()
    return [GrnLineOut.model_validate(r) for r in rows]


@router.post("/receipts/{grn_id}/lines", response_model=GrnLineOut, status_code=status.HTTP_201_CREATED)
async def add_grn_line(
    grn_id: int,
    payload: GrnLineCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Append a line item to a GRN. Recomputes the header totals."""
    grn = (await session.execute(select(GrnHeader).where(GrnHeader.id == grn_id))).scalars().first()
    if not grn:
        raise HTTPException(status_code=404, detail=f"GRN {grn_id} not found")
    line = GrnLine(grn_id=grn_id, **payload.model_dump())
    line.line_total = round((line.received_qty or 0) * (line.unit_cost or 0), 2)
    session.add(line)
    # recompute header totals
    sum_stmt = select(func.coalesce(func.sum(GrnLine.received_qty), 0.0),
                      func.coalesce(func.sum(GrnLine.line_total), 0.0)).where(GrnLine.grn_id == grn_id)
    total_qty, total_value = (await session.execute(sum_stmt)).one()
    grn.total_qty = float(total_qty or 0)
    grn.total_value = float(total_value or 0)
    await session.commit()
    await session.refresh(line)
    return GrnLineOut.model_validate(line)


@router.post("/receipts/{grn_id}/post", response_model=GrnHeaderOut)
async def post_grn(
    grn_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Post a GRN — moves status DRAFT → POSTED. Idempotent."""
    grn = (await session.execute(select(GrnHeader).where(GrnHeader.id == grn_id))).scalars().first()
    if not grn:
        raise HTTPException(status_code=404, detail=f"GRN {grn_id} not found")
    if grn.status == "POSTED":
        return GrnHeaderOut.model_validate(grn)  # idempotent
    if grn.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot post a cancelled GRN")
    grn.status = "POSTED"
    await session.commit()
    await session.refresh(grn)
    return GrnHeaderOut.model_validate(grn)


@router.get("/summary", response_model=GrnSummary)
async def grn_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """GRN roll-up: counts, totals, by status and warehouse."""
    total = (await session.execute(select(func.count(GrnHeader.id)))).scalar() or 0
    draft = (await session.execute(select(func.count(GrnHeader.id)).where(GrnHeader.status == "DRAFT"))).scalar() or 0
    posted = (await session.execute(select(func.count(GrnHeader.id)).where(GrnHeader.status == "POSTED"))).scalar() or 0
    cancelled = (await session.execute(select(func.count(GrnHeader.id)).where(GrnHeader.status == "CANCELLED"))).scalar() or 0
    qty_sum = (await session.execute(select(func.coalesce(func.sum(GrnHeader.total_qty), 0.0)))).scalar() or 0
    val_sum = (await session.execute(select(func.coalesce(func.sum(GrnHeader.total_value), 0.0)))).scalar() or 0
    # by status
    by_status = {}
    rows = (await session.execute(select(GrnHeader.status, func.count(GrnHeader.id)).group_by(GrnHeader.status))).all()
    for s, c in rows:
        by_status[s or "UNKNOWN"] = c
    # by warehouse
    by_warehouse = {}
    rows = (await session.execute(select(GrnHeader.warehouse, func.count(GrnHeader.id)).group_by(GrnHeader.warehouse))).all()
    for w, c in rows:
        by_warehouse[w or "UNKNOWN"] = c
    return GrnSummary(
        total_grns=total,
        draft=draft,
        posted=posted,
        cancelled=cancelled,
        total_received_qty=float(qty_sum),
        total_value=float(val_sum),
        by_status=by_status,
        by_warehouse=by_warehouse,
    )


@router.get("/by-po/{po_id}", response_model=List[GrnHeaderOut])
async def grn_by_po(
    po_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Return all GRNs that were received against a given PO."""
    stmt = select(GrnHeader).where(GrnHeader.po_id == po_id).order_by(desc(GrnHeader.grn_date))
    rows = (await session.execute(stmt)).scalars().all()
    return [GrnHeaderOut.model_validate(r) for r in rows]
