"""
EVN Router — Events, Work Orders, Staff Assignments & Event P&L
================================================================
End-points (prefix ``/api/v1/evn``):

  GET  /events                       — list events (paginated, filterable)
  GET  /events/{id}                  — single event with work-orders & assignments
  POST /events                       — create a new event
  PUT  /events/{id}                  — update an event
  GET  /events/{id}/work-orders      — work orders for an event
  GET  /events/{id}/assignments      — staff assignments for an event
  GET  /events/{id}/financials       — event P&L (revenue − cost)
  GET  /work-orders                  — list work orders
  GET  /work-orders/{id}             — single work order
  POST /work-orders                  — create work order
  GET  /assignments                  — list staff assignments
  POST /assignments                  — create staff assignment
  GET  /summary                      — top-level events rollup
  GET  /upcoming                     — events ordered by date, OPEN only
  GET  /budget-vs-actual             — budget vs. actual variance per event
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_production import (
    Event, WorkOrder, StaffAssignment,
    SalesInvoice, PurchaseOrder, VendorInvoice,
)
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/evn", tags=["EVN Events"])


# ── Pydantic models ────────────────────────────────────────────────────

class EventCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    event_code: str
    pnr_id: Optional[int] = None
    client_id: Optional[int] = None
    event_name: Optional[str] = None
    event_date: Optional[date] = None
    end_date: Optional[date] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    country: str = "EG"
    status: str = "OPEN"
    budget: float = 0.0
    gross_sales: float = 0.0
    currency: str = "EGP"
    notes: Optional[str] = None


class EventOut(EventCreate):
    id: int


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    wo_code: str
    event_id: Optional[int] = None
    department: Optional[str] = None
    task: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "PENDING"
    budget: float = 0.0
    actual_cost: float = 0.0
    currency: str = "EGP"


class WorkOrderOut(WorkOrderCreate):
    id: int


class StaffAssignmentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    staff_id: Optional[int] = None
    work_order_id: Optional[int] = None
    event_id: Optional[int] = None
    role: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    hours_planned: float = 0.0
    hours_actual: float = 0.0
    hourly_rate: float = 0.0
    total_cost: float = 0.0
    currency: str = "EGP"


class StaffAssignmentOut(StaffAssignmentCreate):
    id: int


class EVNSummary(BaseModel):
    total_events: int = 0
    open_events: int = 0
    closed_events: int = 0
    cancelled_events: int = 0
    total_budget: float = 0.0
    total_gross_sales: float = 0.0
    by_status: dict = {}


# ── Helpers ────────────────────────────────────────────────────────────

def _event_filters(client_id, pnr_id, status_, date_from, date_to, search):
    f = []
    if client_id is not None:
        f.append(Event.client_id == client_id)
    if pnr_id is not None:
        f.append(Event.pnr_id == pnr_id)
    if status_:
        f.append(Event.status == status_)
    if date_from:
        f.append(Event.event_date >= date_from)
    if date_to:
        f.append(Event.event_date <= date_to)
    if search:
        f.append(or_(
            Event.event_code.ilike(f"%{search}%"),
            Event.event_name.ilike(f"%{search}%"),
            Event.venue.ilike(f"%{search}%"),
            Event.city.ilike(f"%{search}%"),
        ))
    return f


# ── End-points ─────────────────────────────────────────────────────────

@router.get("/events", response_model=PaginatedResponse[EventOut])
async def list_events(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    client_id: Annotated[Optional[int], Query()] = None,
    pnr_id: Annotated[Optional[int], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(Event)
    f = _event_filters(client_id, pnr_id, status_, date_from, date_to, search)
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(Event.event_date), desc(Event.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[EventOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/events/{event_id}", response_model=dict)
async def get_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    ev = (await session.execute(
        select(Event).where(Event.id == event_id)
    )).scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "Event not found")
    wos = (await session.execute(
        select(WorkOrder).where(WorkOrder.event_id == event_id)
    )).scalars().all()
    sas = (await session.execute(
        select(StaffAssignment).where(StaffAssignment.event_id == event_id)
    )).scalars().all()
    return {
        "event": EventOut.model_validate(ev).model_dump(),
        "work_orders": [WorkOrderOut.model_validate(w).model_dump() for w in wos],
        "assignments": [StaffAssignmentOut.model_validate(s).model_dump() for s in sas],
        "work_order_count": len(wos),
        "assignment_count": len(sas),
    }


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    ev = Event(**payload.model_dump(exclude_unset=True))
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return EventOut.model_validate(ev)


@router.put("/events/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    payload: EventCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    ev = (await session.execute(
        select(Event).where(Event.id == event_id)
    )).scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "Event not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ev, k, v)
    await session.commit()
    await session.refresh(ev)
    return EventOut.model_validate(ev)


@router.get("/events/{event_id}/work-orders", response_model=List[WorkOrderOut])
async def event_work_orders(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rows = (await session.execute(
        select(WorkOrder)
        .where(WorkOrder.event_id == event_id)
        .order_by(WorkOrder.start_date)
    )).scalars().all()
    return [WorkOrderOut.model_validate(r) for r in rows]


@router.get("/events/{event_id}/assignments", response_model=List[StaffAssignmentOut])
async def event_assignments(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rows = (await session.execute(
        select(StaffAssignment)
        .where(StaffAssignment.event_id == event_id)
        .order_by(StaffAssignment.start_date)
    )).scalars().all()
    return [StaffAssignmentOut.model_validate(r) for r in rows]


@router.get("/events/{event_id}/financials", response_model=dict)
async def event_financials(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Event P&L: revenue (sales invoices) − cost (vendor invoices + staff cost)."""
    ev = (await session.execute(
        select(Event).where(Event.id == event_id)
    )).scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "Event not found")
    sales = (await session.execute(
        select(
            func.coalesce(func.sum(SalesInvoice.total), 0).label("revenue"),
            func.coalesce(func.sum(SalesInvoice.tax_amount), 0).label("tax"),
            func.coalesce(func.sum(SalesInvoice.paid_amount), 0).label("paid"),
            func.count().label("inv_count"),
        ).where(SalesInvoice.event_id == event_id)
    )).one()
    purchases = (await session.execute(
        select(
            func.coalesce(func.sum(VendorInvoice.total), 0).label("cost"),
            func.coalesce(func.sum(VendorInvoice.paid_amount), 0).label("paid"),
            func.count().label("inv_count"),
        ).where(VendorInvoice.event_id == event_id)
    )).one()
    staff_cost = (await session.execute(
        select(func.coalesce(func.sum(StaffAssignment.total_cost), 0))
        .where(StaffAssignment.event_id == event_id)
    )).scalar() or 0
    revenue = float(sales.revenue or 0)
    po_cost = float(purchases.cost or 0)
    total_cost = po_cost + float(staff_cost)
    margin = revenue - total_cost
    return {
        "event_id": event_id,
        "event_code": ev.event_code,
        "currency": ev.currency,
        "revenue": round(revenue, 2),
        "tax_collected": round(float(sales.tax or 0), 2),
        "amount_collected": round(float(sales.paid or 0), 2),
        "purchase_cost": round(po_cost, 2),
        "staff_cost": round(float(staff_cost), 2),
        "total_cost": round(total_cost, 2),
        "gross_margin": round(margin, 2),
        "margin_pct": round(margin / revenue * 100, 2) if revenue else 0.0,
        "budget": round(ev.budget or 0, 2),
        "budget_variance": round((ev.budget or 0) - revenue, 2),
        "sales_invoice_count": sales.inv_count or 0,
        "purchase_invoice_count": purchases.inv_count or 0,
    }


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderOut])
async def list_work_orders(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    event_id: Annotated[Optional[int], Query()] = None,
    department: Annotated[Optional[str], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(WorkOrder)
    f = []
    if event_id is not None:
        f.append(WorkOrder.event_id == event_id)
    if department:
        f.append(WorkOrder.department == department)
    if status_:
        f.append(WorkOrder.status == status_)
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(WorkOrder.start_date), desc(WorkOrder.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[WorkOrderOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/work-orders/{wo_id}", response_model=WorkOrderOut)
async def get_work_order(
    wo_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    wo = (await session.execute(
        select(WorkOrder).where(WorkOrder.id == wo_id)
    )).scalar_one_or_none()
    if not wo:
        raise HTTPException(404, "Work order not found")
    return WorkOrderOut.model_validate(wo)


@router.post("/work-orders", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    payload: WorkOrderCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    wo = WorkOrder(**payload.model_dump(exclude_unset=True))
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return WorkOrderOut.model_validate(wo)


@router.get("/assignments", response_model=PaginatedResponse[StaffAssignmentOut])
async def list_assignments(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    event_id: Annotated[Optional[int], Query()] = None,
    staff_id: Annotated[Optional[int], Query()] = None,
    work_order_id: Annotated[Optional[int], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(StaffAssignment)
    f = []
    if event_id is not None:
        f.append(StaffAssignment.event_id == event_id)
    if staff_id is not None:
        f.append(StaffAssignment.staff_id == staff_id)
    if work_order_id is not None:
        f.append(StaffAssignment.work_order_id == work_order_id)
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(StaffAssignment.start_date), desc(StaffAssignment.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[StaffAssignmentOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/assignments", response_model=StaffAssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: StaffAssignmentCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    # Auto-compute total_cost if not provided
    if not payload.total_cost and payload.hours_actual and payload.hourly_rate:
        payload.total_cost = payload.hours_actual * payload.hourly_rate
    sa = StaffAssignment(**payload.model_dump(exclude_unset=True))
    session.add(sa)
    await session.commit()
    await session.refresh(sa)
    return StaffAssignmentOut.model_validate(sa)


@router.get("/summary", response_model=EVNSummary)
async def get_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    head = (await session.execute(
        select(
            func.count().label("cnt"),
            func.coalesce(func.sum(Event.budget), 0).label("budget"),
            func.coalesce(func.sum(Event.gross_sales), 0).label("sales"),
        )
    )).one()
    status_rows = (await session.execute(
        select(Event.status, func.count().label("cnt"))
        .group_by(Event.status)
    )).all()
    by_status = {r.status: r.cnt for r in status_rows if r.status}
    return EVNSummary(
        total_events=head.cnt or 0,
        open_events=by_status.get("OPEN", 0),
        closed_events=by_status.get("CLOSED", 0),
        cancelled_events=by_status.get("CANCELLED", 0),
        total_budget=round(head.budget or 0, 2),
        total_gross_sales=round(head.sales or 0, 2),
        by_status=by_status,
    )


@router.get("/upcoming", response_model=List[EventOut])
async def upcoming_events(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
):
    from datetime import datetime as _dt
    today = _dt.utcnow().date()
    rows = (await session.execute(
        select(Event)
        .where(and_(Event.status == "OPEN", Event.event_date >= today))
        .order_by(Event.event_date)
        .limit(limit)
    )).scalars().all()
    return [EventOut.model_validate(r) for r in rows]


@router.get("/budget-vs-actual", response_model=List[dict])
async def budget_vs_actual(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    rows = (await session.execute(
        select(
            Event.id,
            Event.event_code,
            Event.event_name,
            Event.budget,
            Event.gross_sales,
        )
        .order_by(desc(Event.event_date))
        .limit(limit)
    )).all()
    result = []
    for r in rows:
        revenue_rows = (await session.execute(
            select(func.coalesce(func.sum(SalesInvoice.total), 0))
            .where(SalesInvoice.event_id == r.id)
        )).scalar() or 0
        cost_rows = (await session.execute(
            select(func.coalesce(func.sum(VendorInvoice.total), 0))
            .where(VendorInvoice.event_id == r.id)
        )).scalar() or 0
        budget = float(r.budget or 0)
        revenue = float(revenue_rows or 0)
        cost = float(cost_rows or 0)
        result.append({
            "event_id": r.id,
            "event_code": r.event_code,
            "event_name": r.event_name,
            "budget": round(budget, 2),
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "margin": round(revenue - cost, 2),
            "budget_variance": round(budget - revenue, 2),
            "budget_utilization_pct": round(revenue / budget * 100, 2) if budget else 0.0,
        })
    return result
