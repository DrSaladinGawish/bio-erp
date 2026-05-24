import asyncio
from celery import shared_task
from app.services.cost_engine import CostEngine
from app.services.alert_pubsub import publish_variance_alert
from app.database import AsyncSessionLocal


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_period_actuals(self, period_id: int | None = None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_do_sync(period_id))
        loop.close()
        return result
    except Exception as exc:
        loop.close()
        raise self.retry(exc=exc)


async def _do_sync(period_id: int | None):
    async with AsyncSessionLocal() as db:
        from app.models.costing import BudgetPeriod
        from sqlalchemy import select

        if period_id:
            periods = [await db.get(BudgetPeriod, period_id)]
            if periods[0] is None:
                return {"error": f"Period {period_id} not found"}
        else:
            result = await db.execute(
                select(BudgetPeriod).where(not BudgetPeriod.is_closed)
            )
            periods = result.scalars().all()

        results = []
        for period in periods:
            updated = await CostEngine.update_actuals_from_ledger(db, period.id)
            alerts = await _check_variance_alerts(db, period.id)
            results.append(
                {
                    "period_id": period.id,
                    "period_label": period.label,
                    "lines_updated": updated,
                    "alerts_triggered": len(alerts),
                }
            )
            for alert in alerts:
                publish_variance_alert(alert)

        return {"synced_periods": results}


async def _check_variance_alerts(db, period_id: int) -> list[dict]:
    from app.models.costing import BudgetLine
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    result = await db.execute(
        select(BudgetLine)
        .where(BudgetLine.budget_period_id == period_id)
        .options(joinedload(BudgetLine.cost_center))
    )
    lines = result.scalars().all()
    alerts = []
    for line in lines:
        pct = line.variance_percent
        if abs(pct) > 10:
            alerts.append(
                {
                    "type": "variance_alert",
                    "severity": "investigate",
                    "period_id": period_id,
                    "cost_center_id": line.cost_center_id,
                    "cost_center_name": line.cost_center.name_en
                    if line.cost_center
                    else "",
                    "budgeted": float(line.budgeted_amount),
                    "actual": float(line.actual_amount),
                    "variance": float(line.variance_amount),
                    "variance_pct": round(pct, 2),
                }
            )
    return alerts
