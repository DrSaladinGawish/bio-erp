#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin User & Permissions Module for IncentiveHouse ERP
Integrates with the app-wide auth system (app.middleware.auth).
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class Permission(str, Enum):
    VIEW_DASHBOARD = "view_dashboard"
    EDIT_DASHBOARD = "edit_dashboard"
    VIEW_EVENTS = "view_events"
    CREATE_EVENTS = "create_events"
    EDIT_EVENTS = "edit_events"
    DELETE_EVENTS = "delete_events"
    VIEW_SALES = "view_sales"
    CREATE_SALES = "create_sales"
    EDIT_SALES = "edit_sales"
    VIEW_BANK = "view_bank"
    RECONCILE_BANK = "reconcile_bank"
    VIEW_GL = "view_gl"
    EDIT_GL = "edit_gl"
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_AUDIT = "view_audit"


ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p for p in Permission],
    UserRole.USER: [
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EVENTS,
        Permission.CREATE_EVENTS,
        Permission.EDIT_EVENTS,
        Permission.VIEW_SALES,
        Permission.CREATE_SALES,
        Permission.VIEW_BANK,
        Permission.VIEW_GL,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
    ],
    UserRole.READONLY: [
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EVENTS,
        Permission.VIEW_SALES,
        Permission.VIEW_BANK,
        Permission.VIEW_GL,
        Permission.VIEW_REPORTS,
    ],
}


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    permissions: List[Permission] = []


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    role: UserRole
    permissions: List[str]


def get_user_permissions(role: UserRole) -> List[Permission]:
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, [])


def map_db_role_to_admin_role(user) -> UserRole:
    """Map a DB User ORM to an admin module UserRole."""
    if user.is_superuser:
        return UserRole.ADMIN
    for role in user.roles:
        if role.name == "admin":
            return UserRole.ADMIN
        if role.name in ("manager", "operator"):
            return UserRole.USER
    return UserRole.READONLY


def require_permission(permission: Permission):
    """Dependency factory — checks if current user has the given permission."""
    from fastapi import HTTPException, status, Depends
    from app.middleware.auth import get_current_user

    async def permission_checker(current_user=Depends(get_current_user)):
        user_role = map_db_role_to_admin_role(current_user)
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return current_user

    return permission_checker


def require_admin():
    """Dependency factory — ensures the current user is an admin."""
    from fastapi import HTTPException, status, Depends
    from app.middleware.auth import get_current_user

    async def admin_checker(current_user=Depends(get_current_user)):
        user_role = map_db_role_to_admin_role(current_user)
        if user_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    return admin_checker


DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "email": "admin@incentivehouse.com",
    "full_name": "System Administrator",
    "role": UserRole.ADMIN,
}

DEFAULT_USER = {
    "username": "user",
    "password": "user123",
    "email": "user@incentivehouse.com",
    "full_name": "Regular User",
    "role": UserRole.USER,
}
