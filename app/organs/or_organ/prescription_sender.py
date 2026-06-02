import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.organs.or_organ.models import OrPrescription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/or/prescriptions", tags=["or-prescriptions"])

EVENTCORE_BASE_URL = settings.eventcore_base_url.rstrip("/")
EVENTCORE_PUSH_ENDPOINT = f"{EVENTCORE_BASE_URL}/api/v1/prescriptions/push"
BRIDGE_TOKEN = settings.BIO_ERP_BRIDGE_TOKEN


class PrescriptionPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    external_id: str
    patient_name: str
    patient_id: str
    medication: str
    dosage: str
    prescribing_doctor: str
    notes: Optional[str] = None
    issued_at: Optional[str] = None

    @field_validator("external_id", "patient_name", "patient_id", "medication", "dosage", "prescribing_doctor")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()


class PushRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prescription_ids: Optional[list[str]] = None


class PushResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pushed: int
    failed: int
    errors: list[str] = []


def _build_payload(record: OrPrescription) -> PrescriptionPayload:
    return PrescriptionPayload(
        external_id=str(record.external_id),
        patient_name=record.patient_name,
        patient_id=record.patient_id,
        medication=record.medication,
        dosage=record.dosage,
        prescribing_doctor=record.prescribing_doctor or "",
        notes=getattr(record, "notes", None),
        issued_at=str(record.issued_at) if record.issued_at else None,
    )


@router.post("/push-to-eventcore", response_model=PushResult)
async def push_to_eventcore(req: PushRequest, db: AsyncSession = Depends(get_db)):
    query = select(OrPrescription)

    if req.prescription_ids:
        query = query.where(OrPrescription.id.in_(req.prescription_ids))
    else:
        query = query.where(OrPrescription.exported == False)

    result = await db.execute(query)
    records = list(result.scalars().all())

    if not records:
        return PushResult(pushed=0, failed=0, errors=[])

    payloads = [_build_payload(r) for r in records]
    batch = {
        "prescriptions": [p.model_dump(exclude_none=True) for p in payloads],
        "source": "bio-erp",
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BRIDGE_TOKEN}",
        "X-Bridge-Token": BRIDGE_TOKEN,
    }

    pushed_count = 0
    errors: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(EVENTCORE_PUSH_ENDPOINT, json=batch, headers=headers)

        if response.status_code in (200, 201):
            pushed_count = len(records)
            ids = [r.id for r in records]
            stmt = update(OrPrescription).where(OrPrescription.id.in_(ids)).values(exported=True)
            await db.execute(stmt)
            await db.commit()
            logger.info("Pushed %d prescriptions to EventCore successfully", pushed_count)
        else:
            err_msg = f"EventCore returned status {response.status_code}: {response.text[:200]}"
            errors.append(err_msg)
            logger.warning(err_msg)
    except httpx.RequestError as exc:
        err_msg = f"HTTP request to EventCore failed: {exc}"
        errors.append(err_msg)
        logger.error(err_msg)

    return PushResult(pushed=pushed_count, failed=len(records) - pushed_count, errors=errors)


@router.post("/webhook/eventcore-trigger", response_model=PushResult)
async def eventcore_trigger_webhook(req: PushRequest, db: AsyncSession = Depends(get_db)):
    return await push_to_eventcore(req, db)


@router.get("/pending-count")
async def pending_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrPrescription).where(OrPrescription.exported == False))
    records = result.scalars().all()
    return {"pending": len(records)}


@router.get("/status")
def bridge_status():
    return {
        "bridge": "P2-Reverse",
        "eventcore_url": EVENTCORE_BASE_URL,
        "push_endpoint": EVENTCORE_PUSH_ENDPOINT,
        "token_configured": bool(BRIDGE_TOKEN),
        "status": "active",
    }
