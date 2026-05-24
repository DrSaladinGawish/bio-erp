from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


async def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser only")
    return user


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db), _: User = Depends(_require_admin)
):
    result = await db.execute(select(User).order_by(User.id))
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
    result = await db.execute(select(Role).order_by(Role.id))
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
        select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
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
        }
        for a in result.scalars().all()
    ]
