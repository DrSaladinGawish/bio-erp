"""
Event Operations Router — v2.5.0 Event Lifecycle
=================================================
Endpoints (prefix ``/api/v1/event-ops``):

  GET  /dashboard                — ops team KPIs + today's events
  GET  /briefing/{event_id}      — get ops briefing
  POST /briefing/{event_id}      — create/update ops briefing
  GET  /run-sheet/{event_id}     — get minute-by-minute run sheet
  PUT  /run-sheet/{event_id}     — update run sheet
  POST /post-event/{event_id}    — submit post-event report
  POST /lifecycle/{event_id}     — transition lifecycle status
  GET  /recognition/suggest-services  — auto-suggest services from client history
  GET  /recognition/validate-capacity — validate venue capacity
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.event import Event, EventOperation

LIFECYCLE_STATUSES = [
    "DRAFT",
    "QUOTED",
    "CONFIRMED",
    "PLANNING",
    "IN_PROGRESS",
    "EXECUTED",
    "INVOICED",
    "CLOSED",
]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/event-ops", tags=["Event Operations"])


# ── Pydantic schemas ────────────────────────────────────────────────


class BriefingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    exists: bool
    briefing: Optional[dict] = None


class RunSheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    run_sheet: list = []
    last_updated: Optional[str] = None


class PostEventIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    actual_pax: Optional[int] = None
    actual_cost: Optional[float] = None
    notes: Optional[str] = None
    client_signatory: Optional[str] = None


class LifecycleTransition(BaseModel):
    status: str


# ── Summary & List ──────────────────────────────────────────────────


@router.get("/summary")
async def ops_summary(session: Annotated[AsyncSession, Depends(get_db)]):
    total = (await session.execute(select(func.count(Event.id)))).scalar() or 0
    active = (await session.execute(
        select(func.count(Event.id)).where(Event.lifecycle_status.notin_(["CLOSED", "DRAFT"]))
    )).scalar() or 0
    return {"total_operations": total, "active_operations": active}


@router.get("/list")
async def ops_list(session: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await session.execute(
        select(Event.id, Event.name_en, Event.venue, Event.lifecycle_status, Event.start_date)
        .order_by(Event.start_date.desc())
        .limit(100)
    )).all()
    return {
        "data": [
            {
                "event_id": r.id,
                "task_name": r.name_en,
                "assigned_to": r.venue or "-",
                "status": r.lifecycle_status or "DRAFT",
            }
            for r in rows
        ]
    }


# ── Ops Dashboard ───────────────────────────────────────────────────


@router.get("/dashboard")
async def ops_dashboard(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    today_ = date.today()
    today_str = today_.isoformat()

    today_events = (
        (
            await session.execute(
                select(Event).where(
                    Event.start_date == today_str,
                    Event.lifecycle_status.in_(
                        ["PLANNING", "IN_PROGRESS", "CONFIRMED"]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )

    week_count = (
        await session.execute(
            select(func.count(Event.id)).where(
                Event.start_date >= today_str,
                Event.lifecycle_status.in_(["CONFIRMED", "PLANNING", "IN_PROGRESS"]),
            )
        )
    ).scalar() or 0

    confirmed = (
        (
            await session.execute(
                select(Event).where(Event.lifecycle_status == "CONFIRMED")
            )
        )
        .scalars()
        .all()
    )

    pending_briefings = 0
    for e in confirmed:
        ops = (
            await session.execute(
                select(EventOperation).where(EventOperation.event_id == e.id)
            )
        ).scalar_one_or_none()
        if not ops or not ops.briefing_completed:
            pending_briefings += 1

    pipeline = {}
    for st in LIFECYCLE_STATUSES:
        cnt = (
            await session.execute(
                select(func.count(Event.id)).where(Event.lifecycle_status == st)
            )
        ).scalar() or 0
        pipeline[st] = cnt

    total_active = (
        await session.execute(
            select(func.count(Event.id)).where(
                Event.lifecycle_status.notin_(["CLOSED", "DRAFT"])
            )
        )
    ).scalar() or 0

    return {
        "today_count": len(today_events),
        "today_events": [
            {
                "id": e.id,
                "name": e.name_en,
                "venue": e.venue,
                "status": e.lifecycle_status or e.status,
            }
            for e in today_events
        ],
        "week_count": week_count,
        "pending_briefings": pending_briefings,
        "pipeline": pipeline,
        "total_active": total_active,
    }


# ── Ops Briefing ────────────────────────────────────────────────────


@router.get("/briefing/{event_id}")
async def get_briefing(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    event = (
        await session.execute(select(Event).where(Event.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Event not found")

    ops = (
        await session.execute(
            select(EventOperation).where(EventOperation.event_id == event_id)
        )
    ).scalar_one_or_none()

    if not ops:
        return {"event_id": event_id, "exists": False, "briefing": None}

    return {
        "event_id": event_id,
        "exists": True,
        "briefing": {
            "ops_manager_id": ops.ops_manager_id,
            "briefing_completed": ops.briefing_completed,
            "load_in_time": ops.load_in_time.isoformat() if ops.load_in_time else None,
            "sound_check_done": ops.sound_check_done,
            "catering_final_count": ops.catering_final_count,
            "run_sheet": ops.run_sheet or [],
            "post_event_notes": ops.post_event_notes,
            "client_signatory": ops.client_signatory_name,
        },
    }


@router.post("/briefing/{event_id}")
async def create_briefing(
    event_id: int,
    data: dict,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    event = (
        await session.execute(select(Event).where(Event.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Event not found")

    ops = (
        await session.execute(
            select(EventOperation).where(EventOperation.event_id == event_id)
        )
    ).scalar_one_or_none()

    if not ops:
        ops = EventOperation(event_id=event_id)
        session.add(ops)

    if "ops_manager_id" in data:
        ops.ops_manager_id = data["ops_manager_id"]
    if "briefing_completed" in data:
        ops.briefing_completed = data["briefing_completed"]
    if "load_in_time" in data and data["load_in_time"]:
        ops.load_in_time = datetime.fromisoformat(data["load_in_time"])
    if "sound_check_done" in data:
        ops.sound_check_done = data["sound_check_done"]
    if "catering_final_count" in data:
        ops.catering_final_count = data["catering_final_count"]

    await session.commit()
    return {
        "status": "saved",
        "event_id": event_id,
        "briefing_completed": ops.briefing_completed,
    }


# ── Run Sheet ───────────────────────────────────────────────────────


@router.get("/run-sheet/{event_id}")
async def get_run_sheet(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ops = (
        await session.execute(
            select(EventOperation).where(EventOperation.event_id == event_id)
        )
    ).scalar_one_or_none()
    if not ops:
        raise HTTPException(404, "No operations record for this event")

    return {
        "event_id": event_id,
        "run_sheet": ops.run_sheet or [],
        "last_updated": ops.updated_at.isoformat() if ops.updated_at else None,
    }


@router.put("/run-sheet/{event_id}")
async def update_run_sheet(
    event_id: int,
    data: dict,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ops = (
        await session.execute(
            select(EventOperation).where(EventOperation.event_id == event_id)
        )
    ).scalar_one_or_none()
    if not ops:
        raise HTTPException(404, "No operations record")

    ops.run_sheet = data.get("run_sheet", [])
    await session.commit()
    return {"status": "updated", "items": len(ops.run_sheet) if ops.run_sheet else 0}


# ── Post-Event Report ───────────────────────────────────────────────


@router.post("/post-event/{event_id}")
async def post_event_report(
    event_id: int,
    data: PostEventIn,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    event = (
        await session.execute(select(Event).where(Event.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Event not found")

    ops = (
        await session.execute(
            select(EventOperation).where(EventOperation.event_id == event_id)
        )
    ).scalar_one_or_none()
    if not ops:
        raise HTTPException(400, "No ops briefing exists — create briefing first")

    if data.actual_pax is not None:
        event.actual_pax = data.actual_pax
    if data.actual_cost is not None:
        event.actual_cost = data.actual_cost
    if data.notes is not None:
        ops.post_event_notes = data.notes
    if data.client_signatory is not None:
        ops.client_signatory_name = data.client_signatory

    event.lifecycle_status = "EXECUTED"
    event.status = "COMPLETED"

    await session.commit()
    return {
        "status": "EXECUTED",
        "event_id": event_id,
        "actual_pax": event.actual_pax,
        "actual_cost": float(event.actual_cost) if event.actual_cost else None,
    }


# ── Lifecycle Transition ────────────────────────────────────────────

VALID_TRANSITIONS = {
    "DRAFT": ["QUOTED"],
    "QUOTED": ["CONFIRMED", "DRAFT"],
    "CONFIRMED": ["PLANNING", "CANCELLED"],
    "PLANNING": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["EXECUTED", "CANCELLED"],
    "EXECUTED": ["INVOICED"],
    "INVOICED": ["CLOSED"],
    "CLOSED": [],
}


@router.post("/lifecycle/{event_id}")
async def transition_lifecycle(
    event_id: int,
    data: LifecycleTransition,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    event = (
        await session.execute(select(Event).where(Event.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Event not found")

    new_status = data.status.upper()
    if new_status not in LIFECYCLE_STATUSES:
        raise HTTPException(
            400, f"Invalid status. Must be one of: {LIFECYCLE_STATUSES}"
        )

    current = (event.lifecycle_status or "DRAFT").upper()
    allowed = VALID_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise HTTPException(
            400,
            f"Cannot transition from {current} to {new_status}. Allowed: {allowed}",
        )

    event.lifecycle_status = new_status
    await session.commit()
    return {"event_id": event_id, "old_status": current, "new_status": new_status}


# ── Auto-Recognition ────────────────────────────────────────────────


@router.get("/recognition/suggest-services")
async def suggest_services(
    client_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    category_id: int = 0,
):
    from app.models.ihe_models import SalesInvoice, SalesInvoiceLine as SalesLineItem

    rows = (
        await session.execute(
            select(
                SalesLineItem.description,
                SalesLineItem.quantity,
                SalesLineItem.unit_price,
                SalesLineItem.item_code,
            )
            .select_from(SalesLineItem)
            .join(SalesInvoice, SalesLineItem.invoice_id == SalesInvoice.id)
            .where(SalesInvoice.client_id == client_id)
            .order_by(SalesInvoice.invoice_date.desc())
            .limit(5)
        )
    ).all()

    history = [
        {
            "service": r.description or r.item_code,
            "qty": float(r.quantity or 0),
            "price": float(r.unit_price or 0),
        }
        for r in rows
    ]

    from app.models.event import ServiceUOM

    defaults_raw = (
        (
            await session.execute(
                select(ServiceUOM).where(
                    ServiceUOM.category_id
                    == (category_id if category_id else ServiceUOM.category_id),
                    ServiceUOM.is_active,
                )
            )
        )
        .scalars()
        .all()
    )

    defaults = [
        {
            "uom": d.uom_code,
            "name": d.uom_name,
            "default_price": float(d.default_unit_price)
            if d.default_unit_price
            else None,
        }
        for d in defaults_raw
    ]

    return {
        "client_id": client_id,
        "client_history": history,
        "category_defaults": defaults,
    }


@router.get("/recognition/validate-capacity")
async def validate_capacity(
    venue: str,
    pax: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    past = (
        await session.execute(
            select(Event.actual_pax).where(
                and_(Event.venue == venue, Event.actual_pax.isnot(None))
            )
        )
    ).all()

    values = [r[0] for r in past if r[0]]
    max_observed = max(values) if values else 0
    avg_observed = sum(values) / len(values) if values else 0
    status = "OK" if not values or pax <= max_observed * 1.2 else "WARNING"

    return {
        "venue": venue,
        "requested_pax": pax,
        "max_observed": max_observed,
        "avg_observed": round(avg_observed, 1),
        "status": status,
        "suggestion": "Consider larger venue or adjust pax"
        if status == "WARNING"
        else None,
    }
