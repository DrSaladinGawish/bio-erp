from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models import Event, EventOperation, LifecycleStatus, Staff
from app.models.auth import User
from app.services.event_recognition_service import EventRecognitionService

router = APIRouter(prefix="/api/v1/event-ops", tags=["Event Operations"])


# ── Ops Dashboard ──────────────────────────────────────────────────


@router.get("/dashboard")
async def ops_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    today_count = await db.scalar(
        select(func.count(Event.id)).where(
            Event.lifecycle_status.in_(
                [LifecycleStatus.IN_PROGRESS.value, LifecycleStatus.EXECUTED.value]
            ),
            Event.execution_date.isnot(None),
            func.date(Event.execution_date) == func.current_date(),
        )
    ) or 0

    week_count = await db.scalar(
        select(func.count(Event.id)).where(
            Event.lifecycle_status == LifecycleStatus.CONFIRMED.value,
            Event.execution_date.isnot(None),
        )
    ) or 0

    pending_briefings = await db.scalar(
        select(func.count(EventOperation.id)).where(
            EventOperation.briefing_completed == False
        )
    ) or 0

    missing_briefings = await db.scalar(
        select(func.count(Event.id)).where(
            Event.lifecycle_status == LifecycleStatus.CONFIRMED.value,
            ~Event.id.in_(select(EventOperation.event_id)),
        )
    ) or 0

    resource_conflicts = 0

    todays_events = await db.execute(
        select(Event)
        .where(
            Event.lifecycle_status.in_(
                [LifecycleStatus.IN_PROGRESS.value, LifecycleStatus.EXECUTED.value]
            ),
            func.date(Event.execution_date) == func.current_date(),
        )
        .limit(10)
    )

    return {
        "today_count": today_count,
        "week_count": week_count,
        "pending_briefings": pending_briefings + missing_briefings,
        "resource_conflicts": resource_conflicts,
        "todays_events": [
            {
                "id": e.id,
                "event_code": e.event_code,
                "name_en": e.name_en,
                "venue": e.venue,
                "execution_date": e.execution_date.isoformat() if e.execution_date else None,
                "lifecycle_status": e.lifecycle_status,
                "actual_pax": e.actual_pax,
            }
            for e in todays_events.scalars().all()
        ],
    }


# ── Ops Briefing ───────────────────────────────────────────────────


