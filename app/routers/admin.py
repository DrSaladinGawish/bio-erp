from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog
from app.services.audit_logger import compute_row_hash, AuditJSONEncoder
import json

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


async def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser only")
    return user


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db), _: User = Depends(_require_admin)
):
    result = await db.execute(
        select(User).options(selectinload(User.roles)).order_by(User.id)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name_en": u.full_name_en,
            "is_superuser": u.is_superuser,
            "branch_id": u.branch_id,
            "roles": [{"id": r.id, "name": r.name} for r in u.roles],
        }
        for u in users
    ]


@router.put("/users/{user_id}/roles")
async def set_user_roles(
    user_id: int,
    role_ids: list[int],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    user.roles = list(roles.scalars().all())
    await db.commit()
    return {"updated": True, "user_id": user_id, "role_ids": role_ids}


@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db), _: User = Depends(_require_admin)
):
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    )
    roles = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permissions": [
                {"id": p.id, "code": p.code, "name_en": p.name_en, "module": p.module}
                for p in r.permissions
            ],
        }
        for r in roles
    ]


@router.post("/roles")
async def create_role(
    name: str,
    description: str | None = None,
    permission_ids: list[int] = [],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    role = Role(name=name, description=description)
    if permission_ids:
        perms = await db.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        role.permissions = list(perms.scalars().all())
    db.add(role)
    await db.commit()
    return {"id": role.id, "name": role.name}


@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db), _: User = Depends(_require_admin)
):
    result = await db.execute(
        select(Permission).order_by(Permission.module, Permission.id)
    )
    return [
        {
            "id": p.id,
            "code": p.code,
            "name_en": p.name_en,
            "name_ar": p.name_ar,
            "module": p.module,
        }
        for p in result.scalars().all()
    ]


@router.get("/audit-log")
async def list_audit_log(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    result = await db.execute(
        select(AuditLog)
        .order_by(desc(AuditLog.timestamp))
        .offset(offset)
        .limit(limit)
    )
    return [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "actor_name": a.actor_name,
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "description": a.description,
            "ip_address": a.ip_address,
            "row_hash": a.row_hash,
            "previous_hash": a.previous_hash,
        }
        for a in result.scalars().all()
    ]


@router.get("/audit-log/verify")
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """Verify the SHA-256 hash chain integrity of the audit log."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.id)
    )
    entries = result.scalars().all()
    broken = []
    previous_hash = None
    for entry in entries:
        expected = compute_row_hash(
            entry.timestamp,
            entry.action,
            entry.target_type,
            entry.target_id,
            json.dumps(json.loads(entry.old_value), cls=AuditJSONEncoder) if entry.old_value else None,
            json.dumps(json.loads(entry.new_value), cls=AuditJSONEncoder) if entry.new_value else None,
            previous_hash,
        )
        if entry.row_hash != expected:
            broken.append({
                "id": entry.id,
                "expected_hash": expected,
                "stored_hash": entry.row_hash,
            })
        if entry.previous_hash != previous_hash:
            broken.append({
                "id": entry.id,
                "detail": "previous_hash mismatch",
                "expected_prev": previous_hash,
                "stored_prev": entry.previous_hash,
            })
        previous_hash = entry.row_hash
    return {
        "total_entries": len(entries),
        "chain_intact": len(broken) == 0,
        "broken_links": broken,
    }
