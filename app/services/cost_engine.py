from datetime import datetime
from datetime import timezone
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    BudgetLine,
    CrossCenterAllocation,
    Branch,
    Event,
)


class CostEngine:
    @staticmethod
    async def get_variance_report(
        db: AsyncSession,
        branch_id: int | None = None,
        period_id: int | None = None,
        cost_center_id: int | None = None,
    ) -> dict:
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
        lines = result.scalars().all()

        period_label = lines[0].budget_period.label if lines else "N/A"
        rows = []
        total_budgeted = Decimal("0")
        total_actual = Decimal("0")

        for line in lines:
            v = line.variance_amount
            pct = line.variance_percent
            flag = (
                "investigate" if abs(pct) > 10 else "ok" if abs(pct) > 5 else "on_track"
            )
            rows.append(
                {
                    "cost_center_id": line.cost_center_id,
                    "cost_center_name": line.cost_center.name_en
                    if line.cost_center
                    else "",
                    "coa_account_id": line.coa_account_id,
                    "coa_account_name": line.coa_account.name_en
                    if line.coa_account
                    else "",
                    "budgeted": float(line.budgeted_amount),
                    "actual": float(line.actual_amount),
                    "variance": float(v),
                    "variance_pct": round(pct, 2),
                    "flag": flag,
                }
            )
            total_budgeted += line.budgeted_amount
            total_actual += line.actual_amount

        return {
            "period_label": period_label,
            "branch_id": branch_id,
            "total_budgeted": float(total_budgeted),
            "total_actual": float(total_actual),
            "total_variance": float(total_budgeted - total_actual),
            "rows": rows,
        }

    @staticmethod
    async def execute_allocation(
        db: AsyncSession,
        allocation_id: int,
    ) -> dict:
        result = await db.execute(
            select(CrossCenterAllocation)
            .where(CrossCenterAllocation.id == allocation_id)
            .options(
                joinedload(CrossCenterAllocation.from_cost_center),
                joinedload(CrossCenterAllocation.to_cost_center),
            )
        )
        alloc = result.scalar_one_or_none()
        if not alloc:
            return {"error": "Allocation not found"}
        if alloc.is_executed:
            return {"error": "Already executed"}

        alloc.is_executed = True
        alloc.executed_at = datetime.utcnow()

        source_lines = await db.execute(
            select(BudgetLine)
            .where(BudgetLine.cost_center_id == alloc.from_cost_center_id)
            .where(BudgetLine.budget_period_id == alloc.budget_period_id)
        )
        for sl in source_lines.scalars().all():
            allocated = sl.budgeted_amount * Decimal(str(alloc.rate_percent / 100))
            target_line = await db.execute(
                select(BudgetLine)
                .where(BudgetLine.cost_center_id == alloc.to_cost_center_id)
                .where(BudgetLine.coa_account_id == sl.coa_account_id)
                .where(BudgetLine.budget_period_id == alloc.budget_period_id)
            )
            existing = target_line.scalar_one_or_none()
            if existing:
                existing.committed_amount += allocated
            else:
                db.add(
                    BudgetLine(
                        cost_center_id=alloc.to_cost_center_id,
                        coa_account_id=sl.coa_account_id,
                        budget_period_id=alloc.budget_period_id,
                        branch_id=alloc.to_cost_center_id,
                        budgeted_amount=0,
                        committed_amount=allocated,
                    )
                )

        await db.commit()
        return {
            "status": "executed",
            "from": alloc.from_cost_center.name_en if alloc.from_cost_center else "",
            "to": alloc.to_cost_center.name_en if alloc.to_cost_center else "",
            "rate": alloc.rate_percent,
            "executed_at": alloc.executed_at.isoformat(),
        }

    @staticmethod
    async def get_branch_profitability(
        db: AsyncSession,
        period_id: int | None = None,
        branch_id: int | None = None,
    ) -> list[dict]:
        q = select(Branch).where(Branch.is_active)
        if branch_id:
            q = q.where(Branch.id == branch_id)
        branches_q = await db.execute(q)
        branches = branches_q.scalars().all()
        results = []

        for branch in branches:
            events_q = await db.execute(
                select(
                    func.count(Event.id),
                    func.coalesce(func.sum(Event.total_revenue), 0),
                    func.coalesce(func.sum(Event.total_cost), 0),
                ).where(Event.branch_id == branch.id)
            )
            row = events_q.one()
            event_count = row[0]
            revenue = Decimal(str(row[1]))
            direct_costs = Decimal(str(row[2]))
            gross_profit = revenue - direct_costs
            gross_margin = float(gross_profit / revenue * 100) if revenue else 0

            budget_q = await db.execute(
                select(
                    func.coalesce(func.sum(BudgetLine.budgeted_amount), 0),
                    func.coalesce(func.sum(BudgetLine.actual_amount), 0),
                ).where(BudgetLine.branch_id == branch.id)
            )
            if period_id:
                budget_q = budget_q.where(BudgetLine.budget_period_id == period_id)
            budget_row = budget_q.one()
            budget_variance = Decimal(str(budget_row[0])) - Decimal(str(budget_row[1]))

            op_expenses = Decimal("0")
            net_profit = gross_profit - op_expenses
            net_margin = float(net_profit / revenue * 100) if revenue else 0

            results.append(
                {
                    "branch_id": branch.id,
                    "branch_name": branch.name_en,
                    "revenue": float(revenue),
                    "direct_costs": float(direct_costs),
                    "gross_profit": float(gross_profit),
                    "gross_margin_pct": round(gross_margin, 2),
                    "operating_expenses": float(op_expenses),
                    "net_profit": float(net_profit),
                    "net_margin_pct": round(net_margin, 2),
                    "budget_variance": float(budget_variance),
                    "event_count": event_count,
                }
            )

        return results

    @staticmethod
    async def update_actuals_from_ledger(
        db: AsyncSession,
        period_id: int,
    ) -> int:
        from app.models.transaction import GeneralLedger

        lines_q = await db.execute(
            select(BudgetLine).where(BudgetLine.budget_period_id == period_id)
        )
        lines = lines_q.scalars().all()

        for line in lines:
            gl_q = await db.execute(
                select(func.coalesce(func.sum(GeneralLedger.amount), 0))
                .where(GeneralLedger.coa_account_id == line.coa_account_id)
                .where(GeneralLedger.branch_id == line.branch_id)
            )
            actual = gl_q.scalar()
            line.actual_amount = Decimal(str(actual))

        await db.commit()
        return len(lines)
