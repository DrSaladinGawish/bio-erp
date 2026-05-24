from functools import wraps
from fastapi import Depends, HTTPException, status
from app.middleware.auth import get_current_user
from app.models import User


def require_role(*roles: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: User = Depends(get_current_user), **kwargs):
            if user.is_superuser:
                return await func(*args, user=user, **kwargs)
            user_role_names = {r.name for r in user.roles}
            if not user_role_names.intersection(roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of roles: {', '.join(roles)}",
                )
            return await func(*args, user=user, **kwargs)

        return wrapper

    return decorator


def require_permission(permission_code: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: User = Depends(get_current_user), **kwargs):
            if user.is_superuser:
                return await func(*args, user=user, **kwargs)
            for role in user.roles:
                for perm in role.permissions:
                    if perm.code == permission_code:
                        return await func(*args, user=user, **kwargs)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_code}",
            )

        return wrapper

    return decorator
