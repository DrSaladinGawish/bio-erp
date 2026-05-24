import json
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.models.event_management import (
    EventLog,
    BranchEventSummary,
    MigrationStatus,
)
from app.services.event_bridge import EventBridge

router = APIRouter(prefix="/api/v1/events", tags=["Events"])

_active_ws: list[WebSocket] = []


@router.post("/receive")
async def receive_event(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    event = await EventBridge.sync_web_to_local(db, payload)
    await db.commit()
    await _broadcast_event(event)
    return {"status": "received", "event_id": event.event_id}


@router.get("")
async def list_events(
    branch_id: int | None = Query(None),
    severity: str | None = Query(None),
    source_component: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(EventLog).order_by(EventLog.timestamp.desc())
    if branch_id:
        q = q.where(EventLog.branch_id == branch_id)
    if severity:
        q = q.where(EventLog.severity == severity)
    if source_component:
        q = q.where(EventLog.source_component == source_component)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    events = result.scalars().all()

    count_q = select(func.count(EventLog.id))
    if branch_id:
        count_q = count_q.where(EventLog.branch_id == branch_id)
    if severity:
        count_q = count_q.where(EventLog.severity == severity)
    total = await db.scalar(count_q) or 0

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "source_system": e.source_system,
                "source_component": e.source_component,
                "source_id": e.source_id,
                "branch_id": e.branch_id,
                "user_id": e.user_id,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "payload": e.payload,
                "handled": e.handled,
                "migration_status": e.migration_status,
            }
            for e in events
        ],
    }


@router.get("/branch-summary")
async def branch_event_summary(
    branch_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(BranchEventSummary).order_by(BranchEventSummary.date.desc())
    if branch_id:
        q = q.where(BranchEventSummary.branch_id == branch_id)
    result = await db.execute(q)
    summaries = result.scalars().all()
    return [
        {
            "branch_id": s.branch_id,
            "date": s.date.isoformat() if s.date else None,
            "total_events": s.total_events,
            "critical_count": s.critical_count,
            "warning_count": s.warning_count,
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
        }
        for s in summaries
    ]


@router.get("/sync-status")
async def sync_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total = await db.scalar(select(func.count(EventLog.id))) or 0
    pending = (
        await db.scalar(
            select(func.count(EventLog.id)).where(
                EventLog.migration_status == MigrationStatus.pending.value
            )
        )
        or 0
    )
    synced = (
        await db.scalar(
            select(func.count(EventLog.id)).where(
                EventLog.migration_status == MigrationStatus.synced.value
            )
        )
        or 0
    )
    failed = (
        await db.scalar(
            select(func.count(EventLog.id)).where(
                EventLog.migration_status == MigrationStatus.failed.value
            )
        )
        or 0
    )

    pct = round(synced / total * 100, 1) if total else 100.0
    if failed > 0:
        status = "degraded"
    elif pending > 0:
        status = "syncing"
    elif pct >= 100:
        status = "healthy"
    else:
        status = "syncing"

    return {
        "status": status,
        "total": total,
        "pending": pending,
        "synced": synced,
        "failed": failed,
        "sync_pct": pct,
    }


@router.get("/pipeline")
async def events_pipeline(
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pending = await db.execute(
        select(EventLog)
        .where(EventLog.migration_status == MigrationStatus.pending.value)
        .order_by(EventLog.timestamp.desc())
        .limit(limit)
    )
    synced = await db.execute(
        select(EventLog)
        .where(EventLog.migration_status == MigrationStatus.synced.value)
        .order_by(EventLog.timestamp.desc())
        .limit(limit)
    )
    failed = await db.execute(
        select(EventLog)
        .where(EventLog.migration_status == MigrationStatus.failed.value)
        .order_by(EventLog.timestamp.desc())
        .limit(limit)
    )
    return [
        {
            "status": "pending",
            "events": [_serialize_event(e) for e in pending.scalars().all()],
        },
        {
            "status": "synced",
            "events": [_serialize_event(e) for e in synced.scalars().all()],
        },
        {
            "status": "failed",
            "events": [_serialize_event(e) for e in failed.scalars().all()],
        },
    ]


def _serialize_event(e: EventLog) -> dict:
    return {
        "event_id": e.event_id,
        "event_type": e.event_type,
        "source_system": e.source_system,
        "source_component": e.source_component,
        "source_id": e.source_id,
        "branch_id": e.branch_id,
        "user_id": e.user_id,
        "severity": e.severity,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "payload": e.payload,
        "handled": e.handled,
        "migration_status": e.migration_status,
    }


@router.post("/sync-trigger")
async def sync_trigger(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await EventBridge.sync_local_to_web(db)
    return {"triggered": True, "synced_count": count}


@router.websocket("/ws/events")
async def event_websocket(websocket: WebSocket):
    await websocket.accept()
    _active_ws.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("ping"):
                await websocket.send_json({"pong": True})
    except WebSocketDisconnect:
        if websocket in _active_ws:
            _active_ws.remove(websocket)


async def _broadcast_event(event: EventLog):
    dead = []
    payload = {
        "type": "event",
        "event_id": event.event_id,
        "event_type": event.event_type,
        "source_component": event.source_component,
        "branch_id": event.branch_id,
        "severity": event.severity,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "payload": event.payload,
    }
    for ws in _active_ws:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _active_ws.remove(ws)
