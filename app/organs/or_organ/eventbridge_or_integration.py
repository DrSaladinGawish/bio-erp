"""
EventBridge OR Integration Hook
================================
Optional hook that fires OR analysis after EventBridge syncs an event.
Can be toggled on/off, filters by event type, and never blocks the sync.

Usage:
    from app.organs.or_organ.eventbridge_or_integration import EventBridgeORHook

    class EventBridge:
        def __init__(self):
            self.or_hook = EventBridgeORHook()

    # In sync_web_to_local, after event creation:
    event = ...
    await self.or_hook.after_event_sync(db, event)
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_management import EventLog
from app.organs.or_organ.auto_trigger import AutoTriggerEngine

logger = logging.getLogger(__name__)

ANALYZE_EVENT_TYPES = {
    "event_created",
    "job_created",
    "project_started",
    "order_placed",
    "sync",
}

SKIP_SEVERITIES = {"debug", "trace"}


class EventBridgeORHook:
    """
    Hooks into EventBridge to trigger OR analysis after event sync.
    Lightweight - never blocks or raises on failure.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.trigger = AutoTriggerEngine()

    def should_analyze(self, event: EventLog) -> bool:
        """Filter: only analyze relevant event types, skip noise."""
        if not self.enabled:
            return False
        if not event or not event.id:
            return False
        if (event.severity or "").lower() in SKIP_SEVERITIES:
            return False
        event_type = (event.event_type or "").lower()
        if event_type not in ANALYZE_EVENT_TYPES and event_type not in {
            s.lower() for s in ANALYZE_EVENT_TYPES
        }:
            return False
        return True

    async def after_event_sync(self, db: AsyncSession, event: EventLog) -> Optional[dict]:
        """
        Called after EventBridge syncs an event.
        Returns OR analysis result or None if skipped/failed.
        NEVER blocks the caller — wraps in try/except.
        """
        if not self.should_analyze(event):
            return None
        try:
            result = await self.trigger.on_event_created(event.id)
            logger.info(
                "OR hook: Event %s analyzed (%s)",
                event.id,
                result.get("overall_feasible", "unknown"),
            )
            return result
        except Exception as e:
            logger.warning("OR hook: Event %s analysis failed: %s", event.id, e, exc_info=True)
            return None