@router.get("/briefing/{event_id}")
async def get_ops_briefing(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    ops = await db.execute(
        select(EventOperation).where(EventOperation.event_id == event_id)
    )
    briefing = ops.scalar_one_or_none()
    if not briefing:
        raise HTTPException(404, detail="Ops briefing not found")
    return {
        "id": briefing.id,
        "event_id": briefing.event_id,
        "ops_manager_id": briefing.ops_manager_id,
        "briefing_completed": briefing.briefing_completed,
        "load_in_time": briefing.load_in_time.isoformat() if briefing.load_in_time else None,
        "sound_check_done": briefing.sound_check_done,
        "catering_final_count": briefing.catering_final_count,
        "run_sheet": briefing.run_sheet,
        "post_event_notes": briefing.post_event_notes,
        "client_signatory_name": briefing.client_signatory_name,
    }


@router.post("/briefing/{event_id}")
async def create_or_update_briefing(
    event_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.update")),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, detail="Event not found")

    ops = await db.execute(
        select(EventOperation).where(EventOperation.event_id == event_id)
    )
    briefing = ops.scalar_one_or_none()

    if not briefing:
        briefing = EventOperation(event_id=event_id)
        db.add(briefing)

    briefing.ops_manager_id = payload.get("ops_manager_id", briefing.ops_manager_id)
    briefing.briefing_completed = payload.get("briefing_completed", briefing.briefing_completed)
    briefing.load_in_time = payload.get("load_in_time", briefing.load_in_time)
    briefing.sound_check_done = payload.get("sound_check_done", briefing.sound_check_done)
    briefing.catering_final_count = payload.get("catering_final_count", briefing.catering_final_count)
    briefing.run_sheet = payload.get("run_sheet", briefing.run_sheet)
    briefing.post_event_notes = payload.get("post_event_notes", briefing.post_event_notes)
    briefing.client_signatory_name = payload.get("client_signatory_name", briefing.client_signatory_name)
    briefing.client_signature_path = payload.get("client_signature_path", briefing.client_signature_path)

    await db.commit()
    await db.refresh(briefing)

    return {"status": "ok", "id": briefing.id}


# ── Run Sheet ──────────────────────────────────────────────────────


@router.get("/run-sheet/{event_id}")
async def get_run_sheet(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    ops = await db.execute(
        select(EventOperation).where(EventOperation.event_id == event_id)
    )
    briefing = ops.scalar_one_or_none()
    if not briefing:
        raise HTTPException(404, detail="Ops briefing not found for this event")
    return {"event_id": event_id, "run_sheet": briefing.run_sheet or []}


@router.put("/run-sheet/{event_id}")
async def update_run_sheet(
    event_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.update")),
):
    ops = await db.execute(
        select(EventOperation).where(EventOperation.event_id == event_id)
    )
    briefing = ops.scalar_one_or_none()
    if not briefing:
        raise HTTPException(404, detail="Ops briefing not found for this event")

    briefing.run_sheet = payload.get("run_sheet", briefing.run_sheet)
    await db.commit()
    return {"status": "ok", "event_id": event_id}


# ── Post-Event Report ──────────────────────────────────────────────


@router.post("/post-event/{event_id}")
async def submit_post_event_report(
    event_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.update")),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, detail="Event not found")

    ops = await db.execute(
        select(EventOperation).where(EventOperation.event_id == event_id)
    )
    briefing = ops.scalar_one_or_none()

    if not briefing:
        briefing = EventOperation(event_id=event_id)
        db.add(briefing)

    briefing.post_event_notes = payload.get("post_event_notes", briefing.post_event_notes)
    briefing.client_signatory_name = payload.get("client_signatory_name", briefing.client_signatory_name)
    briefing.client_signature_path = payload.get("client_signature_path", briefing.client_signature_path)

    event.actual_pax = payload.get("actual_pax", event.actual_pax)
    event.actual_cost = payload.get("actual_cost", event.actual_cost)

    new_status = payload.get("lifecycle_status")
    if new_status and new_status in [s.value for s in LifecycleStatus]:
        event.lifecycle_status = new_status

    await db.commit()
    return {"status": "ok", "event_id": event_id}


# ── Lifecycle Transitions ──────────────────────────────────────────


@router.post("/lifecycle/{event_id}")
async def transition_lifecycle(
    event_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.update")),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, detail="Event not found")

    new_status = payload.get("lifecycle_status", "")
    valid_statuses = [s.value for s in LifecycleStatus]
    if new_status not in valid_statuses:
        raise HTTPException(400, detail=f"Invalid lifecycle status. Must be one of: {', '.join(valid_statuses)}")

    event.lifecycle_status = new_status
    if new_status == LifecycleStatus.IN_PROGRESS.value:
        event.execution_date = payload.get("execution_date", datetime.utcnow())
    await db.commit()

    return {
        "status": "ok",
        "event_id": event_id,
        "lifecycle_status": event.lifecycle_status,
    }


# ── Recognition ────────────────────────────────────────────────────


@router.get("/recognition/suggest-services")
async def suggest_services(
    client_id: int = Query(...),
    category_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    result = await EventRecognitionService.suggest_services(
        db=db, client_id=client_id, category_id=category_id
    )
    return result


@router.get("/recognition/validate-capacity")
async def validate_capacity(
    event_name: str | None = Query(None),
    pax: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    result = await EventRecognitionService.validate_capacity(
        db=db, event_name=event_name, pax=pax
    )
    return result
