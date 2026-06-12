"""
dashboard_api.py — FastAPI version
Serves all /api/v1/dashboard/* endpoints with database-backed data
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

# ── SCHEMAS ──
class UserMe(BaseModel):
    id: int
    username: str
    name: str
    role: str
    email: str

class KpiSummary(BaseModel):
    total_events: int
    active_events: int
    total_revenue: float
    total_clients: int
    total_pos: int
    unreconciled_items: int
    new_clients: int
    revenue_growth: int
    pending_operations: int
    items_pending_review: int
    total_costs: float
    gross_margin: float
    margin_percent: float
    ap_due: float
    ar_due: float
    bank_balance: float
    pending_approvals: int
    eta_validated: int
    eta_rejected: int
    updated_at: str

class YearsResponse(BaseModel):
    years: List[str]
    revenue: List[float]

class CategoriesResponse(BaseModel):
    categories: List[str]
    counts: List[int]

class ActivityItem(BaseModel):
    id: int
    timestamp: str
    action_type: str
    user: str
    table_name: str
    record_id: int

class ActivityResponse(BaseModel):
    activities: List[ActivityItem]
    total: int

class FlagItem(BaseModel):
    label: str
    count: int
    color: str

class FlagsResponse(BaseModel):
    flags: List[FlagItem]

class StatusResponse(BaseModel):
    status: str
    version: str
    database: str
    modules: dict
    timestamp: str

# ── CACHE ──
_last_summary = None
_last_summary_ts = None

# ── HELPERS ──

async def _safe_scalar(db, query):
    try:
        r = await db.execute(text(query))
        return r.scalar() or 0
    except Exception:
        return 0

async def _safe_fetch_one(db, query):
    try:
        r = await db.execute(text(query))
        return r.fetchone()
    except Exception:
        return None

async def _fetch_summary(db):
    """Query database for live KPI summary data."""
    event_count = await _safe_scalar(db, "SELECT COUNT(*) FROM events")
    active_events = await _safe_scalar(db, "SELECT COUNT(*) FROM events WHERE status IN ('ACTIVE','IN_PROGRESS','CONFIRMED','PLANNED')")
    client_count = await _safe_scalar(db, "SELECT COUNT(*) FROM clients")
    po_count = await _safe_scalar(db, "SELECT COUNT(*) FROM purchase_orders")
    vendor_count = await _safe_scalar(db, "SELECT COUNT(*) FROM suppliers")

    rev_row = await _safe_fetch_one(db, "SELECT COALESCE(SUM(total),0) FROM sales_invoices")
    total_revenue = float(rev_row[0]) if rev_row else 0.0

    cost_row = await _safe_fetch_one(db, "SELECT COALESCE(SUM(total_amount),0) FROM vendor_invoices")
    total_costs = float(cost_row[0]) if cost_row else 0.0

    bank_row = await _safe_fetch_one(db, "SELECT COALESCE(SUM(amount),0) FROM bnk_transactions")
    bank_balance = float(bank_row[0]) if bank_row else 0.0

    ar_row = await _safe_fetch_one(db, "SELECT COALESCE(SUM(total-paid_amount),0) FROM sales_invoices WHERE status NOT IN ('PAID','CANCELLED')")
    ar_due = float(ar_row[0]) if ar_row else 0.0

    ap_row = await _safe_fetch_one(db, "SELECT COALESCE(SUM(total_amount-paid_amount),0) FROM vendor_invoices WHERE status NOT IN ('PAID','CANCELLED')")
    ap_due = float(ap_row[0]) if ap_row else 0.0

    user_count = await _safe_scalar(db, "SELECT COUNT(*) FROM users")
    branch_count = await _safe_scalar(db, "SELECT COUNT(*) FROM branches")
    event_budget = await _safe_scalar(db, "SELECT COALESCE(SUM(budget),0) FROM events")
    gross_margin = total_revenue - total_costs
    margin_percent = round((gross_margin / total_revenue * 100), 1) if total_revenue else 0

    return KpiSummary(
        total_events=event_count,
        active_events=active_events,
        total_revenue=total_revenue,
        total_clients=client_count,
        total_pos=po_count,
        unreconciled_items=0,
        new_clients=0,
        revenue_growth=0,
        pending_operations=0,
        items_pending_review=0,
        total_costs=total_costs,
        gross_margin=gross_margin,
        margin_percent=margin_percent,
        ap_due=ap_due,
        ar_due=ar_due,
        bank_balance=bank_balance,
        pending_approvals=0,
        eta_validated=0,
        eta_rejected=0,
        updated_at=datetime.now().isoformat()
    )

# ── ENDPOINTS ──

@router.get("/auth/me", response_model=UserMe)
async def auth_me(request: Request):
    """Return current user info"""
    user = getattr(request.state, "user", None)
    if user:
        return UserMe(
            id=user.get("id", 1),
            username=user.get("username", "admin"),
            name=user.get("name", "Administrator"),
            role=user.get("role", "admin"),
            email=user.get("email", "admin@incentivehouse.com")
        )
    return UserMe(id=1, username="admin", name="Administrator", role="admin", email="admin@incentivehouse.com")

@router.get("/summary", response_model=KpiSummary)
async def dashboard_summary():
    """Main dashboard KPI cards from live database"""
    async for db in get_db():
        try:
            result = await _fetch_summary(db)
            return result
        except Exception:
            pass
        finally:
            await db.close()
        break
    return KpiSummary(total_events=0, active_events=0, total_revenue=0.0, total_clients=0, total_pos=0, unreconciled_items=0, new_clients=0, revenue_growth=0, pending_operations=0, items_pending_review=0, total_costs=0.0, gross_margin=0.0, margin_percent=0.0, ap_due=0.0, ar_due=0.0, bank_balance=0.0, pending_approvals=0, eta_validated=0, eta_rejected=0, updated_at=datetime.now().isoformat())

@router.get("/years", response_model=YearsResponse)
async def dashboard_years():
    """Sales revenue by fiscal year"""
    async for db in get_db():
        try:
            r = await db.execute(text("SELECT EXTRACT(YEAR FROM invoice_date)::int AS yr, COALESCE(SUM(total),0) AS rev FROM sales_invoices GROUP BY yr ORDER BY yr"))
            rows = r.fetchall()
            await db.close()
            years = [str(r[0]) for r in rows]
            revenue = [float(r[1]) for r in rows]
            return YearsResponse(years=years, revenue=revenue)
        except Exception:
            await db.close()
        break
    return YearsResponse(years=[], revenue=[])

@router.get("/categories", response_model=CategoriesResponse)
async def dashboard_categories():
    """Record counts by entity type"""
    async for db in get_db():
        try:
            ev = await _safe_scalar(db, "SELECT COUNT(*) FROM events")
            cl = await _safe_scalar(db, "SELECT COUNT(*) FROM clients")
            sp = await _safe_scalar(db, "SELECT COUNT(*) FROM suppliers")
            inv = await _safe_scalar(db, "SELECT COUNT(*) FROM sales_invoices")
            await db.close()
            return CategoriesResponse(categories=["Events", "Clients", "Suppliers", "Invoices"], counts=[ev, cl, sp, inv])
        except Exception:
            await db.close()
        break
    return CategoriesResponse(categories=["Events", "Clients", "Suppliers", "Invoices"], counts=[0, 0, 0, 0])

@router.get("/activity", response_model=ActivityResponse)
async def dashboard_activity(limit: int = 5):
    """Recent activity from audit log"""
    async for db in get_db():
        try:
            r = await db.execute(text("SELECT id, timestamp, action, actor_name, target_type, COALESCE(target_id,0) FROM audit_logs ORDER BY id DESC LIMIT :limit"), {"limit": limit})
            rows = r.fetchall()
            total_r = await db.execute(text("SELECT COUNT(*) FROM audit_logs"))
            total = total_r.scalar() or 0
            await db.close()
            activities = [
                ActivityItem(id=row[0], timestamp=str(row[1]), action_type=row[2],
                             user=row[3], table_name=row[4] or "system", record_id=row[5])
                for row in rows
            ]
            return ActivityResponse(activities=activities, total=total)
        except Exception:
            await db.close()
        break
    return ActivityResponse(activities=[], total=0)

@router.get("/flags", response_model=FlagsResponse)
async def dashboard_flags():
    """System alerts and flags computed from database"""
    async for db in get_db():
        try:
            unallocated = await _safe_scalar(db, "SELECT COUNT(*) FROM events WHERE budget IS NULL OR budget = 0")
            orphan_vendors = await _safe_scalar(db, "SELECT COUNT(*) FROM suppliers WHERE id NOT IN (SELECT DISTINCT vendor_id FROM purchase_orders WHERE vendor_id IS NOT NULL)")
            missing_inv = await _safe_scalar(db, "SELECT COUNT(*) FROM vendor_invoices WHERE total_amount IS NULL OR total_amount = 0")
            stale = await _safe_scalar(db, "SELECT COUNT(*) FROM events WHERE updated_at < NOW() - INTERVAL '90 days'")
            await db.close()
            return FlagsResponse(flags=[
                FlagItem(label="Unallocated Budget", count=unallocated, color="danger"),
                FlagItem(label="Orphan Vendors", count=orphan_vendors, color="success" if orphan_vendors == 0 else "warning"),
                FlagItem(label="Missing Invoice Amounts", count=missing_inv, color="warning"),
                FlagItem(label="Stale Events (90d)", count=stale, color="info"),
            ])
        except Exception:
            await db.close()
        break
    return FlagsResponse(flags=[])

@router.get("/status", response_model=StatusResponse)
async def v2_status():
    """System status (backward compat)"""
    return StatusResponse(
        status="ok", version="5.4.0", database="ok",
        modules={"grn": "ok", "cost": "ok", "event_budget": "ok", "bsc": "ok",
                 "bi": "ok", "budget": "ok", "approval": "ok", "ops": "ok"},
        timestamp=datetime.now().isoformat()
    )
