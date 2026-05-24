from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.strategic_cost import (
    TargetCosting,
    LifeCycleCost,
    ActivityCostPool,
    ValueChainActivity,
    KaizenCosting,
    CostVarianceAnalysis,
    BalancedScorecard,
    BSCObjective,
    BSCIndicator,
    BSCMeasurement,
    EventProfitability,
)
from app.models.event import Event


class StrategicCostService:
    @staticmethod
    async def create_target_costing(db: AsyncSession, data: dict) -> TargetCosting:
        target_cost = data["target_price"] * (1 - data["target_margin_pct"] / 100)
        cost_gap = data["current_cost"] - target_cost
        gap_pct = (cost_gap / target_cost * 100) if target_cost > 0 else 0
        record = TargetCosting(
            event_id=data.get("event_id"),
            target_price=data["target_price"],
            target_margin_pct=data["target_margin_pct"],
            target_cost=round(target_cost, 2),
            current_cost=data["current_cost"],
            cost_gap=round(cost_gap, 2),
            gap_pct=round(gap_pct, 2),
            notes=data.get("notes"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_target_costing(
        db: AsyncSession, event_id: Optional[int] = None
    ) -> List[TargetCosting]:
        query = select(TargetCosting)
        if event_id:
            query = query.where(TargetCosting.event_id == event_id)
        query = query.order_by(TargetCosting.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_lifecycle_cost(db: AsyncSession, data: dict) -> LifeCycleCost:
        variance = data["actual_amount"] - data["planned_amount"]
        record = LifeCycleCost(
            event_id=data["event_id"],
            phase=data["phase"],
            category=data["category"],
            description=data.get("description"),
            planned_amount=data["planned_amount"],
            actual_amount=data["actual_amount"],
            variance=round(variance, 2),
            cost_driver=data.get("cost_driver"),
            driver_quantity=data.get("driver_quantity", 0),
            unit_cost=data.get("unit_cost", 0),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_lifecycle_costs(
        db: AsyncSession, event_id: int
    ) -> List[LifeCycleCost]:
        result = await db.execute(
            select(LifeCycleCost)
            .where(LifeCycleCost.event_id == event_id)
            .order_by(LifeCycleCost.phase, LifeCycleCost.category)
        )
        return result.scalars().all()

    @staticmethod
    async def create_abc_pool(db: AsyncSession, data: dict) -> ActivityCostPool:
        cost_driver_rate = (
            (data["total_cost"] / data["driver_quantity"])
            if data["driver_quantity"] > 0
            else 0
        )
        record = ActivityCostPool(
            event_id=data.get("event_id"),
            pool_name=data["pool_name"],
            cost_driver=data["cost_driver"],
            total_cost=data["total_cost"],
            driver_quantity=data["driver_quantity"],
            cost_driver_rate=round(cost_driver_rate, 4),
            notes=data.get("notes"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_abc_event_analysis(db: AsyncSession, event_id: int) -> dict:
        result = await db.execute(
            select(ActivityCostPool).where(ActivityCostPool.event_id == event_id)
        )
        pools = result.scalars().all()
        if not pools:
            return {"event_id": event_id, "pools": [], "pareto": [], "total_cost": 0}
        total_cost = sum(p.total_cost for p in pools)
        sorted_pools = sorted(pools, key=lambda p: p.total_cost, reverse=True)
        cumulative = 0
        pareto = []
        for p in sorted_pools:
            cumulative += p.total_cost
            pct = (p.total_cost / total_cost * 100) if total_cost > 0 else 0
            cum_pct = (cumulative / total_cost * 100) if total_cost > 0 else 0
            pareto.append(
                {
                    "pool_name": p.pool_name,
                    "total_cost": p.total_cost,
                    "pct": round(pct, 1),
                    "cumulative_pct": round(cum_pct, 1),
                }
            )
        return {
            "event_id": event_id,
            "pools": [
                {
                    "id": p.id,
                    "pool_name": p.pool_name,
                    "cost_driver": p.cost_driver,
                    "total_cost": p.total_cost,
                    "cost_driver_rate": p.cost_driver_rate,
                }
                for p in pools
            ],
            "pareto": pareto,
            "total_cost": total_cost,
        }

    @staticmethod
    async def create_value_chain(db: AsyncSession, data: dict) -> ValueChainActivity:
        value_added = data["revenue_attributable"] - data["cost"]
        value_added_pct = (
            (value_added / data["revenue_attributable"] * 100)
            if data["revenue_attributable"] > 0
            else 0
        )
        benchmark_gap = None
        if data.get("benchmark_cost") is not None:
            benchmark_gap = data["cost"] - data["benchmark_cost"]
        record = ValueChainActivity(
            event_id=data["event_id"],
            activity_name=data["activity_name"],
            activity_type=data["activity_type"],
            cost=data["cost"],
            revenue_attributable=data["revenue_attributable"],
            value_added=round(value_added, 2),
            value_added_pct=round(value_added_pct, 2),
            benchmark_cost=data.get("benchmark_cost"),
            benchmark_gap=round(benchmark_gap, 2)
            if benchmark_gap is not None
            else None,
            notes=data.get("notes"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_value_chain_analysis(db: AsyncSession, event_id: int) -> dict:
        result = await db.execute(
            select(ValueChainActivity).where(ValueChainActivity.event_id == event_id)
        )
        activities = result.scalars().all()
        primary = [a for a in activities if a.activity_type == "primary"]
        support = [a for a in activities if a.activity_type == "support"]
        total_cost = sum(a.cost for a in activities)
        total_value_added = sum(a.value_added for a in activities)
        benchmark_gap_total = sum(
            a.benchmark_gap for a in activities if a.benchmark_gap is not None
        )

        def serialize(acts):
            return [
                {
                    "id": a.id,
                    "activity_name": a.activity_name,
                    "activity_type": a.activity_type,
                    "cost": a.cost,
                    "revenue_attributable": a.revenue_attributable,
                    "value_added": a.value_added,
                    "value_added_pct": a.value_added_pct,
                    "benchmark_cost": a.benchmark_cost,
                    "benchmark_gap": a.benchmark_gap,
                }
                for a in acts
            ]

        return {
            "event_id": event_id,
            "primary_activities": serialize(primary),
            "support_activities": serialize(support),
            "total_cost": total_cost,
            "total_value_added": round(total_value_added, 2),
            "benchmark_gap_total": round(benchmark_gap_total, 2),
        }

    @staticmethod
    async def create_kaizen(db: AsyncSession, data: dict) -> KaizenCosting:
        target_cost = data["baseline_cost"] * (1 - data["target_reduction_pct"] / 100)
        record = KaizenCosting(
            event_id=data.get("event_id"),
            kaizen_number=data["kaizen_number"],
            description=data["description"],
            category=data.get("category"),
            baseline_cost=data["baseline_cost"],
            target_reduction_pct=data["target_reduction_pct"],
            target_cost=round(target_cost, 2),
            actual_cost=0,
            achieved_reduction_pct=0,
            status="planned",
            responsible_person=data.get("responsible_person"),
            notes=data.get("notes"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_kaizen_result(
        db: AsyncSession, kaizen_id: int, actual_cost: float
    ) -> KaizenCosting:
        result = await db.execute(
            select(KaizenCosting).where(KaizenCosting.id == kaizen_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        record.actual_cost = actual_cost
        record.achieved_reduction_pct = (
            round((record.baseline_cost - actual_cost) / record.baseline_cost * 100, 2)
            if record.baseline_cost > 0
            else 0
        )
        record.status = (
            "achieved"
            if record.achieved_reduction_pct >= record.target_reduction_pct
            else "partial"
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_kaizen(
        db: AsyncSession, event_id: Optional[int] = None
    ) -> List[KaizenCosting]:
        query = select(KaizenCosting)
        if event_id:
            query = query.where(KaizenCosting.event_id == event_id)
        query = query.order_by(KaizenCosting.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_variance(db: AsyncSession, data: dict) -> CostVarianceAnalysis:
        price_variance = (data["standard_price"] - data["actual_price"]) * data[
            "actual_quantity"
        ]
        quantity_variance = (
            data["standard_quantity"] - data["actual_quantity"]
        ) * data["standard_price"]
        total_variance = price_variance + quantity_variance
        record = CostVarianceAnalysis(
            event_id=data.get("event_id"),
            line_item=data["line_item"],
            standard_cost=data["standard_cost"],
            actual_cost=data["actual_cost"],
            standard_quantity=data["standard_quantity"],
            actual_quantity=data["actual_quantity"],
            standard_price=data["standard_price"],
            actual_price=data["actual_price"],
            price_variance=round(price_variance, 2),
            quantity_variance=round(quantity_variance, 2),
            total_variance=round(total_variance, 2),
            is_favorable=total_variance <= 0,
            root_cause=data.get("root_cause"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_variances(
        db: AsyncSession, event_id: Optional[int] = None
    ) -> List[CostVarianceAnalysis]:
        query = select(CostVarianceAnalysis)
        if event_id:
            query = query.where(CostVarianceAnalysis.event_id == event_id)
        query = query.order_by(CostVarianceAnalysis.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()


class BalancedScorecardService:
    @staticmethod
    async def create_bsc(db: AsyncSession, data: dict) -> BalancedScorecard:
        record = BalancedScorecard(
            event_id=data["event_id"],
            name=data["name"],
            period=data["period"],
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_bsc(db: AsyncSession, bsc_id: int) -> BalancedScorecard:
        result = await db.execute(
            select(BalancedScorecard)
            .options(
                selectinload(BalancedScorecard.objectives),
                selectinload(BalancedScorecard.indicators),
            )
            .where(BalancedScorecard.id == bsc_id)
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def list_bsc(
        db: AsyncSession, event_id: Optional[int] = None
    ) -> List[BalancedScorecard]:
        query = select(BalancedScorecard)
        if event_id:
            query = query.where(BalancedScorecard.event_id == event_id)
        query = query.order_by(BalancedScorecard.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_objective(db: AsyncSession, data: dict) -> BSCObjective:
        record = BSCObjective(
            bsc_id=data["bsc_id"],
            perspective=data["perspective"],
            objective_name=data["objective_name"],
            weight=data.get("weight", 0),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        await BalancedScorecardService._recalculate_bsc(db, data["bsc_id"])
        return record

    @staticmethod
    async def create_indicator(db: AsyncSession, data: dict) -> BSCIndicator:
        record = BSCIndicator(
            bsc_id=data["bsc_id"],
            objective_id=data.get("objective_id"),
            perspective=data["perspective"],
            indicator_name=data["indicator_name"],
            formula=data.get("formula"),
            target_value=data["target_value"],
            weight=data.get("weight", 0),
            uom=data.get("uom"),
            frequency=data.get("frequency", "monthly"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        await BalancedScorecardService._recalculate_bsc(db, data["bsc_id"])
        return record

    @staticmethod
    async def create_measurement(db: AsyncSession, data: dict) -> BSCMeasurement:
        target = data["target_value"]
        actual = data["actual_value"]
        score = min(100, (actual / target * 100)) if target > 0 else 0
        record = BSCMeasurement(
            indicator_id=data["indicator_id"],
            measurement_date=data["measurement_date"],
            actual_value=actual,
            target_value=target,
            score=round(score, 2),
            notes=data.get("notes"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        result = await db.execute(
            select(BSCIndicator).where(BSCIndicator.id == data["indicator_id"])
        )
        indicator = result.scalar_one_or_none()
        if indicator:
            meas_result = await db.execute(
                select(func.avg(BSCMeasurement.score)).where(
                    BSCMeasurement.indicator_id == indicator.id
                )
            )
            avg_score = meas_result.scalar() or 0
            indicator.actual_value = actual
            indicator.score = round(avg_score, 2)
            await db.commit()
            await BalancedScorecardService._recalculate_bsc(db, indicator.bsc_id)

        return record

    @staticmethod
    async def _recalculate_bsc(db: AsyncSession, bsc_id: int):
        result = await db.execute(
            select(BalancedScorecard)
            .options(
                selectinload(BalancedScorecard.objectives),
                selectinload(BalancedScorecard.indicators),
            )
            .where(BalancedScorecard.id == bsc_id)
        )
        bsc = result.unique().scalar_one_or_none()
        if not bsc:
            return

        perspectives = {
            "financial": [],
            "customer": [],
            "internal_process": [],
            "learning_growth": [],
        }
        for obj in bsc.objectives:
            if obj.perspective in perspectives:
                perspectives[obj.perspective].append(obj)

        for ind in bsc.indicators:
            if ind.perspective in perspectives:
                existing = next(
                    (o for o in bsc.objectives if o.id == ind.objective_id), None
                )
                if existing:
                    existing.score = ind.score

        for name, objs in perspectives.items():
            if objs:
                total_weight = sum(o.weight for o in objs)
                avg = (
                    sum(o.score * (o.weight / total_weight) for o in objs)
                    if total_weight > 0
                    else 0
                )
            else:
                inds = [i for i in bsc.indicators if i.perspective == name]
                avg = sum(i.score for i in inds) / len(inds) if inds else 0
            setattr(bsc, f"{name}_score", round(avg, 2))

        scores = [
            bsc.financial_score,
            bsc.customer_score,
            bsc.internal_process_score,
            bsc.learning_growth_score,
        ]
        bsc.overall_score = round(sum(scores) / len(scores), 2)
        await db.commit()

    @staticmethod
    async def get_bsc_dashboard(db: AsyncSession, event_id: int) -> dict:
        result = await db.execute(
            select(BalancedScorecard)
            .options(
                selectinload(BalancedScorecard.objectives),
                selectinload(BalancedScorecard.indicators),
            )
            .where(BalancedScorecard.event_id == event_id)
            .order_by(BalancedScorecard.created_at.desc())
        )
        bsc = result.unique().scalar_one_or_none()
        if not bsc:
            return {"error": "No BSC found for this event"}

        perspectives = {}
        for p in ["financial", "customer", "internal_process", "learning_growth"]:
            objs = [o for o in bsc.objectives if o.perspective == p]
            inds = [i for i in bsc.indicators if i.perspective == p]
            perspectives[p] = {
                "score": getattr(bsc, f"{p}_score"),
                "objectives": [
                    {
                        "id": o.id,
                        "name": o.objective_name,
                        "weight": o.weight,
                        "score": o.score,
                    }
                    for o in objs
                ],
                "indicators": [
                    {
                        "id": i.id,
                        "name": i.indicator_name,
                        "target": i.target_value,
                        "actual": i.actual_value,
                        "score": i.score,
                        "uom": i.uom,
                    }
                    for i in inds
                ],
            }

        return {
            "bsc": {
                "id": bsc.id,
                "name": bsc.name,
                "period": bsc.period,
                "overall_score": bsc.overall_score,
                "status": bsc.status,
            },
            "perspectives": perspectives,
        }


class EventProfitabilityService:
    @staticmethod
    async def calculate_profitability(
        db: AsyncSession, event_id: int
    ) -> EventProfitability:
        result = await db.execute(
            select(Event)
            .options(
                selectinload(Event.line_items),
                selectinload(Event.budget_lines),
            )
            .where(Event.id == event_id)
        )
        event = result.unique().scalar_one_or_none()
        if not event:
            return None

        total_revenue = sum(
            (li.quantity or 0) * (li.selling_price or 0)
            for li in (event.line_items or [])
        )
        direct_costs = sum(bl.total_cost or 0 for bl in (event.budget_lines or []))
        gross_profit = total_revenue - direct_costs
        gross_margin_pct = (
            (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        )

        operating_expenses = direct_costs * 0.15
        net_profit = gross_profit - operating_expenses
        net_margin_pct = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        roi = (net_profit / direct_costs * 100) if direct_costs > 0 else 0

        avg_ticket = (
            total_revenue / max(event.estimated_attendees or 1, 1)
            if hasattr(event, "estimated_attendees") and event.estimated_attendees
            else 0
        )
        contribution_margin = total_revenue - (direct_costs * 0.7)
        contribution_ratio = (
            (contribution_margin / total_revenue * 100) if total_revenue > 0 else 0
        )
        break_even = (
            (
                operating_expenses
                / (
                    avg_ticket
                    - (direct_costs * 0.7 / max(event.estimated_attendees or 1, 1))
                )
            )
            if avg_ticket > 0
            else 0
        )

        existing = await db.execute(
            select(EventProfitability).where(EventProfitability.event_id == event_id)
        )
        profitability = existing.scalar_one_or_none()

        data = dict(
            event_id=event_id,
            total_revenue=round(total_revenue, 2),
            direct_costs=round(direct_costs, 2),
            gross_profit=round(gross_profit, 2),
            gross_margin_pct=round(gross_margin_pct, 2),
            operating_expenses=round(operating_expenses, 2),
            net_profit=round(net_profit, 2),
            net_margin_pct=round(net_margin_pct, 2),
            roi=round(roi, 2),
            break_even_attendees=round(break_even, 0),
            actual_attendees=event.estimated_attendees
            if hasattr(event, "estimated_attendees")
            else None,
            revenue_per_attendee=round(avg_ticket, 2),
            cost_per_attendee=round(
                direct_costs / max(event.estimated_attendees or 1, 1), 2
            )
            if hasattr(event, "estimated_attendees") and event.estimated_attendees
            else 0,
            contribution_margin=round(contribution_margin, 2),
            contribution_ratio=round(contribution_ratio, 2),
        )

        if profitability:
            for key, val in data.items():
                setattr(profitability, key, val)
        else:
            profitability = EventProfitability(**data)
            db.add(profitability)

        await db.commit()
        await db.refresh(profitability)
        return profitability

    @staticmethod
    async def get_profitability(db: AsyncSession, event_id: int) -> EventProfitability:
        result = await db.execute(
            select(EventProfitability).where(EventProfitability.event_id == event_id)
        )
        return result.scalar_one_or_none()
