from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_full_dashboard()


@router.get("/revenue-kpi")
async def revenue_kpi(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_1_revenue_kpi()


@router.get("/expense-kpi")
async def expense_kpi(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_2_expense_kpi()


@router.get("/event-pipeline")
async def event_pipeline(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_3_event_pipeline()


@router.get("/budget-health")
async def budget_health(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_4_budget_health()


@router.get("/recent-transactions")
async def recent_transactions(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_5_recent_transactions(limit)


@router.get("/ar-aging")
async def ar_aging_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_6_ar_aging_summary()


@router.get("/upcoming-events")
async def upcoming_events(
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_7_upcoming_events(limit)


@router.get("/counts")
async def customer_supplier_counts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    svc = DashboardService(db)
    return await svc.get_panel_8_customer_supplier_counts()
