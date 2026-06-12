#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin Router for IncentiveHouse ERP — DB-backed, integrates with app auth.
Endpoints: /api/v1/admin/auth/login, /auth/me, /users/*, /permissions/*
"""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import verify_password, hash_password, get_current_user
from app.models.auth import User
from app.organs.incentivehouse_organ.admin_permissions_module import (
    UserRole,
    Permission,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    get_user_permissions,
    require_admin,
    map_db_role_to_admin_role,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


def _create_admin_token(user: User) -> str:
    """Create a JWT with role and permissions embedded."""
    role = map_db_role_to_admin_role(user)
    permissions = [p.value for p in get_user_permissions(role)]
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": role.value,
        "permissions": permissions,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


async def _user_to_response(user: User) -> UserResponse:
    role = map_db_role_to_admin_role(user)
    permissions = get_user_permissions(role)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name_en or user.full_name_ar,
        role=role,
        is_active=user.is_active if hasattr(user, "is_active") else True,
        created_at=user.created_at
        if hasattr(user, "created_at")
        else datetime.now(timezone.utc),
        last_login=user.last_login,
        permissions=permissions,
    )


@router.post("/auth/login")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user, return JWT with embedded role and permissions."""
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    role = map_db_role_to_admin_role(user)
    permissions = [p.value for p in get_user_permissions(role)]
    token = _create_admin_token(user)

    return Token(
        access_token=token,
        expires_in=3600,
        role=role,
        permissions=permissions,
    )


@router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile with permissions."""
    return await _user_to_response(current_user)


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [await _user_to_response(u) for u in users]


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    existing = await db.execute(select(User).where(User.username == user_data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    user = User(
        username=user_data.username,
        email=user_data.email or f"{user_data.username}@incentivehouse.com",
        hashed_password=hash_password(user_data.password),
        full_name_en=user_data.full_name,
        is_superuser=(user_data.role == UserRole.ADMIN),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _user_to_response(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await _user_to_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update: UserUpdate,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """Update user role/status (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.email is not None:
        user.email = update.email
    if update.full_name is not None:
        user.full_name_en = update.full_name
    if update.role is not None:
        user.is_superuser = update.role == UserRole.ADMIN
    if update.is_active is not None and hasattr(user, "is_active"):
        user.is_active = update.is_active

    await db.commit()
    await db.refresh(user)
    return await _user_to_response(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """Delete user (admin only). Cannot delete self or superuser."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot delete a superuser")

    await db.delete(user)
    await db.commit()
    return {"message": f"User '{user.username}' deleted"}


@router.get("/permissions")
async def list_permissions(current_user: User = Depends(get_current_user)):
    """List all available permissions and their role mappings."""
    from app.organs.incentivehouse_organ.admin_permissions_module import (
        ROLE_PERMISSIONS,
    )

    return {
        "permissions": [p.value for p in Permission],
        "roles": {
            UserRole.ADMIN.value: [p.value for p in ROLE_PERMISSIONS[UserRole.ADMIN]],
            UserRole.USER.value: [p.value for p in ROLE_PERMISSIONS[UserRole.USER]],
            UserRole.READONLY.value: [
                p.value for p in ROLE_PERMISSIONS[UserRole.READONLY]
            ],
        },
    }


@router.get("/permissions/check")
async def check_permission(
    permission: str,
    current_user: User = Depends(get_current_user),
):
    """Check if the current user has a specific permission."""
    try:
        perm = Permission(permission)
        role = map_db_role_to_admin_role(current_user)
        from app.organs.incentivehouse_organ.admin_permissions_module import (
            has_permission,
        )

        return {
            "permission": permission,
            "has_permission": has_permission(role, perm),
            "role": role.value,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid permission name")
