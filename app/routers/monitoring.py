from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models import User, Event, ETASubmissionQueue, EventBudgetLine
from app.services.metrics import (
    metrics_response,
    ETA_QUEUE_SIZE,
    ACTIVE_EVENTS,
    TOTAL_REVENUE,
    PENDING_RFQS,
    WS_CLIENTS,
    CELERY_QUEUE_DEPTH,
)
from app.routers.dashboard import active_connections as dashboard_connections
from app.routers.websocket_alerts import _active_connections as alert_connections
from app.services.health import HealthCheck
from app.services.alert_service import AlertService

router = APIRouter(tags=["Monitoring"])


@router.get("/metrics")
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    active = await db.execute(select(func.count()).where(Event.status == "ACTIVE"))
    ACTIVE_EVENTS.set(active.scalar() or 0)

    revenue = await db.execute(
        select(func.sum(EventBudgetLine.total_cost)).where(EventBudgetLine.is_active)
    )
    TOTAL_REVENUE.set(float(revenue.scalar() or 0))

    pending = await db.execute(
        select(func.count()).where(ETASubmissionQueue.status == "pending")
    )
    PENDING_RFQS.set(pending.scalar() or 0)

    for status in [
        "pending",
        "submitted",
        "accepted",
        "rejected",
        "failed",
        "retrying",
    ]:
        count = await db.execute(
            select(func.count()).where(ETASubmissionQueue.status == status)
        )
        ETA_QUEUE_SIZE.labels(status=status).set(count.scalar() or 0)

    WS_CLIENTS.set(len(dashboard_connections) + len(alert_connections))

    try:
        from celery import current_app

        insp = current_app.control.inspect(timeout=1)
        active_queues = insp.active_queues() or {}
        seen = set()
        for queues in active_queues.values():
            for q in queues:
                name = q.get("name", "unknown")
                if name not in seen:
                    CELERY_QUEUE_DEPTH.labels(queue=name).set(1)
                    seen.add(name)
    except Exception:
        pass

    return metrics_response()


@router.get("/health")
async def health_check():
    return await HealthCheck.full_check()


@router.get("/alerts")
async def get_alerts(user: User = Depends(RequirePermission("admin_view"))):
    return await AlertService.run_all_checks()


@router.post("/alerts/test")
async def test_alert(user: User = Depends(RequirePermission("admin_view"))):
    await AlertService.notify(
        [
            {
                "severity": "warning",
                "component": "test",
                "message": "This is a test alert from BIO-ERP monitoring",
            }
        ]
    )
    return {"sent": True}
