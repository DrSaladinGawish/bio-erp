"""
BSC Router — Balanced Scorecard
Prefix: /api/v1/bsc
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from ..models_empty_modules import BscObjective, BscIndicator

router = APIRouter(prefix="/api/v1/bsc", tags=["Balanced Scorecard"])

@router.get("/objectives")
async def list_objectives(session: AsyncSession = Depends(get_async_session)):
    rows = (await session.execute(select(BscObjective).order_by(BscObjective.perspective, BscObjective.code))).scalars().all()
    return {"data": [{"id": r.id, "perspective": r.perspective, "code": r.code, "name_en": r.name_en, "weight": r.weight} for r in rows], "total": len(rows)}

@router.get("/indicators")
async def list_indicators(session: AsyncSession = Depends(get_async_session)):
    rows = (await session.execute(select(BscIndicator).order_by(BscIndicator.code))).scalars().all()
    return {"data": [{"id": r.id, "code": r.code, "name_en": r.name_en, "target_value": r.target_value, "actual_value": r.actual_value, "unit": r.uom} for r in rows], "total": len(rows)}

@router.get("/summary")
async def bsc_summary(session: AsyncSession = Depends(get_async_session)):
    objectives = (await session.execute(select(func.count(BscObjective.id)))).scalar() or 0
    indicators = (await session.execute(select(func.count(BscIndicator.id)))).scalar() or 0
    return {"total_objectives": objectives, "total_indicators": indicators}
