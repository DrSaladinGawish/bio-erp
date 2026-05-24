from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.models.auth import User, Role
from datetime import timezone
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name_en: str | None = None
    full_name_ar: str | None = None
    branch_id: int = 1
    role_ids: list[int] = []


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .options(joinedload(User.roles))
        .where(User.username == req.username)
    )
    user = result.unique().scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        logger = AuditLogger(db)
        await logger.log(
            "LOGIN_FAILED", "User", description=f"Failed login for {req.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    role_names = [r.name for r in user.roles]
    token = create_access_token(user.id, user.username, role_names, user.branch_id)

    user.last_login = __import__("datetime").datetime.utcnow()
    logger = AuditLogger(db)
    await logger.log(
        "LOGIN", "User", user.id, actor_id=user.id, actor_name=user.username
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "roles": role_names},
    }


@router.post("/users")
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superuser only"
        )

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name_en=req.full_name_en,
        full_name_ar=req.full_name_ar,
        branch_id=req.branch_id,
    )
    db.add(user)
    await db.flush()

    if req.role_ids:
        roles_result = await db.execute(select(Role).where(Role.id.in_(req.role_ids)))
        user.roles = list(roles_result.scalars().all())

    logger = AuditLogger(db)
    await logger.log(
        "CREATE",
        "User",
        user.id,
        new_value={"username": req.username},
        actor_id=current_user.id,
    )
    return {"id": user.id, "username": user.username}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name_en": current_user.full_name_en,
        "full_name_ar": current_user.full_name_ar,
        "branch_id": current_user.branch_id,
        "is_superuser": current_user.is_superuser,
        "roles": [{"id": r.id, "name": r.name} for r in current_user.roles],
    }
