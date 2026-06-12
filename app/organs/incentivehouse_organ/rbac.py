"""
P0-A1: Role-Based Access Control (RBAC) System
Full permissions matrix for IncentiveHouse ERP — Zero Gap Compliance
"""

import os
from enum import Enum
from typing import List, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt


class Permission(str, Enum):
    """Granular permissions across all ERP modules."""

    EVENT_READ = "event:read"
    EVENT_CREATE = "event:create"
    EVENT_UPDATE = "event:update"
    EVENT_DELETE = "event:delete"
    EVENT_OPS = "event:ops"
    EVENT_APPROVE = "event:approve"

    SALES_READ = "sales:read"
    SALES_WRITE = "sales:write"
    SALES_QUOTE = "sales:quote"
    SALES_INVOICE = "sales:invoice"

    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"
    FINANCE_RECONCILE = "finance:reconcile"
    FINANCE_REPORT = "finance:report"

    PO_READ = "po:read"
    PO_CREATE = "po:create"
    PO_APPROVE = "po:approve"
    VENDOR_READ = "vendor:read"
    VENDOR_WRITE = "vendor:write"

    STAFF_READ = "staff:read"
    STAFF_WRITE = "staff:write"
    STAFF_PAYROLL = "staff:payroll"

    ADMIN = "admin:*"
    AUDIT_READ = "audit:read"
    BACKUP = "backup:*"
    CONFIG = "config:*"

    AI_USE = "ai:use"
    AI_ADMIN = "ai:admin"
    REPORT_GENERATE = "report:generate"

    SCM_READ = "scm:read"
    SCM_WRITE = "scm:write"
    SCM_ADMIN = "scm:admin"


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    OPS_MANAGER = "ops_manager"
    OPS_TEAM = "ops_team"
    SALES_MANAGER = "sales_manager"
    SALES_EXEC = "sales_exec"
    FINANCE_MANAGER = "finance_manager"
    ACCOUNTANT = "accountant"
    PROCUREMENT = "procurement"
    HR_MANAGER = "hr_manager"
    VIEWER = "viewer"
    CLIENT = "client"


ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.SUPER_ADMIN: [p for p in Permission],
    Role.OPS_MANAGER: [
        Permission.EVENT_READ,
        Permission.EVENT_CREATE,
        Permission.EVENT_UPDATE,
        Permission.EVENT_OPS,
        Permission.EVENT_APPROVE,
        Permission.SALES_READ,
        Permission.SALES_QUOTE,
        Permission.PO_READ,
        Permission.PO_CREATE,
        Permission.PO_APPROVE,
        Permission.VENDOR_READ,
        Permission.VENDOR_WRITE,
        Permission.STAFF_READ,
        Permission.STAFF_WRITE,
        Permission.AUDIT_READ,
        Permission.REPORT_GENERATE,
        Permission.AI_USE,
        Permission.SCM_READ,
        Permission.SCM_WRITE,
    ],
    Role.OPS_TEAM: [
        Permission.EVENT_READ,
        Permission.EVENT_OPS,
        Permission.SALES_READ,
        Permission.PO_READ,
        Permission.VENDOR_READ,
        Permission.AI_USE,
    ],
    Role.SALES_MANAGER: [
        Permission.EVENT_READ,
        Permission.EVENT_CREATE,
        Permission.EVENT_UPDATE,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.SALES_QUOTE,
        Permission.SALES_INVOICE,
        Permission.REPORT_GENERATE,
        Permission.AI_USE,
    ],
    Role.SALES_EXEC: [
        Permission.EVENT_READ,
        Permission.EVENT_CREATE,
        Permission.EVENT_UPDATE,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.SALES_QUOTE,
        Permission.AI_USE,
    ],
    Role.FINANCE_MANAGER: [
        Permission.EVENT_READ,
        Permission.FINANCE_READ,
        Permission.FINANCE_WRITE,
        Permission.FINANCE_RECONCILE,
        Permission.FINANCE_REPORT,
        Permission.SALES_INVOICE,
        Permission.PO_APPROVE,
        Permission.REPORT_GENERATE,
        Permission.AUDIT_READ,
        Permission.AI_USE,
        Permission.SCM_READ,
    ],
    Role.ACCOUNTANT: [
        Permission.EVENT_READ,
        Permission.FINANCE_READ,
        Permission.FINANCE_WRITE,
        Permission.FINANCE_RECONCILE,
        Permission.AI_USE,
    ],
    Role.PROCUREMENT: [
        Permission.PO_READ,
        Permission.PO_CREATE,
        Permission.VENDOR_READ,
        Permission.VENDOR_WRITE,
        Permission.EVENT_READ,
        Permission.AI_USE,
        Permission.SCM_READ,
    ],
    Role.HR_MANAGER: [
        Permission.STAFF_READ,
        Permission.STAFF_WRITE,
        Permission.STAFF_PAYROLL,
        Permission.REPORT_GENERATE,
        Permission.AI_USE,
    ],
    Role.VIEWER: [
        Permission.EVENT_READ,
        Permission.SALES_READ,
        Permission.FINANCE_READ,
    ],
    Role.CLIENT: [
        Permission.EVENT_READ,
    ],
}


class RBACService:
    @staticmethod
    def get_role_permissions(role: Role) -> set[Permission]:
        return set(ROLE_PERMISSIONS.get(role, []))

    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        perms = RBACService.get_role_permissions(role)
        return permission in perms or Permission.ADMIN in perms

    @staticmethod
    def has_any_permission(role: Role, permissions: list[Permission]) -> bool:
        return any(RBACService.has_permission(role, p) for p in permissions)

    @staticmethod
    def has_all_permissions(role: Role, permissions: list[Permission]) -> bool:
        return all(RBACService.has_permission(role, p) for p in permissions)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict:
    """Decode HS256 JWT from Authorization header and return user info dict."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = credentials.credentials
    secret = os.getenv("JWT_SECRET", "jwt-dev-secret")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    roles = payload.get("roles", ["viewer"])
    role_str = roles[0] if roles else "viewer"
    return {
        "user_id": int(payload.get("sub", 0)),
        "username": payload.get("username", "unknown"),
        "role": role_str,
        "roles": roles,
    }


def require_permission(permission: Permission):
    async def checker(current_user: dict = Depends(get_current_user)):
        role = Role(current_user.get("role", "viewer"))
        if not RBACService.has_permission(role, permission):
            raise HTTPException(403, f"Requires permission: {permission.value}")
        return current_user

    return checker


def require_any_permission(*permissions: Permission):
    async def checker(current_user: dict = Depends(get_current_user)):
        role = Role(current_user.get("role", "viewer"))
        if not RBACService.has_any_permission(role, list(permissions)):
            raise HTTPException(
                403, f"Requires one of: {[p.value for p in permissions]}"
            )
        return current_user

    return checker
