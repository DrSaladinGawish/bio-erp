"""
Auto-Trigger Engine for OR-ERP
================================
Listens for domain events (Event created, stock alert, invoice)
and launches OR analysis in background tasks.

Integration:
    from app.organs.or_organ.auto_trigger import AutoTriggerEngine

    @router.post("/api/v1/events")
    async def create_event(..., background_tasks: BackgroundTasks):
        event = crud.create_event(...)
        trigger = AutoTriggerEngine()
        background_tasks.add_task(trigger.on_event_created, event.id)
        return event
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session_factory
from app.organs.or_organ.job_or_bridge import EventORBridge

logger = logging.getLogger(__name__)

SANDBOX_DIR = os.getenv("OR_SANDBOX_DIR", "./analysis_sandbox")


class AutoTriggerEngine:
    """
    Fires OR analyses automatically when domain events occur.
    Each analysis is saved as a JSON file in the sandbox — NEVER writes to production DB.
    """

    def __init__(self):
        self._session_factory = get_async_session_factory()

    async def on_event_created(self, event_id: int) -> dict:
        """
        Triggered when a new Event is created (P0).
        Runs: LP production mix → EOQ inventory → PERT schedule → CVP profit
        """
        logger.info("Auto-trigger: Event %s created — starting OR analysis", event_id)
        async with self._session_factory() as db:
            bridge = EventORBridge(db, event_id, sandbox_dir=SANDBOX_DIR)
            results = await bridge.run_all()
            logger.info(
                "Auto-trigger: Event %s analyzed — LP:%s EOQ:%s PERT:%s CVP:%s",
                event_id,
                results.get("lp", {}).get("status", "skip"),
                results.get("eoq", {}).get("status", "skip"),
                results.get("pert", {}).get("status", "skip"),
                results.get("cvp", {}).get("status", "skip"),
            )
            return results

    async def on_stock_alert(self, sku: str, current_qty: float, reorder_point: float) -> dict:
        """
        Triggered when inventory falls below reorder point (P1).
        Runs: EOQ reorder calculation + ABC classification update
        """
        logger.info("Auto-trigger: Stock alert for %s (qty=%s, reorder=%s)", sku, current_qty, reorder_point)
        async with self._session_factory() as db:
            bridge = EventORBridge(db, sandbox_dir=SANDBOX_DIR)
            result = bridge.analyze_stock_alert(sku, current_qty, reorder_point)
            return result

    async def on_invoice_posted(self, invoice_id: int, invoice_type: str) -> dict:
        """
        Triggered when an invoice is posted (P2).
        Runs: CVP break-even update + profitability analysis
        """
        logger.info("Auto-trigger: Invoice %s (%s) posted", invoice_id, invoice_type)
        async with self._session_factory() as db:
            bridge = EventORBridge(db, sandbox_dir=SANDBOX_DIR)
            result = await bridge.analyze_invoice_impact(invoice_id, invoice_type)
            return result
