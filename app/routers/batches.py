from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.models.manufacturing import (
    VALID_TRANSITIONS,
    Batch,
    BatchStatus,
    BatchStatusHistory,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/manufacturing", tags=["manufacturing"])


# ── Pydantic schemas ──────────────────────────────────────────────

class BatchCreate(BaseModel):
    bioreactor_id: Optional[int] = None
    cell_line_id: Optional[int] = None
    gene_construct_id: Optional[int] = None
    product_id: Optional[int] = None
    volume_l: float = 0.0
    inoculum_density: Optional[float] = None
    target_biomass_gl: Optional[float] = None
    notes: Optional[str] = None


class BatchUpdate(BaseModel):
    bioreactor_id: Optional[int] = None
    cell_line_id: Optional[int] = None
    gene_construct_id: Optional[int] = None
    product_id: Optional[int] = None
    volume_l: Optional[float] = None
    inoculum_density: Optional[float] = None
    target_biomass_gl: Optional[float] = None
    actual_biomass_gl: Optional[float] = None
    total_cost_egp: Optional[float] = None
    yield_achieved: Optional[float] = None
    notes: Optional[str] = None


class BatchResponse(BaseModel):
    id: int
    batch_number: str
    status: str
    phase: str
    bioreactor_id: Optional[int] = None
    cell_line_id: Optional[int] = None
    gene_construct_id: Optional[int] = None
    product_id: Optional[int] = None
    volume_l: float
    inoculum_density: Optional[float] = None
    target_biomass_gl: Optional[float] = None
    actual_biomass_gl: Optional[float] = None
    start_time: Optional[str] = None
    harvest_time: Optional[str] = None
    total_cost_egp: float
    yield_achieved: Optional[float] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_active: bool


# ── Helpers ───────────────────────────────────────────────────────

def _batch_to_dict(b: Batch) -> dict:
    return {
        "id": b.id,
        "batch_number": b.batch_number,
        "status": b.status.value if isinstance(b.status, BatchStatus) else b.status,
        "phase": b.phase or "lag",
        "bioreactor_id": b.bioreactor_id,
        "cell_line_id": b.cell_line_id,
        "gene_construct_id": b.gene_construct_id,
        "product_id": b.product_id,
        "volume_l": float(b.volume_l or 0),
        "inoculum_density": float(b.inoculum_density) if b.inoculum_density else None,
        "target_biomass_gl": float(b.target_biomass_gl) if b.target_biomass_gl else None,
        "actual_biomass_gl": float(b.actual_biomass_gl) if b.actual_biomass_gl else None,
        "start_time": b.start_time.isoformat() if b.start_time else None,
        "harvest_time": b.harvest_time.isoformat() if b.harvest_time else None,
        "total_cost_egp": float(b.total_cost_egp or 0),
        "yield_achieved": float(b.yield_achieved) if b.yield_achieved else None,
        "notes": b.notes,
        "created_by": b.created_by,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        "is_active": b.is_active,
    }


async def _generate_batch_number(db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"BIO-{today}-"
    count = (await db.scalar(select(func.count()).select_from(Batch).where(Batch.batch_number.like(f"{prefix}%")))) or 0
    return f"{prefix}{count + 1:04d}"


async def _transition(batch: Batch, target: BatchStatus, db: AsyncSession, user: User, reason: str = ""):
    current = batch.status if isinstance(batch.status, BatchStatus) else BatchStatus(batch.status)
    target_enum = target if isinstance(target, BatchStatus) else BatchStatus(target)

    if target_enum not in VALID_TRANSITIONS.get(current, set()):
        allowed = [s.value for s in VALID_TRANSITIONS.get(current, set())]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current.value}' to '{target_enum.value}'. Allowed: {allowed}",
        )

    old_status = batch.status
    batch.status = target_enum
    history = BatchStatusHistory(
        batch_id=batch.id,
        from_status=old_status.value if isinstance(old_status, BatchStatus) else old_status,
        to_status=target_enum.value,
        changed_by=user.id,
        reason=reason or f"Transition {old_status.value} → {target_enum.value}",
    )
    db.add(history)


# ── CRUD Endpoints ────────────────────────────────────────────────

@router.get("/batches", response_model=dict)
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Batch).where(Batch.deleted_at.is_(None))
    if status_filter:
        query = query.where(Batch.status == status_filter)
    query = query.order_by(Batch.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    batches = result.scalars().all()

    return {
        "data": [_batch_to_dict(b) for b in batches],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


@router.get("/batches/{batch_id}", response_model=dict)
async def get_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return _batch_to_dict(batch)


@router.post("/batches", status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    batch_number = await _generate_batch_number(db)
    batch = Batch(
        batch_number=batch_number,
        status=BatchStatus.DRAFT,
        phase="lag",
        bioreactor_id=payload.bioreactor_id,
        cell_line_id=payload.cell_line_id,
        gene_construct_id=payload.gene_construct_id,
        product_id=payload.product_id,
        volume_l=payload.volume_l,
        inoculum_density=payload.inoculum_density,
        target_biomass_gl=payload.target_biomass_gl,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    history = BatchStatusHistory(
        batch_id=batch.id,
        to_status=BatchStatus.DRAFT.value,
        changed_by=current_user.id,
        reason="Batch created",
    )
    db.add(history)
    await db.commit()

    return _batch_to_dict(batch)


@router.put("/batches/{batch_id}")
async def update_batch(
    batch_id: int,
    payload: BatchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(batch, field, value)
    await db.commit()
    await db.refresh(batch)
    return _batch_to_dict(batch)


@router.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    batch.deleted_at = datetime.now(timezone.utc)
    batch.is_active = False
    await db.commit()
    return {"deleted": True}


# ── State Machine Endpoints ───────────────────────────────────────

@router.post("/batches/{batch_id}/release")
async def release_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await _transition(batch, BatchStatus.RELEASED, db, current_user)
    batch.start_time = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(batch)
    return _batch_to_dict(batch)


@router.post("/batches/{batch_id}/start")
async def start_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await _transition(batch, BatchStatus.IN_PROGRESS, db, current_user)
    batch.phase = "exponential"
    await db.commit()
    await db.refresh(batch)
    return _batch_to_dict(batch)


@router.post("/batches/{batch_id}/complete")
async def complete_batch(
    batch_id: int,
    actual_biomass_gl: Optional[float] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await _transition(batch, BatchStatus.COMPLETED, db, current_user)
    batch.harvest_time = datetime.now(timezone.utc)
    if actual_biomass_gl is not None:
        batch.actual_biomass_gl = actual_biomass_gl
    await db.commit()
    await db.refresh(batch)
    return _batch_to_dict(batch)


@router.post("/batches/{batch_id}/archive")
async def archive_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await _transition(batch, BatchStatus.ARCHIVED, db, current_user)
    await db.commit()
    await db.refresh(batch)
    return _batch_to_dict(batch)


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id, Batch.deleted_at.is_(None)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await _transition(batch, BatchStatus.CANCELLED, db, current_user)
    await db.commit()
    await db.refresh(batch)
    return _batch_to_dict(batch)
