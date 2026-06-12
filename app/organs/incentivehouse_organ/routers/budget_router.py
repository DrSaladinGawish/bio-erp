"""
Budget Router — Budgeting & Forecasting
Prefix: /api/v1/ih-budget
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from ..models_empty_modules import BudgetLine, BudgetCategory

router = APIRouter(prefix="/api/v1/ih-budget", tags=["Budget"])

@router.get("/lines")
async def list_budget_lines(session: AsyncSession = Depends(get_async_session)):
    rows = (await session.execute(select(BudgetLine).order_by(BudgetLine.fiscal_year.desc(), BudgetLine.id))).scalars().all()
    return {"data": [{"id": r.id, "event_id": r.event_id, "fiscal_year": r.fiscal_year, "planned_amount": r.planned_amount, "approved_amount": r.approved_amount, "actual_amount": r.actual_amount, "status": r.status} for r in rows], "total": len(rows)}

@router.get("/categories")
async def list_budget_categories(session: AsyncSession = Depends(get_async_session)):
    rows = (await session.execute(select(BudgetCategory).order_by(BudgetCategory.code))).scalars().all()
    return {"data": [{"id": r.id, "code": r.code, "name_en": r.name_en, "category_type": r.category_type} for r in rows], "total": len(rows)}

@router.get("/summary")
async def budget_summary(session: AsyncSession = Depends(get_async_session)):
    total_lines = (await session.execute(select(func.count(BudgetLine.id)))).scalar() or 0
    total_planned = (await session.execute(select(func.coalesce(func.sum(BudgetLine.planned_amount), 0.0)))).scalar() or 0
    total_actual = (await session.execute(select(func.coalesce(func.sum(BudgetLine.actual_amount), 0.0)))).scalar() or 0
    return {"total_lines": total_lines, "total_planned": float(total_planned), "total_actual": float(total_actual), "variance": float(total_planned - total_actual)}
