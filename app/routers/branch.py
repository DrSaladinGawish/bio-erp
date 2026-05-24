from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.branch import Branch
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/branches", tags=["Branches"])


class BranchCreate(BaseModel):
    code: str
    name_en: str
    name_ar: str | None = None
    address_en: str | None = None
    address_ar: str | None = None
    phone: str | None = None
    email: str | None = None
    vat_rate: float = 0.14
    country: str = "Egypt"
    is_hq: bool = False
    currency_id: int = 1


@router.get("")
async def list_branches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Branch).where(Branch.is_active))
    return result.scalars().all()


@router.post("/")
async def create_branch(
    req: BranchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("branch.create")),
):
    branch = Branch(
        code=req.code,
        name_en=req.name_en,
        name_ar=req.name_ar,
        address_en=req.address_en,
        address_ar=req.address_ar,
        phone=req.phone,
        email=req.email,
        vat_rate=req.vat_rate,
        country=req.country,
        is_hq=req.is_hq,
        currency_id=req.currency_id,
    )
    db.add(branch)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "Branch", branch.id, new_value=req.model_dump(), actor_id=user.id
    )
    return branch
