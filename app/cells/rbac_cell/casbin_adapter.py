from __future__ import annotations

import os
from typing import Optional

import casbin
from fastapi import Depends, HTTPException, Request
from structlog import get_logger

from app.middleware.auth import get_current_user
from app.models.auth import User

logger = get_logger()

_MODEL_CONF = os.getenv(
    "RBAC_MODEL_CONF",
    os.path.join(os.path.dirname(__file__), "policy_model.conf"),
)
_POLICY_CSV = os.getenv(
    "RBAC_POLICY_CSV",
    os.path.join(os.path.dirname(__file__), "policy.csv"),
)

_enforcer: Optional["casbin.Enforcer"] = None


def get_enforcer() -> casbin.Enforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = casbin.Enforcer(_MODEL_CONF, _POLICY_CSV)
    return _enforcer


def casbin_enforce(resource: str, action: str) -> callable:
    async def enforce(
        request: Request,
        user: User = Depends(get_current_user),
    ) -> None:
        enforcer = get_enforcer()

        tenant = request.headers.get("X-Tenant-ID", "default")
        role_names = [r.name for r in user.roles] if user.roles else []

        if user.is_superuser:
            allowed = True
        else:
            allowed = any(
                enforcer.enforce(role, resource, action, tenant)
                for role in role_names
            )

        logger.info(
            "casbin.enforce",
            user=user.username,
            roles=role_names,
            resource=resource,
            action=action,
            tenant=tenant,
            allowed=allowed,
        )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Casbin denied: none of roles {role_names} can {action} on '{resource}'",
            )

    return Depends(enforce)
