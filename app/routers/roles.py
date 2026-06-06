from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.middleware.auth import RequirePermission, get_current_user
from app.models.auth import User, Role, Permission

router = APIRouter(prefix="/api/v1/roles", tags=["Roles"])


@router.get("/")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("user:read")),
):
    result = await db.execute(
        select(Role).options(joinedload(Role.permissions)).order_by(Role.name)
    )
    roles = result.unique().scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": [{"code": p.code, "name": p.name_en} for p in r.permissions],
        }
        for r in roles
    ]


@router.get("/my-permissions")
async def my_permissions(
    user: User = Depends(get_current_user),
):
    perms = set()
    role_list = []
    for role in user.roles:
        role_perms = [{"code": p.code, "name": p.name_en} for p in role.permissions]
        role_list.append({
            "id": role.id,
            "name": role.name,
            "permissions": role_perms,
        })
        for p in role.permissions:
            perms.add(p.code)
    return {
        "user_id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser,
        "roles": role_list,
        "permissions": sorted(perms),
    }


@router.get("/{role_id}")
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("user:read")),
):
    result = await db.execute(
        select(Role)
        .options(joinedload(Role.permissions))
        .where(Role.id == role_id)
    )
    role = result.unique().scalar_one_or_none()
    if not role:
        raise HTTPException(404, detail="Role not found")
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": [{"code": p.code, "name": p.name_en} for p in role.permissions],
    }


@router.post("/{role_id}/assign/{user_id}")
async def assign_role(
    role_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("user:write")),
):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(404, detail="Role not found")
    result = await db.execute(
        select(User).options(joinedload(User.roles)).where(User.id == user_id)
    )
    target = result.unique().scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail="User not found")

    for r in target.roles:
        if r.id == role_id:
            return {"message": f"Role '{role.name}' already assigned to user '{target.username}'"}
    target.roles.append(role)
    await db.commit()
    return {"message": f"Role '{role.name}' assigned to user '{target.username}'"}


@router.delete("/{role_id}/assign/{user_id}")
async def remove_role(
    role_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("user:write")),
):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(404, detail="Role not found")
    result = await db.execute(
        select(User).options(joinedload(User.roles)).where(User.id == user_id)
    )
    target = result.unique().scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail="User not found")

    initial_count = len(target.roles)
    target.roles = [r for r in target.roles if r.id != role_id]
    if len(target.roles) == initial_count:
        raise HTTPException(400, detail=f"User does not have role '{role.name}'")
    await db.commit()
    return {"message": f"Role '{role.name}' removed from user '{target.username}'"}
