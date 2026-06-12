"""
COST Router — Cost Management
==============================
End-points (prefix ``/api/v1/cost``):

  GET  /allocations                 — list cost allocations (paginated, filterable)
  GET  /allocations/{id}            — single allocation
  POST /allocations                 — create a new cost allocation
  DELETE /allocations/{id}          — reverse/delete an allocation
  GET  /summary                     — totals by category / cost-center / month
  GET  /by-event/{event_id}         — all costs for an event
  GET  /by-cost-center/{cc}         — all costs for a cost-center
  GET  /categories                  — distinct cost categories present
  GET  /monthly                     — monthly series (for charts)

Table: ``cost_allocations`` (one row per cost posted to a cost-center/event/PNR).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_empty_modules import CostAllocation
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cost", tags=["COST Management"])


# ── Pydantic models ────────────────────────────────────────────────────


class CostAllocationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    alloc_date: date
    cost_center: Optional[str] = None
    category: str
    event_id: Optional[int] = None
    pnr_id: Optional[int] = None
    vendor_id: Optional[int] = None
    po_id: Optional[int] = None
    source_type: Optional[str] = None  # PO / VI / JV / MANUAL
    source_id: Optional[int] = None
    amount: float
    currency: str = "EGP"
    exchange_rate: float = 1.0
    account_code: Optional[str] = None
    description: Optional[str] = None
    allocated_by: Optional[str] = None


class CostAllocationOut(CostAllocationCreate):
    id: int
    amount_egp: float = 0.0
    status: str = "POSTED"
    created_at: Optional[datetime] = None


class CostSummary(BaseModel):
    total_allocations: int = 0
    total_amount: float = 0.0
    total_amount_egp: float = 0.0
    by_category: dict = {}
    by_cost_center: dict = {}
    by_currency: dict = {}
    by_status: dict = {}


# ── End-points ─────────────────────────────────────────────────────────


@router.get("/allocations", response_model=PaginatedResponse[CostAllocationOut])
async def list_allocations(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    cost_center: Annotated[Optional[str], Query()] = None,
    category: Annotated[Optional[str], Query()] = None,
    event_id: Annotated[Optional[int], Query()] = None,
    pnr_id: Annotated[Optional[int], Query()] = None,
    vendor_id: Annotated[Optional[int], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    """List cost allocations, paginated and filterable."""
    stmt = select(CostAllocation)
    f = []
    if cost_center:
        f.append(CostAllocation.cost_center == cost_center)
    if category:
        f.append(CostAllocation.category == category)
    if event_id is not None:
        f.append(CostAllocation.event_id == event_id)
    if pnr_id is not None:
        f.append(CostAllocation.pnr_id == pnr_id)
    if vendor_id is not None:
        f.append(CostAllocation.vendor_id == vendor_id)
    if status_:
        f.append(CostAllocation.status == status_)
    if date_from:
        f.append(CostAllocation.alloc_date >= date_from)
    if date_to:
        f.append(CostAllocation.alloc_date <= date_to)
    if search:
        f.append(
            or_(
                CostAllocation.description.ilike(f"%{search}%"),
                CostAllocation.category.ilike(f"%{search}%"),
            )
        )
    if f:
        stmt = stmt.where(and_(*f))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(desc(CostAllocation.alloc_date), desc(CostAllocation.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[CostAllocationOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/allocations/{alloc_id}", response_model=CostAllocationOut)
async def get_allocation(
    alloc_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Fetch a single cost allocation."""
    row = (await session.execute(select(CostAllocation).where(CostAllocation.id == alloc_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Cost allocation {alloc_id} not found")
    return CostAllocationOut.model_validate(row)


@router.post("/allocations", response_model=CostAllocationOut, status_code=status.HTTP_201_CREATED)
async def create_allocation(
    payload: CostAllocationCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Create a new cost allocation (defaults to POSTED status)."""
    data = payload.model_dump()
    # amount_egp = amount * exchange_rate
    data["amount_egp"] = round((data.get("amount") or 0) * (data.get("exchange_rate") or 1.0), 2)
    alloc = CostAllocation(**data)
    session.add(alloc)
    await session.commit()
    await session.refresh(alloc)
    return CostAllocationOut.model_validate(alloc)


@router.delete("/allocations/{alloc_id}", response_model=dict)
async def reverse_allocation(
    alloc_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Reverse a posted allocation (sets status to REVERSED, does not delete)."""
    alloc = (await session.execute(select(CostAllocation).where(CostAllocation.id == alloc_id))).scalars().first()
    if not alloc:
        raise HTTPException(status_code=404, detail=f"Cost allocation {alloc_id} not found")
    if alloc.status == "REVERSED":
        return {"id": alloc_id, "status": "REVERSED", "note": "already reversed"}
    alloc.status = "REVERSED"
    await session.commit()
    return {"id": alloc_id, "status": "REVERSED"}


@router.get("/summary", response_model=CostSummary)
async def cost_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
):
    """Cost roll-up by category, cost-center, currency, status."""
    base = select(CostAllocation)
    f = []
    if date_from:
        f.append(CostAllocation.alloc_date >= date_from)
    if date_to:
        f.append(CostAllocation.alloc_date <= date_to)
    if status_:
        f.append(CostAllocation.status == status_)
    if f:
        base = base.where(and_(*f))

    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    amt_sum = (await session.execute(select(func.coalesce(func.sum(CostAllocation.amount), 0.0)).where(*f) if f else select(func.coalesce(func.sum(CostAllocation.amount), 0.0)))).scalar() or 0
    egp_sum = (await session.execute(select(func.coalesce(func.sum(CostAllocation.amount_egp), 0.0)).where(*f) if f else select(func.coalesce(func.sum(CostAllocation.amount_egp), 0.0)))).scalar() or 0

    # by category
    by_cat: dict = {}
    rows = (await session.execute(
        select(CostAllocation.category, func.coalesce(func.sum(CostAllocation.amount_egp), 0.0))
        .where(*f).group_by(CostAllocation.category) if f else
        select(CostAllocation.category, func.coalesce(func.sum(CostAllocation.amount_egp), 0.0)).group_by(CostAllocation.category)
    )).all()
    for cat, amt in rows:
        by_cat[cat or "UNCATEGORIZED"] = float(amt or 0)

    # by cost-center
    by_cc: dict = {}
    rows = (await session.execute(
        select(CostAllocation.cost_center, func.coalesce(func.sum(CostAllocation.amount_egp), 0.0))
        .where(*f).group_by(CostAllocation.cost_center) if f else
        select(CostAllocation.cost_center, func.coalesce(func.sum(CostAllocation.amount_egp), 0.0)).group_by(CostAllocation.cost_center)
    )).all()
    for cc, amt in rows:
        by_cc[cc or "UNASSIGNED"] = float(amt or 0)

    # by currency
    by_cur: dict = {}
    rows = (await session.execute(
        select(CostAllocation.currency, func.coalesce(func.sum(CostAllocation.amount), 0.0))
        .where(*f).group_by(CostAllocation.currency) if f else
        select(CostAllocation.currency, func.coalesce(func.sum(CostAllocation.amount), 0.0)).group_by(CostAllocation.currency)
    )).all()
    for cur, amt in rows:
        by_cur[cur or "EGP"] = float(amt or 0)

    # by status
    by_status: dict = {}
    rows = (await session.execute(
        select(CostAllocation.status, func.count(CostAllocation.id))
        .where(*f).group_by(CostAllocation.status) if f else
        select(CostAllocation.status, func.count(CostAllocation.id)).group_by(CostAllocation.status)
    )).all()
    for s, c in rows:
        by_status[s or "UNKNOWN"] = c

    return CostSummary(
        total_allocations=total,
        total_amount=float(amt_sum),
        total_amount_egp=float(egp_sum),
        by_category=by_cat,
        by_cost_center=by_cc,
        by_currency=by_cur,
        by_status=by_status,
    )


@router.get("/by-event/{event_id}", response_model=List[CostAllocationOut])
async def costs_by_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """All cost allocations tied to a specific event."""
    stmt = select(CostAllocation).where(CostAllocation.event_id == event_id).order_by(desc(CostAllocation.alloc_date))
    rows = (await session.execute(stmt)).scalars().all()
    return [CostAllocationOut.model_validate(r) for r in rows]


@router.get("/by-cost-center/{cc}", response_model=List[CostAllocationOut])
async def costs_by_cost_center(
    cc: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    """All cost allocations for a given cost-center, optionally date-bounded."""
    stmt = select(CostAllocation).where(CostAllocation.cost_center == cc)
    if date_from:
        stmt = stmt.where(CostAllocation.alloc_date >= date_from)
    if date_to:
        stmt = stmt.where(CostAllocation.alloc_date <= date_to)
    stmt = stmt.order_by(desc(CostAllocation.alloc_date))
    rows = (await session.execute(stmt)).scalars().all()
    return [CostAllocationOut.model_validate(r) for r in rows]


@router.get("/categories", response_model=List[str])
async def distinct_categories(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Return the distinct list of cost categories present in the data."""
    stmt = select(CostAllocation.category).distinct().order_by(CostAllocation.category)
    rows = (await session.execute(stmt)).scalars().all()
    return [r for r in rows if r]


@router.get("/monthly", response_model=List[dict])
async def monthly_series(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    year: Annotated[Optional[int], Query()] = None,
):
    """Return cost totals by month (default = current year) for charting."""
    from sqlalchemy import extract
    if year is None:
        year = date.today().year
    stmt = (
        select(
            extract("month", CostAllocation.alloc_date).label("month"),
            func.coalesce(func.sum(CostAllocation.amount_egp), 0.0).label("total_egp"),
            func.count(CostAllocation.id).label("count"),
        )
        .where(extract("year", CostAllocation.alloc_date) == year)
        .group_by("month")
        .order_by("month")
    )
    rows = (await session.execute(stmt)).all()
    return [{"month": int(m), "total_egp": float(t or 0), "count": int(c or 0)} for m, t, c in rows]
