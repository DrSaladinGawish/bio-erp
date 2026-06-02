"""
P4 — EventCore Webhook Receiver (Bio-ERP side)

Listens for job-created events from EventCore, triggers OR analysis,
and returns results. Prescriptions are pushed via the P2 sender endpoint.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, get_async_session_factory
from app.organs.or_organ.auto_trigger import AutoTriggerEngine
from app.organs.or_organ.prescription_sender import push_to_eventcore, PushRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auto-trigger", tags=["auto-trigger"])


class JobEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: int
    title: str
    client_id: Optional[int] = None
    event_type: str = "new_job"


class TriggerResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    job_id: int
    analyses: dict
    prescriptions_pushed: int = 0
    message: str = ""


@router.post("/job", response_model=TriggerResult)
async def on_job_created(event: JobEvent, x_bridge_token: str = Header(alias="X-Bridge-Token")):
    if x_bridge_token != settings.BIO_ERP_BRIDGE_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bridge token")

    logger.info("P4 webhook: job %s created — triggering OR analysis", event.job_id)

    trigger = AutoTriggerEngine()
    analyses = await trigger.on_event_created(event.job_id)

    factory = get_async_session_factory()
    async with factory() as db:
        push_result = await push_to_eventcore(PushRequest(), db)
        prescriptions_pushed = push_result.pushed

    return TriggerResult(
        status="completed",
        job_id=event.job_id,
        analyses=analyses,
        prescriptions_pushed=prescriptions_pushed,
        message=f"OR analysis triggered for job {event.job_id}",
    )


@router.get("/health")
async def webhook_health():
    return {"service": "P4-auto-trigger", "status": "active"}
