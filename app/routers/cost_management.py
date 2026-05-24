from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.models import (
    BudgetLine,
    BudgetPeriod,
    CrossCenterAllocation,
)
from app.schemas.cost_management import (
    BudgetPeriodCreate,
    BudgetPeriodResponse,
    BudgetLineResponse,
    BudgetLineBulkCreate,
    CostAllocationCreate,
    CostAllocationResponse,
)
from app.services.cost_engine import CostEngine

router = APIRouter(prefix="/api/v1/cost-management", tags=["Cost Management"])


@router.post("/periods", response_model=BudgetPeriodResponse)
async def create_period(
    req: BudgetPeriodCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    period = BudgetPeriod(**req.model_dump())
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


@router.get("/periods", response_model=list[BudgetPeriodResponse])
async def list_periods(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetPeriod).order_by(
            BudgetPeriod.fiscal_year.desc(), BudgetPeriod.quarter.desc()
        )
    )
    return result.scalars().all()


@router.post("/budget-lines", response_model=list[BudgetLineResponse])
async def create_budget_lines(
    req: BudgetLineBulkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    created = []
    for line_data in req.lines:
        line = BudgetLine(**line_data.model_dump())
        db.add(line)
        created.append(line)
    await db.commit()
    for line in created:
        await db.refresh(line)
    return [_to_response(line) for line in created]


@router.get("/budget-lines", response_model=list[BudgetLineResponse])
async def list_budget_lines(
    branch_id: int | None = Query(None),
    period_id: int | None = Query(None),
    cost_center_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(BudgetLine).options(
        joinedload(BudgetLine.cost_center),
        joinedload(BudgetLine.coa_account),
        joinedload(BudgetLine.budget_period),
    )
    if branch_id:
        q = q.where(BudgetLine.branch_id == branch_id)
    if period_id:
        q = q.where(BudgetLine.budget_period_id == period_id)
    if cost_center_id:
        q = q.where(BudgetLine.cost_center_id == cost_center_id)

    result = await db.execute(q)
    return [_to_response(line) for line in result.scalars().all()]


@router.get("/variance-report")
async def variance_report(
    branch_id: int | None = Query(None),
    period_id: int | None = Query(None),
    cost_center_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await CostEngine.get_variance_report(
        db, branch_id, period_id, cost_center_id
    )


@router.post("/allocations", response_model=CostAllocationResponse)
async def create_allocation(
    req: CostAllocationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    alloc = CrossCenterAllocation(**req.model_dump())
    db.add(alloc)
    await db.commit()
    await db.refresh(alloc)
    return alloc


@router.post("/allocations/{alloc_id}/execute")
async def execute_allocation(
    alloc_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await CostEngine.execute_allocation(db, alloc_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/branch-profitability")
async def branch_profitability(
    period_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await CostEngine.get_branch_profitability(db, period_id)


@router.post("/sync-actuals/{period_id}")
async def sync_actuals(
    period_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await CostEngine.update_actuals_from_ledger(db, period_id)
    return {"updated_lines": count}


def _to_response(line: BudgetLine) -> dict:
    return {
        "id": line.id,
        "cost_center_id": line.cost_center_id,
        "coa_account_id": line.coa_account_id,
        "budget_period_id": line.budget_period_id,
        "branch_id": line.branch_id,
        "budgeted_amount": float(line.budgeted_amount),
        "actual_amount": float(line.actual_amount),
        "committed_amount": float(line.committed_amount),
        "variance_amount": float(line.variance_amount),
        "variance_percent": round(line.variance_percent, 2),
        "notes": line.notes,
        "created_at": line.created_at,
        "cost_center_name": line.cost_center.name_en if line.cost_center else None,
        "coa_account_name": line.coa_account.name_en if line.coa_account else None,
        "period_label": line.budget_period.label if line.budget_period else None,
    }
