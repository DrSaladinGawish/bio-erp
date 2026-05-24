from datetime import datetime
from datetime import timezone
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models import (
    Event,
    EventLineItem,
    EventBudgetLine,
    CostCenter,
    CostAllocation,
    ActivityCost,
    StandardCost,
    EventCostAnalysis,
)


class CostingEngine:
    @staticmethod
    async def calculate_event_cost_analysis(db: AsyncSession, event_id: int) -> Dict:
        result = await db.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(
                selectinload(Event.line_items),
                selectinload(Event.budget_lines),
                selectinload(Event.client),
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            return {"error": "Event not found"}

        total_revenue = sum(
            (li.quantity or 0) * (li.selling_price or 0) for li in event.line_items
        )

        budget = event.budget_lines or []

        SECTION_MATERIALS = {"BOOTH", "FURNITURE"}
        SECTION_LABOR = {"STAFFING"}
        SECTION_SUBCONTRACTOR = {"EQUIPMENT"}

        direct_materials = sum(
            b.total_cost for b in budget if b.section in SECTION_MATERIALS
        )
        direct_labor = sum(b.total_cost for b in budget if b.section in SECTION_LABOR)
        subcontractor_costs = sum(
            b.total_cost for b in budget if b.section in SECTION_SUBCONTRACTOR
        )

        venue_rental = sum(b.total_cost for b in budget if b.section == "VENUE")
        equipment_rental = sum(b.total_cost for b in budget if b.section == "EQUIPMENT")
        transportation = sum(b.total_cost for b in budget if b.section == "TRANSPORT")
        catering = sum(b.total_cost for b in budget if b.section == "CATERING")
        marketing = sum(b.total_cost for b in budget if b.section == "MARKETING")
        staff_costs = sum(b.total_cost for b in budget if b.section == "STAFFING")

        all_sections = {
            "BOOTH",
            "FURNITURE",
            "STAFFING",
            "EQUIPMENT",
            "VENUE",
            "TRANSPORT",
            "CATERING",
            "MARKETING",
        }
        other_expenses = sum(
            b.total_cost for b in budget if b.section not in all_sections
        )

        total_operating = (
            venue_rental
            + equipment_rental
            + transportation
            + catering
            + marketing
            + staff_costs
            + other_expenses
        )

        cogs = direct_materials + direct_labor + subcontractor_costs
        gross_profit = total_revenue - cogs
        gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

        net_profit = gross_profit - total_operating
        net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

        variable_costs = cogs * 0.7 + total_operating * 0.3
        fixed_costs = cogs * 0.3 + total_operating * 0.7

        contribution_margin = total_revenue - variable_costs
        cm_ratio = (
            (contribution_margin / total_revenue * 100) if total_revenue > 0 else 0
        )

        breakeven = fixed_costs / (cm_ratio / 100) if cm_ratio > 0 else 0

        total_costs = cogs + total_operating
        organ_efficiency = (total_revenue / total_costs * 100) if total_costs > 0 else 0
        cell_utilization = (
            min(100, (total_revenue / max(event.total_budget, 1)) * 100)
            if event.total_budget
            else 0
        )
        neural_load = len(event.line_items) * 0.1 + len(budget) * 0.05

        analysis = {
            "event_id": event_id,
            "event_name": event.name_en,
            "status": event.status,
            "revenue": {"total_revenue": round(total_revenue, 2), "currency": "EGP"},
            "direct_costs": {
                "materials": round(direct_materials, 2),
                "labor": round(direct_labor, 2),
                "subcontractors": round(subcontractor_costs, 2),
                "total_cogs": round(cogs, 2),
            },
            "gross_profit": {
                "amount": round(gross_profit, 2),
                "margin_pct": round(gross_margin, 2),
            },
            "operating_expenses": {
                "venue_rental": round(venue_rental, 2),
                "equipment_rental": round(equipment_rental, 2),
                "transportation": round(transportation, 2),
                "catering": round(catering, 2),
                "marketing": round(marketing, 2),
                "staff_costs": round(staff_costs, 2),
                "other": round(other_expenses, 2),
                "total": round(total_operating, 2),
            },
            "net_profit": {
                "amount": round(net_profit, 2),
                "margin_pct": round(net_margin, 2),
            },
            "breakeven_analysis": {
                "variable_costs": round(variable_costs, 2),
                "fixed_costs": round(fixed_costs, 2),
                "contribution_margin": round(contribution_margin, 2),
                "cm_ratio_pct": round(cm_ratio, 2),
                "breakeven_revenue": round(breakeven, 2),
            },
            "biological_metrics": {
                "organ_efficiency": round(organ_efficiency, 2),
                "cell_utilization_pct": round(cell_utilization, 2),
                "neural_load_score": round(neural_load, 2),
            },
            "variance_analysis": await CostingEngine._calculate_variances(db, event_id),
            "calculated_at": datetime.utcnow().isoformat(),
        }

        existing = await db.execute(
            select(EventCostAnalysis).where(EventCostAnalysis.event_id == event_id)
        )
        if existing.scalar_one_or_none():
            await db.execute(
                update(EventCostAnalysis)
                .where(EventCostAnalysis.event_id == event_id)
                .values(
                    total_revenue=total_revenue,
                    direct_materials=direct_materials,
                    direct_labor=direct_labor,
                    subcontractor_costs=subcontractor_costs,
                    gross_profit=gross_profit,
                    gross_margin_pct=gross_margin,
                    venue_rental=venue_rental,
                    equipment_rental=equipment_rental,
                    transportation=transportation,
                    catering=catering,
                    marketing=marketing,
                    staff_costs=staff_costs,
                    other_expenses=other_expenses,
                    total_operating_expenses=total_operating,
                    net_profit=net_profit,
                    net_margin_pct=net_margin,
                    breakeven_revenue=breakeven,
                    contribution_margin_pct=cm_ratio,
                    organ_efficiency=organ_efficiency,
                    cell_utilization=cell_utilization,
                    neural_load=neural_load,
                    calculated_at=datetime.utcnow(),
                )
            )
        else:
            analysis_record = EventCostAnalysis(
                event_id=event_id,
                total_revenue=total_revenue,
                direct_materials=direct_materials,
                direct_labor=direct_labor,
                subcontractor_costs=subcontractor_costs,
                gross_profit=gross_profit,
                gross_margin_pct=gross_margin,
                venue_rental=venue_rental,
                equipment_rental=equipment_rental,
                transportation=transportation,
                catering=catering,
                marketing=marketing,
                staff_costs=staff_costs,
                other_expenses=other_expenses,
                total_operating_expenses=total_operating,
                net_profit=net_profit,
                net_margin_pct=net_margin,
                breakeven_revenue=breakeven,
                contribution_margin_pct=cm_ratio,
                organ_efficiency=organ_efficiency,
                cell_utilization=cell_utilization,
                neural_load=neural_load,
            )
            db.add(analysis_record)

        await db.commit()
        return analysis

    @staticmethod
    async def _calculate_variances(db: AsyncSession, event_id: int) -> Dict:
        result = await db.execute(
            select(StandardCost).where(StandardCost.event_id == event_id)
        )
        standards = result.scalars().all()

        variances = {
            "material_variance": sum(s.material_variance for s in standards),
            "labor_variance": sum(s.labor_variance for s in standards),
            "overhead_variance": sum(s.overhead_variance for s in standards),
            "efficiency_variance": sum(s.efficiency_variance for s in standards),
            "total_variance": sum(
                s.material_variance + s.labor_variance + s.overhead_variance
                for s in standards
            ),
        }
        return {k: round(v, 2) for k, v in variances.items()}

    @staticmethod
    async def activity_based_costing(
        db: AsyncSession, cost_center_id: int, period: str
    ) -> Dict:
        result = await db.execute(
            select(CostCenter).where(CostCenter.id == cost_center_id)
        )
        cc = result.scalar_one_or_none()
        if not cc:
            return {"error": "Cost center not found"}

        result = await db.execute(
            select(ActivityCost)
            .where(ActivityCost.cost_center_id == cost_center_id)
            .where(ActivityCost.period == period)
        )
        activities = result.scalars().all()

        result = await db.execute(
            select(CostAllocation)
            .where(CostAllocation.cost_center_id == cost_center_id)
            .where(CostAllocation.period == period)
        )
        allocations = result.scalars().all()

        total_cost = sum(a.total_cost for a in activities)
        total_driver = sum(a.driver_quantity for a in activities)

        return {
            "cost_center": cc.name_en,
            "period": period,
            "total_cost": round(total_cost, 2),
            "activities": [
                {
                    "name": a.activity_name,
                    "driver": a.cost_driver,
                    "driver_qty": a.driver_quantity,
                    "total_cost": round(a.total_cost, 2),
                    "cost_per_driver": round(a.cost_per_driver, 4)
                    if a.cost_per_driver
                    else round(a.total_cost / a.driver_quantity, 4)
                    if a.driver_quantity
                    else 0,
                }
                for a in activities
            ],
            "cost_allocations": [
                {
                    "type": alloc.cost_type.value,
                    "amount": round(alloc.amount, 2),
                    "base": alloc.allocation_base,
                    "rate": round(alloc.rate_per_unit, 4)
                    if alloc.rate_per_unit
                    else None,
                }
                for alloc in allocations
            ],
            "summary": {
                "total_activities": len(activities),
                "total_allocations": len(allocations),
                "average_cost_per_driver": round(total_cost / total_driver, 4)
                if total_driver
                else 0,
            },
        }

    @staticmethod
    async def compare_budget_vs_actual(db: AsyncSession, event_id: int) -> Dict:
        result = await db.execute(
            select(EventBudgetLine)
            .where(EventBudgetLine.event_id == event_id)
            .where(EventBudgetLine.is_active)
        )
        budget_lines = result.scalars().all()

        result = await db.execute(
            select(EventLineItem).where(EventLineItem.event_id == event_id)
        )
        actual_lines = result.scalars().all()

        comparison = []
        total_budget = 0
        total_actual = 0

        for budget in budget_lines:
            actual = next(
                (a for a in actual_lines if a.master_node_id == budget.master_node_id),
                None,
            )
            actual_cost = (actual.quantity * actual.unit_cost) if actual else 0

            total_budget += budget.total_cost
            total_actual += actual_cost

            comparison.append(
                {
                    "item": budget.description,
                    "budgeted": round(budget.total_cost, 2),
                    "actual": round(actual_cost, 2),
                    "variance": round(budget.total_cost - actual_cost, 2),
                    "variance_pct": round(
                        (budget.total_cost - actual_cost) / budget.total_cost * 100, 2
                    )
                    if budget.total_cost
                    else 0,
                    "status": "under"
                    if actual_cost < budget.total_cost
                    else "over"
                    if actual_cost > budget.total_cost
                    else "on_budget",
                }
            )

        return {
            "event_id": event_id,
            "total_budget": round(total_budget, 2),
            "total_actual": round(total_actual, 2),
            "total_variance": round(total_budget - total_actual, 2),
            "variance_pct": round((total_budget - total_actual) / total_budget * 100, 2)
            if total_budget
            else 0,
            "line_items": comparison,
            "overall_status": "under_budget"
            if total_actual < total_budget
            else "over_budget"
            if total_actual > total_budget
            else "on_budget",
        }
