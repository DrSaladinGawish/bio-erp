"""
OR Trigger Endpoint (Webhook Alternative)
==========================================
Alternative to modifying EventBridge directly.
External systems/frontends call this after creating an event.

Usage:
    # After creating event in frontend:
    fetch("/api/v1/or/trigger/event-created", {
        method: "POST",
        body: JSON.stringify({ event_id: 123 })
    })
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session_factory
from app.organs.or_organ.auto_trigger import AutoTriggerEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/or/trigger", tags=["OR Trigger"])

session_factory = get_async_session_factory()


class EventCreatedPayload(BaseModel):
    event_id: int = Field(..., description="ID of the created event")
    run_lp: bool = True
    run_eoq: bool = True
    run_pert: bool = True
    run_cvp: bool = True


class StockAlertPayload(BaseModel):
    sku: str
    current_qty: float
    reorder_point: float


class InvoicePayload(BaseModel):
    invoice_id: int
    invoice_type: str = Field(..., pattern="^(customer|vendor)$")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/event-created")
async def trigger_event_created(
    payload: EventCreatedPayload,
    background_tasks: BackgroundTasks,
):
    """Trigger OR analysis when a new event is created."""
    trigger = AutoTriggerEngine()
    background_tasks.add_task(trigger.on_event_created, payload.event_id)
    return {
        "success": True,
        "message": f"OR analysis queued for event {payload.event_id}",
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/stock-alert")
async def trigger_stock_alert(
    payload: StockAlertPayload,
    background_tasks: BackgroundTasks,
):
    """Trigger EOQ reorder analysis when stock falls below reorder point."""
    trigger = AutoTriggerEngine()
    background_tasks.add_task(
        trigger.on_stock_alert,
        payload.sku,
        payload.current_qty,
        payload.reorder_point,
    )
    return {
        "success": True,
        "message": f"Stock alert analysis queued for {payload.sku}",
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/invoice-posted")
async def trigger_invoice_posted(
    payload: InvoicePayload,
    background_tasks: BackgroundTasks,
):
    """Trigger CVP impact analysis when an invoice is posted."""
    trigger = AutoTriggerEngine()
    background_tasks.add_task(
        trigger.on_invoice_posted,
        payload.invoice_id,
        payload.invoice_type,
    )
    return {
        "success": True,
        "message": f"Invoice impact analysis queued for {payload.invoice_type} invoice {payload.invoice_id}",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/status")
async def trigger_status():
    """Check if trigger endpoint is active."""
    return {
        "success": True,
        "triggers_available": [
            "POST /api/v1/or/trigger/event-created",
            "POST /api/v1/or/trigger/stock-alert",
            "POST /api/v1/or/trigger/invoice-posted",
        ],
        "mode": "BACKGROUND_TASKS",
        "timestamp": datetime.now().isoformat(),
    }
