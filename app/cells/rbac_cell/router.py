from fastapi import APIRouter, Depends

from app.cells.rbac_cell.casbin_adapter import get_enforcer
from app.middleware.auth import get_current_user
from app.models.auth import User

router = APIRouter(prefix="/api/v1/rbac", tags=["RBAC"])


@router.post("/check")
async def check_permission(
    role: str, resource: str, action: str, tenant: str = "default"
):
    enforcer = get_enforcer()
    allowed = enforcer.enforce(role, resource, action, tenant)
    return {"allowed": allowed}


@router.get("/health")
async def rbac_health(_: User = Depends(get_current_user)):
    enforcer = get_enforcer()
    return {
        "status": "active",
        "policy_count": len(enforcer.get_policy()),
        "model": "casbin_rbac_with_domains",
    }


@router.get("/roles/{role}/permissions")
async def get_role_permissions(
    role: str,
    _: User = Depends(get_current_user),
):
    enforcer = get_enforcer()
    perms = enforcer.get_permissions_for_user(role)
    return {"role": role, "permissions": perms}
