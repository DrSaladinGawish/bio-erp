import logging
from datetime import date, datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_management import (
    EventLog,
    BranchEventSummary,
    EventType,
    SourceSystem,
    SourceComponent,
    Severity,
    MigrationStatus,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.utcnow()


class EventBridge:
    @staticmethod
    async def emit(
        db: AsyncSession,
        event_type: EventType,
        source_component: SourceComponent,
        *,
        source_id: str | None = None,
        branch_id: int | None = None,
        user_id: int | None = None,
        severity: Severity = Severity.info,
        payload: dict | None = None,
        source_system: SourceSystem = SourceSystem.local_bio,
    ) -> EventLog:
        event = EventLog(
            event_type=event_type.value,
            source_system=source_system.value,
            source_component=source_component.value,
            source_id=source_id,
            branch_id=branch_id,
            user_id=user_id,
            severity=severity.value,
            timestamp=_utcnow(),
            payload=payload,
            migration_status=MigrationStatus.pending.value,
        )
        db.add(event)
        await db.flush()
        await EventBridge._update_branch_summary(db, branch_id)
        return event

    @staticmethod
    async def _update_branch_summary(db: AsyncSession, branch_id: int | None) -> None:
        if branch_id is None:
            return
        today = date.today()
        stmt = select(BranchEventSummary).where(
            and_(
                BranchEventSummary.branch_id == branch_id,
                BranchEventSummary.date == today,
            )
        )
        result = await db.execute(stmt)
        summary = result.scalar_one_or_none()
        if not summary:
            summary = BranchEventSummary(
                branch_id=branch_id,
                date=today,
                total_events=0,
                critical_count=0,
                warning_count=0,
            )
            db.add(summary)
            await db.flush()

        summary.total_events = (
            await db.scalar(
                select(func.count(EventLog.id)).where(
                    and_(
                        EventLog.branch_id == branch_id,
                        func.date(EventLog.timestamp) == today,
                    )
                )
            )
        ) or 0
        summary.critical_count = (
            await db.scalar(
                select(func.count(EventLog.id)).where(
                    and_(
                        EventLog.branch_id == branch_id,
                        func.date(EventLog.timestamp) == today,
                        EventLog.severity == Severity.critical.value,
                    )
                )
            )
        ) or 0
        summary.warning_count = (
            await db.scalar(
                select(func.count(EventLog.id)).where(
                    and_(
                        EventLog.branch_id == branch_id,
                        func.date(EventLog.timestamp) == today,
                        EventLog.severity == Severity.warning.value,
                    )
                )
            )
        ) or 0
        summary.last_sync_at = _utcnow()

    @staticmethod
    async def sync_local_to_web(
        db: AsyncSession,
        web_api_url: str = "http://localhost:8000/api/v1/events/receive",
    ) -> int:
        import httpx

        stmt = (
            select(EventLog)
            .where(
                EventLog.migration_status == MigrationStatus.pending.value,
                EventLog.source_system == SourceSystem.local_bio.value,
            )
            .order_by(EventLog.timestamp)
            .limit(100)
        )

        result = await db.execute(stmt)
        events = result.scalars().all()
        synced = 0

        for event in events:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        web_api_url,
                        json={
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "source_system": event.source_system,
                            "source_component": event.source_component,
                            "source_id": event.source_id,
                            "branch_id": event.branch_id,
                            "user_id": event.user_id,
                            "severity": event.severity,
                            "timestamp": event.timestamp.isoformat(),
                            "payload": event.payload,
                        },
                    )
                    if resp.status_code == 200:
                        event.migration_status = MigrationStatus.synced.value
                        event.handled = True
                        synced += 1
                    else:
                        event.migration_status = MigrationStatus.failed.value
            except Exception as e:
                logger.warning(f"Sync failed for event {event.event_id}: {e}")
                event.migration_status = MigrationStatus.failed.value

        await db.commit()
        return synced

    @staticmethod
    async def sync_web_to_local(
        db: AsyncSession,
        payload: dict,
    ) -> EventLog:
        event = EventLog(
            event_id=payload.get("event_id"),
            event_type=payload.get("event_type", EventType.sync.value),
            source_system=SourceSystem.web_api.value,
            source_component=SourceComponent.api.value,
            source_id=payload.get("source_id"),
            branch_id=payload.get("branch_id"),
            user_id=payload.get("user_id"),
            severity=payload.get("severity", Severity.info.value),
            timestamp=datetime.fromisoformat(payload["timestamp"])
            if "timestamp" in payload
            else _utcnow(),
            payload=payload.get("payload"),
            migration_status=MigrationStatus.synced.value,
            handled=True,
        )
        db.add(event)
        await db.flush()
        await EventBridge._update_branch_summary(db, payload.get("branch_id"))
        return event

    @staticmethod
    async def branch_event_aggregator(
        db: AsyncSession,
        branch_id: int | None = None,
        since: datetime | None = None,
    ) -> list[dict]:
        q = select(
            func.date(EventLog.timestamp).label("event_date"),
            EventLog.severity,
            func.count(EventLog.id).label("count"),
        )
        if branch_id:
            q = q.where(EventLog.branch_id == branch_id)
        if since:
            q = q.where(EventLog.timestamp >= since)
        q = q.group_by(func.date(EventLog.timestamp), EventLog.severity).order_by(
            func.date(EventLog.timestamp).desc()
        )

        result = await db.execute(q)
        rows = result.all()
        summary: dict[str, dict] = {}
        for row in rows:
            d = str(row.event_date)
            if d not in summary:
                summary[d] = {
                    "date": d,
                    "info": 0,
                    "warning": 0,
                    "critical": 0,
                    "total": 0,
                }
            summary[d][row.severity] = row.count
            summary[d]["total"] += row.count

        return sorted(summary.values(), key=lambda x: x["date"], reverse=True)

    @staticmethod
    async def conflict_resolution(
        existing: EventLog,
        incoming: dict,
    ) -> dict:
        existing_ts = (
            existing.timestamp.replace(tzinfo=timezone.utc)
            if existing.timestamp
            else datetime.min.replace(tzinfo=timezone.utc)
        )
        incoming_ts = (
            datetime.fromisoformat(incoming["timestamp"]).replace(tzinfo=timezone.utc)
            if "timestamp" in incoming
            else _utcnow()
        )

        if incoming_ts >= existing_ts:
            return {"action": "incoming_wins", "timestamp": incoming_ts.isoformat()}
        return {"action": "existing_kept", "timestamp": existing_ts.isoformat()}

    @staticmethod
    async def queue_failed_events(
        db: AsyncSession,
        max_retries: int = 3,
    ) -> list[EventLog]:
        stmt = (
            select(EventLog)
            .where(
                EventLog.migration_status == MigrationStatus.failed.value,
            )
            .order_by(EventLog.timestamp)
            .limit(50)
        )
        result = await db.execute(stmt)
        events = result.scalars().all()
        for event in events:
            retry_count = (event.payload or {}).get("retry_count", 0)
            if retry_count < max_retries:
                event.migration_status = MigrationStatus.pending.value
                p = dict(event.payload or {})
                p["retry_count"] = retry_count + 1
                event.payload = p
        await db.commit()
        return events
