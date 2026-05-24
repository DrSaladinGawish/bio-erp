import hashlib
import json
from datetime import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.event import Event, EventBudgetLine
from app.models.budget_lifecycle import BudgetLifecycle, BudgetSnapshot, BUDGET_VERSIONS

router = APIRouter(prefix="/api/v1/budget-lifecycle", tags=["Budget Lifecycle"])


def get_version_label(version: int) -> str:
    return BUDGET_VERSIONS.get(version, f"V{version}")


@router.get("/{event_id}")
async def get_budget_lifecycle(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.read")),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, detail="Event not found")

    result = await db.execute(
        select(BudgetLifecycle).where(BudgetLifecycle.event_id == event_id)
    )
    lifecycle = result.scalar_one_or_none()
    if not lifecycle:
        lifecycle = BudgetLifecycle(event_id=event_id)
        db.add(lifecycle)
        await db.commit()
        await db.refresh(lifecycle)

    return {
        "event_id": event_id,
        "current_active_version": lifecycle.current_active_version,
        "v1": {"label": "Conceptual", "status": lifecycle.v1_status},
        "v2": {"label": "Executable", "status": lifecycle.v2_status},
        "v3": {"label": "Final", "status": lifecycle.v3_status},
    }


@router.post("/{event_id}/submit")
async def submit_budget_version(
    event_id: int,
    version: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.update")),
):
    if version not in BUDGET_VERSIONS:
        raise HTTPException(
            400, detail=f"Invalid version {version}. Must be 1, 2, or 3"
        )

    result = await db.execute(
        select(BudgetLifecycle).where(BudgetLifecycle.event_id == event_id)
    )
    lifecycle = result.scalar_one_or_none()
    if not lifecycle:
        lifecycle = BudgetLifecycle(event_id=event_id)
        db.add(lifecycle)
        await db.flush()

    status_attr = f"v{version}_status"
    current_status = getattr(lifecycle, status_attr)
    if current_status != "Draft":
        raise HTTPException(
            400,
            detail=f"Version {version} ({get_version_label(version)}) is already {current_status}",
        )

    setattr(lifecycle, status_attr, "Submitted")
    setattr(lifecycle, f"v{version}_submitted_at", datetime.utcnow())
    await db.commit()
    return {"event_id": event_id, "version": version, "status": "Submitted"}


@router.post("/{event_id}/approve")
async def approve_budget_version(
    event_id: int,
    version: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.approve")),
):
    if version not in BUDGET_VERSIONS:
        raise HTTPException(400, detail=f"Invalid version {version}")

    result = await db.execute(
        select(BudgetLifecycle).where(BudgetLifecycle.event_id == event_id)
    )
    lifecycle = result.scalar_one_or_none()
    if not lifecycle:
        raise HTTPException(404, detail="Budget lifecycle not found")

    status_attr = f"v{version}_status"
    current_status = getattr(lifecycle, status_attr)
    if current_status != "Submitted":
        raise HTTPException(
            400, detail=f"Version {version} must be Submitted before approval"
        )

    setattr(lifecycle, status_attr, "Approved")
    setattr(lifecycle, f"v{version}_approved_by", user.id)
    setattr(lifecycle, f"v{version}_approved_at", datetime.utcnow())
    lifecycle.current_active_version = version
    await db.commit()
    return {"event_id": event_id, "version": version, "status": "Approved"}


@router.post("/{event_id}/lock")
async def lock_budget_version(
    event_id: int,
    version: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.lock")),
):
    if version not in BUDGET_VERSIONS:
        raise HTTPException(400, detail=f"Invalid version {version}")

    result = await db.execute(
        select(BudgetLifecycle).where(BudgetLifecycle.event_id == event_id)
    )
    lifecycle = result.scalar_one_or_none()
    if not lifecycle:
        raise HTTPException(404, detail="Budget lifecycle not found")

    status_attr = f"v{version}_status"
    current_status = getattr(lifecycle, status_attr)
    if current_status not in ("Approved", "Submitted"):
        raise HTTPException(
            400, detail=f"Version {version} must be Approved or Submitted to lock"
        )

    setattr(lifecycle, status_attr, "Locked")
    setattr(lifecycle, f"v{version}_locked_by", user.id)
    setattr(lifecycle, f"v{version}_locked_at", datetime.utcnow())

    # Take a snapshot of current budget lines for this version
    lines_result = await db.execute(
        select(EventBudgetLine).where(
            EventBudgetLine.event_id == event_id,
            EventBudgetLine.budget_version == version,
        )
    )
    lines = lines_result.scalars().all()

    line_data = []
    total_cost = 0.0
    total_revenue = 0.0
    for line in lines:
        line_data.append(
            {
                "id": line.id,
                "description": line.description,
                "quantity": line.quantity,
                "unit_cost": line.unit_cost,
                "total_cost": line.total_cost,
                "markup_percent": line.markup_percent,
                "selling_price": line.selling_price,
                "section": line.section,
            }
        )
        total_cost += line.total_cost
        total_revenue += line.selling_price * line.quantity

    hash_data = f"{event_id}:V{version}:{total_cost}:{total_revenue}:{datetime.utcnow().isoformat()}"
    lock_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    snapshot = BudgetSnapshot(
        event_id=event_id,
        budget_version=version,
        line_data=json.dumps(line_data, default=str),
        total_budget=total_cost,
        total_cost=total_cost,
        total_revenue=total_revenue,
        gross_profit=total_revenue - total_cost,
        taken_by=user.id,
        notes=f"Snapshot at lock of version {version} ({get_version_label(version)}). SHA256: {lock_hash[:16]}...",
    )
    db.add(snapshot)
    await db.commit()

    return {
        "event_id": event_id,
        "version": version,
        "status": "Locked",
        "snapshot_id": snapshot.id,
        "lock_hash": lock_hash,
        "locked_at": datetime.utcnow().isoformat(),
    }


@router.get("/{event_id}/verify")
async def verify_budget_lock(
    event_id: int,
    version: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.read")),
):
    """Verify budget snapshot integrity against stored hash"""
    result = await db.execute(
        select(BudgetSnapshot)
        .where(
            BudgetSnapshot.event_id == event_id,
            BudgetSnapshot.budget_version == version,
        )
        .order_by(BudgetSnapshot.id.desc())
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(404, detail="Snapshot not found")

    hash_data = f"{event_id}:V{version}:{snapshot.total_cost}:{snapshot.total_revenue}:{snapshot.snapshot_taken_at.isoformat()}"
    computed_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    stored_hash = (
        snapshot.notes.split("SHA256: ")[-1].split("...")[0]
        if "SHA256: " in snapshot.notes
        else ""
    )

    return {
        "verified": computed_hash.startswith(stored_hash) if stored_hash else False,
        "stored_hash_prefix": stored_hash,
        "computed_hash_prefix": computed_hash[:16],
        "snapshot_id": snapshot.id,
        "snapshot_taken_at": snapshot.snapshot_taken_at,
        "message": "Budget integrity verified"
        if stored_hash and computed_hash.startswith(stored_hash)
        else "BUDGET TAMPERING DETECTED",
    }


@router.get("/{event_id}/snapshots")
async def list_budget_snapshots(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.read")),
):
    result = await db.execute(
        select(BudgetSnapshot)
        .where(BudgetSnapshot.event_id == event_id)
        .order_by(BudgetSnapshot.budget_version.asc())
    )
    snapshots = result.scalars().all()
    return [
        {
            "id": s.id,
            "budget_version": s.budget_version,
            "version_label": BUDGET_VERSIONS.get(
                s.budget_version, f"V{s.budget_version}"
            ),
            "total_budget": s.total_budget,
            "total_cost": s.total_cost,
            "total_revenue": s.total_revenue,
            "gross_profit": s.gross_profit,
            "snapshot_taken_at": s.snapshot_taken_at,
        }
        for s in snapshots
    ]


@router.get("/{event_id}/snapshots/{snapshot_id}")
async def get_budget_snapshot(
    event_id: int,
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("budget.read")),
):
    result = await db.execute(
        select(BudgetSnapshot).where(
            BudgetSnapshot.id == snapshot_id,
            BudgetSnapshot.event_id == event_id,
        )
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(404, detail="Snapshot not found")
    return {
        "id": snapshot.id,
        "budget_version": snapshot.budget_version,
        "version_label": BUDGET_VERSIONS.get(
            snapshot.budget_version, f"V{snapshot.budget_version}"
        ),
        "total_budget": snapshot.total_budget,
        "total_cost": snapshot.total_cost,
        "total_revenue": snapshot.total_revenue,
        "gross_profit": snapshot.gross_profit,
        "line_data": json.loads(snapshot.line_data) if snapshot.line_data else [],
        "snapshot_taken_at": snapshot.snapshot_taken_at,
    }
