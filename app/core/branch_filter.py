from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User


class BranchFilter:
    """Resolved branch filter context from RBAC + request params."""

    def __init__(self, branch_id: int | None, user: User, is_superuser: bool):
        self.branch_id = branch_id
        self.user = user
        self.is_superuser = is_superuser

    @property
    def is_filtered(self) -> bool:
        return self.branch_id is not None


async def get_branch_filter(
    request: Request,
    branch_id: int | None = Query(None, description="Filter by branch ID"),
    user: User = Depends(get_current_user),
) -> BranchFilter:
    """Resolve effective branch filter based on user role and request params.

    - Superuser: can pass ?branch_id=X to filter, None = all branches
    - Non-superuser: locked to their own branch_id, ignores ?branch_id param
    """
    if user.is_superuser:
        return BranchFilter(
            branch_id=branch_id,
            user=user,
            is_superuser=True,
        )

    return BranchFilter(
        branch_id=user.branch_id,
        user=user,
        is_superuser=False,
    )


async def get_optional_branch_filter(
    request: Request,
    branch_id: int | None = Query(None, description="Filter by branch ID"),
    db: AsyncSession = Depends(get_db),
) -> BranchFilter:
    """Optional auth version â€” returns BranchFilter with user=None if unauthenticated.

    Used by HTMX endpoints that work in guest mode.
    """
    user = None
    try:
        user = await get_current_user(request, db)
    except Exception:
        pass

    if user and not user.is_superuser:
        return BranchFilter(
            branch_id=user.branch_id,
            user=user,
            is_superuser=False,
        )

    return BranchFilter(
        branch_id=branch_id,
        user=user,
        is_superuser=user.is_superuser if user else False,
    )
