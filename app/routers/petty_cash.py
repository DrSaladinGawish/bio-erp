from datetime import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.transaction import PettyCashReg, PettyCashLine
from app.services.serial_number import SerialNumberService

router = APIRouter(prefix="/api/v1/petty-cash", tags=["Petty Cash"])


class PettyCashLineCreate(BaseModel):
    expense_category: str
    description: str | None = None
    amount: float
    receipt_number: str | None = None
    receipt_date: datetime | None = None


class PettyCashRegisterCreate(BaseModel):
    description: str | None = None
    lines: list[PettyCashLineCreate]


@router.post("/registers")
async def create_petty_cash_register(
    req: PettyCashRegisterCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("pettycash.create")),
):
    sn = SerialNumberService(db)
    register_number = await sn.generate("PC", PettyCashReg)

    total = sum(line.amount for line in req.lines)

    reg = PettyCashReg(
        register_number=register_number,
        description=req.description,
        total_amount=total,
        status="OPEN",
    )
    db.add(reg)
    await db.flush()

    for line in req.lines:
        db.add(
            PettyCashLine(
                register_id=reg.id,
                expense_category=line.expense_category,
                description=line.description,
                amount=line.amount,
                receipt_number=line.receipt_number,
                receipt_date=line.receipt_date or datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

    await db.commit()
    await db.refresh(reg)
    return {
        "id": reg.id,
        "register_number": reg.register_number,
        "status": "OPEN",
        "total_amount": total,
    }


@router.get("/registers")
async def list_petty_cash_registers(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("pettycash.read")),
):
    query = select(PettyCashReg).order_by(PettyCashReg.created_at.desc()).limit(limit)
    if status:
        query = query.where(PettyCashReg.status == status)
    result = await db.execute(query)
    registers = result.scalars().all()
    return [
        {
            "id": r.id,
            "register_number": r.register_number,
            "description": r.description,
            "total_amount": r.total_amount,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in registers
    ]


@router.get("/registers/{register_id}")
async def get_petty_cash_register(
    register_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("pettycash.read")),
):
    result = await db.execute(
        select(PettyCashReg)
        .options(selectinload(PettyCashReg.lines))
        .where(PettyCashReg.id == register_id)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(404, detail="Petty cash register not found")
    return {
        "id": reg.id,
        "register_number": reg.register_number,
        "description": reg.description,
        "total_amount": reg.total_amount,
        "status": reg.status,
        "lines": [
            {
                "id": line.id,
                "expense_category": line.expense_category,
                "description": line.description,
                "amount": line.amount,
                "receipt_number": line.receipt_number,
                "receipt_date": line.receipt_date,
            }
            for line in reg.lines
        ],
    }


@router.post("/registers/{register_id}/approve")
async def approve_petty_cash(
    register_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("pettycash.approve")),
):
    result = await db.execute(
        select(PettyCashReg).where(PettyCashReg.id == register_id)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(404, detail="Petty cash register not found")
    if reg.status != "OPEN":
        raise HTTPException(400, detail=f"Register is already {reg.status}")
    reg.status = "APPROVED"
    reg.approved_by = user.id
    reg.approval_date = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"id": reg.id, "register_number": reg.register_number, "status": "APPROVED"}


@router.post("/registers/{register_id}/close")
async def close_petty_cash(
    register_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("pettycash.approve")),
):
    result = await db.execute(
        select(PettyCashReg).where(PettyCashReg.id == register_id)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(404, detail="Petty cash register not found")
    if reg.status == "CLOSED":
        raise HTTPException(400, detail="Register is already closed")
    reg.status = "CLOSED"
    await db.commit()
    return {"id": reg.id, "register_number": reg.register_number, "status": "CLOSED"}
