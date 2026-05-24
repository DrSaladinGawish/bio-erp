from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.coa import COACategory, COAAccount
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/coa", tags=["Chart of Accounts"])


class CategoryCreate(BaseModel):
    code: str
    name_en: str
    name_ar: str | None = None
    report_type: str | None = None


class AccountCreate(BaseModel):
    code: str
    name_en: str
    name_ar: str | None = None
    category_id: int
    account_type: str | None = None
    parent_id: int | None = None
    opening_balance: float = 0.0


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(COACategory).where(COACategory.is_active))
    return result.scalars().all()


@router.post("/categories")
async def create_category(
    req: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("coa.create")),
):
    cat = COACategory(
        code=req.code,
        name_en=req.name_en,
        name_ar=req.name_ar,
        report_type=req.report_type,
    )
    db.add(cat)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "COACategory", cat.id, new_value=req.model_dump(), actor_id=user.id
    )
    return cat


@router.get("/accounts")
async def list_accounts(
    category_id: int | None = None, db: AsyncSession = Depends(get_db)
):
    query = select(COAAccount).where(COAAccount.is_active)
    if category_id:
        query = query.where(COAAccount.category_id == category_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/accounts")
async def create_account(
    req: AccountCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("coa.create")),
):
    acct = COAAccount(
        code=req.code,
        name_en=req.name_en,
        name_ar=req.name_ar,
        category_id=req.category_id,
        account_type=req.account_type,
        parent_id=req.parent_id,
        opening_balance=req.opening_balance,
    )
    db.add(acct)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "COAAccount", acct.id, new_value=req.model_dump(), actor_id=user.id
    )
    return acct


@router.get("/accounts/{account_id}")
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(COAAccount).where(COAAccount.id == account_id))
    acct = result.scalar_one_or_none()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    return acct
