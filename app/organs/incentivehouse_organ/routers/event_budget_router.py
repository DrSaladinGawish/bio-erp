"""
Event Budget Router — Per-Event Budget Tracking
================================================
End-points (prefix ``/api/v1/event-budget``):

  GET  /lines                       — list all event budget lines (paginated, filterable)
  GET  /lines/{id}                  — single budget line
  POST /lines                       — create a new budget line
  PUT  /lines/{id}                  — update planned / actual / committed
  DELETE /lines/{id}                — delete a budget line
  GET  /by-event/{event_id}         — all lines for an event (with totals)
  GET  /summary                     — roll-up by category & by event (planned vs actual)
  GET  /profitability               — per-event profitability (planned revenue - planned cost + actuals)
  GET  /categories                  — distinct categories present

Table: ``event_budget_lines``
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_empty_modules import EventBudgetLine
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/event-budget", tags=["Event Budget"])


# ── Pydantic models ────────────────────────────────────────────────────


class EventBudgetLineCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    event_id: int
    pnr_id: Optional[int] = None
    category: str
    sub_category: Optional[str] = None
    planned_amount: float = 0.0
    actual_amount: float = 0.0
    committed_amount: float = 0.0
    currency: str = "EGP"
    notes: Optional[str] = None
    approved_by: Optional[str] = None


class EventBudgetLineUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    planned_amount: Optional[float] = None
    actual_amount: Optional[float] = None
    committed_amount: Optional[float] = None
    sub_category: Optional[str] = None
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    currency: Optional[str] = None


class EventBudgetLineOut(EventBudgetLineCreate):
    id: int
    variance: float = 0.0
    created_at: Optional[datetime] = None


class EventBudgetSummary(BaseModel):
    total_lines: int = 0
    total_planned: float = 0.0
    total_actual: float = 0.0
    total_committed: float = 0.0
    total_variance: float = 0.0
    by_category: dict = {}
    by_event: dict = {}


# ── Helpers ────────────────────────────────────────────────────────────


def _compute_variance(line: EventBudgetLine) -> float:
    """Variance = planned − actual. Positive = under budget."""
    return round((line.planned_amount or 0) - (line.actual_amount or 0), 2)


# ── End-points ─────────────────────────────────────────────────────────


@router.get("/lines", response_model=PaginatedResponse[EventBudgetLineOut])
async def list_budget_lines(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    event_id: Annotated[Optional[int], Query()] = None,
    pnr_id: Annotated[Optional[int], Query()] = None,
    category: Annotated[Optional[str], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    """List event budget lines, paginated and filterable."""
    stmt = select(EventBudgetLine)
    f = []
    if event_id is not None:
        f.append(EventBudgetLine.event_id == event_id)
    if pnr_id is not None:
        f.append(EventBudgetLine.pnr_id == pnr_id)
    if category:
        f.append(EventBudgetLine.category == category)
    if search:
        f.append(
            or_(
                EventBudgetLine.category.ilike(f"%{search}%"),
                EventBudgetLine.sub_category.ilike(f"%{search}%"),
                EventBudgetLine.notes.ilike(f"%{search}%"),
            )
        )
    if f:
        stmt = stmt.where(and_(*f))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(EventBudgetLine.event_id, EventBudgetLine.category)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[EventBudgetLineOut(
            **{k: v for k, v in EventBudgetLineOut.model_validate(r).model_dump().items() if k != "variance"},
            variance=_compute_variance(r),
        ) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/lines/{line_id}", response_model=EventBudgetLineOut)
async def get_budget_line(
    line_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Fetch a single event budget line."""
    row = (await session.execute(select(EventBudgetLine).where(EventBudgetLine.id == line_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Budget line {line_id} not found")
    out = EventBudgetLineOut.model_validate(row)
    out.variance = _compute_variance(row)
    return out


@router.post("/lines", response_model=EventBudgetLineOut, status_code=status.HTTP_201_CREATED)
async def create_budget_line(
    payload: EventBudgetLineCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Create a new event budget line."""
    line = EventBudgetLine(**payload.model_dump())
    session.add(line)
    await session.commit()
    await session.refresh(line)
    out = EventBudgetLineOut.model_validate(line)
    out.variance = _compute_variance(line)
    return out


@router.put("/lines/{line_id}", response_model=EventBudgetLineOut)
async def update_budget_line(
    line_id: int,
    payload: EventBudgetLineUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Update planned / actual / committed / notes on a budget line."""
    line = (await session.execute(select(EventBudgetLine).where(EventBudgetLine.id == line_id))).scalars().first()
    if not line:
        raise HTTPException(status_code=404, detail=f"Budget line {line_id} not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(line, k, v)
    await session.commit()
    await session.refresh(line)
    out = EventBudgetLineOut.model_validate(line)
    out.variance = _compute_variance(line)
    return out


@router.delete("/lines/{line_id}", response_model=dict)
async def delete_budget_line(
    line_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Delete a budget line."""
    line = (await session.execute(select(EventBudgetLine).where(EventBudgetLine.id == line_id))).scalars().first()
    if not line:
        raise HTTPException(status_code=404, detail=f"Budget line {line_id} not found")
    await session.delete(line)
    await session.commit()
    return {"id": line_id, "status": "deleted"}


@router.get("/by-event/{event_id}", response_model=dict)
async def by_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """All lines for an event plus totals (planned/actual/committed/variance)."""
    stmt = select(EventBudgetLine).where(EventBudgetLine.event_id == event_id).order_by(EventBudgetLine.category)
    rows = (await session.execute(stmt)).scalars().all()
    if not rows:
        return {"event_id": event_id, "lines": [], "totals": {"planned": 0, "actual": 0, "committed": 0, "variance": 0}}
    planned = sum(r.planned_amount or 0 for r in rows)
    actual = sum(r.actual_amount or 0 for r in rows)
    committed = sum(r.committed_amount or 0 for r in rows)
    return {
        "event_id": event_id,
        "lines": [
            {
                **{k: v for k, v in EventBudgetLineOut.model_validate(r).model_dump().items() if k != "variance"},
                "variance": _compute_variance(r),
            } for r in rows
        ],
        "totals": {
            "planned": round(planned, 2),
            "actual": round(actual, 2),
            "committed": round(committed, 2),
            "variance": round(planned - actual, 2),
        },
    }


@router.get("/summary", response_model=EventBudgetSummary)
async def budget_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Roll-up across all events: by category & by event."""
    total = (await session.execute(select(func.count(EventBudgetLine.id)))).scalar() or 0
    planned = (await session.execute(select(func.coalesce(func.sum(EventBudgetLine.planned_amount), 0.0)))).scalar() or 0
    actual = (await session.execute(select(func.coalesce(func.sum(EventBudgetLine.actual_amount), 0.0)))).scalar() or 0
    committed = (await session.execute(select(func.coalesce(func.sum(EventBudgetLine.committed_amount), 0.0)))).scalar() or 0
    # by category
    by_cat: dict = {}
    rows = (await session.execute(
        select(
            EventBudgetLine.category,
            func.coalesce(func.sum(EventBudgetLine.planned_amount), 0.0),
            func.coalesce(func.sum(EventBudgetLine.actual_amount), 0.0),
            func.coalesce(func.sum(EventBudgetLine.committed_amount), 0.0),
        ).group_by(EventBudgetLine.category)
    )).all()
    for cat, p, a, c in rows:
        by_cat[cat or "UNCATEGORIZED"] = {
            "planned": float(p or 0), "actual": float(a or 0), "committed": float(c or 0),
        }
    # by event
    by_event: dict = {}
    rows = (await session.execute(
        select(
            EventBudgetLine.event_id,
            func.coalesce(func.sum(EventBudgetLine.planned_amount), 0.0),
            func.coalesce(func.sum(EventBudgetLine.actual_amount), 0.0),
            func.coalesce(func.sum(EventBudgetLine.committed_amount), 0.0),
        ).group_by(EventBudgetLine.event_id)
    )).all()
    for ev, p, a, c in rows:
        by_event[str(ev)] = {
            "planned": float(p or 0), "actual": float(a or 0), "committed": float(c or 0),
        }
    return EventBudgetSummary(
        total_lines=total,
        total_planned=float(planned),
        total_actual=float(actual),
        total_committed=float(committed),
        total_variance=round(float(planned) - float(actual), 2),
        by_category=by_cat,
        by_event=by_event,
    )


@router.get("/profitability", response_model=List[dict])
async def profitability(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Per-event profitability: revenue planned/actual minus cost planned/actual.
    Convention: REVENUE* categories are revenue, anything else is cost.
    """
    rows = (await session.execute(
        select(
            EventBudgetLine.event_id,
            EventBudgetLine.category,
            func.coalesce(func.sum(EventBudgetLine.planned_amount), 0.0),
            func.coalesce(func.sum(EventBudgetLine.actual_amount), 0.0),
        ).group_by(EventBudgetLine.event_id, EventBudgetLine.category)
    )).all()

    # bucket per event
    by_ev: dict = {}
    for ev, cat, p, a in rows:
        ev = int(ev)
        cat = (cat or "").upper()
        if ev not in by_ev:
            by_ev[ev] = {"event_id": ev, "revenue_planned": 0.0, "revenue_actual": 0.0,
                         "cost_planned": 0.0, "cost_actual": 0.0}
        if "REVENUE" in cat or "INCOME" in cat:
            by_ev[ev]["revenue_planned"] += float(p or 0)
            by_ev[ev]["revenue_actual"] += float(a or 0)
        else:
            by_ev[ev]["cost_planned"] += float(p or 0)
            by_ev[ev]["cost_actual"] += float(a or 0)

    out = []
    for ev, v in by_ev.items():
        out.append({
            "event_id": ev,
            "revenue_planned": round(v["revenue_planned"], 2),
            "revenue_actual": round(v["revenue_actual"], 2),
            "cost_planned": round(v["cost_planned"], 2),
            "cost_actual": round(v["cost_actual"], 2),
            "margin_planned": round(v["revenue_planned"] - v["cost_planned"], 2),
            "margin_actual": round(v["revenue_actual"] - v["cost_actual"], 2),
        })
    out.sort(key=lambda x: x["margin_actual"], reverse=True)
    return out


@router.get("/categories", response_model=List[str])
async def distinct_categories(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Distinct list of budget categories present."""
    stmt = select(EventBudgetLine.category).distinct().order_by(EventBudgetLine.category)
    rows = (await session.execute(stmt)).scalars().all()
    return [r for r in rows if r]
