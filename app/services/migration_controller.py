import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_management import (
    EventLog,
    BranchEventSummary,
    MigrationStatus,
)

logger = logging.getLogger(__name__)


class MigrationController:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.phases: dict[str, dict] = {
            "phase_1_schema_alignment": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
            },
            "phase_2_historical_sync": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
            },
            "phase_3_real_time_sync": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
            },
            "phase_4_conflict_resolution": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
            },
            "phase_5_cutover_validation": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
            },
        }

    async def execute_phase(self, phase: str) -> dict:
        if phase not in self.phases:
            return {"error": f"Unknown phase: {phase}"}

        self.phases[phase]["status"] = "in_progress"
        self.phases[phase]["started_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

        try:
            if phase == "phase_1_schema_alignment":
                result = await self._schema_alignment()
            elif phase == "phase_2_historical_sync":
                result = await self._historical_sync()
            elif phase == "phase_3_real_time_sync":
                result = await self._real_time_sync()
            elif phase == "phase_4_conflict_resolution":
                result = await self._resolve_conflicts()
            elif phase == "phase_5_cutover_validation":
                result = await self._cutover_validation()
            else:
                result = {"error": "not implemented"}

            self.phases[phase]["status"] = "completed"
            self.phases[phase]["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            self.phases[phase]["result"] = result
        except Exception as e:
            self.phases[phase]["status"] = "failed"
            self.phases[phase]["error"] = str(e)
            logger.exception(f"Migration phase {phase} failed: {e}")
            result = {"error": str(e)}

        return result

    async def _schema_alignment(self) -> dict:
        from app.database import engine, Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return {
            "status": "tables_created",
            "tables": ["event_logs", "branch_event_summaries"],
        }

    async def _historical_sync(self) -> dict:
        from app.services.event_bridge import EventBridge

        stmt = (
            select(EventLog)
            .where(
                EventLog.migration_status == MigrationStatus.pending.value,
            )
            .order_by(EventLog.timestamp)
            .limit(500)
        )

        result = await self.db.execute(stmt)
        events = result.scalars().all()

        synced = 0
        for event in events:
            try:
                event.migration_status = MigrationStatus.synced.value
                event.handled = True
                await EventBridge._update_branch_summary(self.db, event.branch_id)
                synced += 1
            except Exception:
                event.migration_status = MigrationStatus.failed.value

        await self.db.commit()
        return {"synced": synced, "total_pending": len(events)}

    async def _real_time_sync(self) -> dict:
        from app.services.event_bridge import EventBridge

        count = await EventBridge.sync_local_to_web(self.db)
        return {"synced_to_web": count}

    async def _resolve_conflicts(self) -> dict:
        stmt = select(EventLog).where(
            EventLog.migration_status == MigrationStatus.failed.value,
        )
        result = await self.db.execute(stmt)
        failed = result.scalars().all()

        resolved = 0
        for event in failed:
            event.migration_status = MigrationStatus.pending.value
            resolved += 1

        await self.db.commit()
        return {"resolved": resolved, "requeued_for_sync": resolved}

    async def _cutover_validation(self) -> dict:
        total = await self.db.scalar(select(func.count(EventLog.id))) or 0
        synced = (
            await self.db.scalar(
                select(func.count(EventLog.id)).where(
                    EventLog.migration_status == MigrationStatus.synced.value
                )
            )
            or 0
        )
        failed = (
            await self.db.scalar(
                select(func.count(EventLog.id)).where(
                    EventLog.migration_status == MigrationStatus.failed.value
                )
            )
            or 0
        )

        branch_summaries = await self.db.execute(
            select(func.count(BranchEventSummary.id))
        )
        summary_count = branch_summaries.scalar() or 0

        integrity = total > 0 and synced == total and failed == 0
        return {
            "status": "passed" if integrity else "failed",
            "total_events": total,
            "synced": synced,
            "failed": failed,
            "branch_summaries": summary_count,
            "integrity_ok": integrity,
        }

    def get_status(self) -> dict:
        return {
            "migration_id": "local_to_web_v1",
            "phases": self.phases,
            "overall_status": "completed"
            if all(p["status"] == "completed" for p in self.phases.values())
            else "in_progress",
        }
