from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.services.costing_engine import CostingEngine
from app.models import EventCostAnalysis, Event
from app.models.auth import User
from app.middleware.auth import get_current_user, RequirePermission

router = APIRouter(tags=["Costing & Analysis"])


@router.post("/analyze/{event_id}")
async def analyze_event_costs(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    result = await CostingEngine.calculate_event_cost_analysis(db, event_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/abc/{cost_center_id}")
async def activity_based_costing(
    cost_center_id: int,
    period: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await CostingEngine.activity_based_costing(db, cost_center_id, period)


@router.get("/variance/{event_id}")
async def budget_variance(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await CostingEngine.compare_budget_vs_actual(db, event_id)


@router.get("/margin-analysis")
async def margin_analysis(
    period_from: Optional[str] = None,
    period_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    query = (
        select(EventCostAnalysis, Event.name_en, Event.start_date)
        .join(Event, EventCostAnalysis.event_id == Event.id)
        .order_by(Event.start_date.desc())
    )

    if period_from:
        query = query.where(Event.start_date >= period_from)
    if period_to:
        query = query.where(Event.start_date <= period_to)

    result = await db.execute(query.limit(50))
    rows = result.all()

    return {
        "period": f"{period_from or 'all'} to {period_to or 'now'}",
        "events_analyzed": len(rows),
        "summary": {
            "total_revenue": round(
                sum(r.EventCostAnalysis.total_revenue for r in rows), 2
            ),
            "total_gross_profit": round(
                sum(r.EventCostAnalysis.gross_profit for r in rows), 2
            ),
            "total_net_profit": round(
                sum(r.EventCostAnalysis.net_profit for r in rows), 2
            ),
            "avg_gross_margin": round(
                sum(r.EventCostAnalysis.gross_margin_pct for r in rows) / len(rows), 2
            )
            if rows
            else 0,
            "avg_net_margin": round(
                sum(r.EventCostAnalysis.net_margin_pct for r in rows) / len(rows), 2
            )
            if rows
            else 0,
        },
        "events": [
            {
                "id": r.EventCostAnalysis.event_id,
                "name": r.name_en,
                "date": r.start_date,
                "revenue": round(r.EventCostAnalysis.total_revenue, 2),
                "gross_margin": round(r.EventCostAnalysis.gross_margin_pct, 2),
                "net_margin": round(r.EventCostAnalysis.net_margin_pct, 2),
                "organ_efficiency": round(r.EventCostAnalysis.organ_efficiency, 2),
            }
            for r in rows
        ],
    }


@router.get("/biological-health")
async def biological_system_health(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    result = await db.execute(
        select(func.count(Event.id)).where(Event.status == "APPROVED")
    )
    active_count = result.scalar() or 0

    result = await db.execute(
        select(
            func.avg(EventCostAnalysis.organ_efficiency),
            func.avg(EventCostAnalysis.cell_utilization),
            func.avg(EventCostAnalysis.neural_load),
        )
    )
    avg_efficiency, avg_utilization, avg_neural = result.first() or (0, 0, 0)

    result = await db.execute(
        select(
            func.count().filter(EventCostAnalysis.net_profit > 0),
            func.count().filter(EventCostAnalysis.net_profit <= 0),
        )
    )
    profitable, unprofitable = result.first() or (0, 0)

    recommendations = []
    if (avg_utilization or 0) < 60:
        recommendations.append("Increase cell utilization on low-activity events")
    if unprofitable > profitable * 0.2:
        recommendations.append("Review unprofitable events for cost reduction")
    if (avg_neural or 0) > 8:
        recommendations.append("Neural load high â€” simplify decision chains")

    return {
        "system_status": "healthy" if (avg_efficiency or 0) > 50 else "warning",
        "active_organs": active_count,
        "avg_organ_efficiency": round(avg_efficiency or 0, 2),
        "avg_cell_utilization": round(avg_utilization or 0, 2),
        "avg_neural_load": round(avg_neural or 0, 2),
        "profitability": {
            "profitable_events": profitable,
            "unprofitable_events": unprofitable,
            "profitability_ratio": round(
                profitable / (profitable + unprofitable) * 100, 2
            )
            if (profitable + unprofitable) > 0
            else 0,
        },
        "recommendations": recommendations,
    }
