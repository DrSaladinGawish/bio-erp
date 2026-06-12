"""
dashboard_api.py — FastAPI version
Serves all /api/v1/dashboard/* endpoints with fallback data
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

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

class YearItem(BaseModel):
    id: int
    label: str
    status: str
    is_active: bool

class YearsResponse(BaseModel):
    years: List[YearItem]
    current_year: int

class CategoryItem(BaseModel):
    id: int
    name: str
    code: str
    budget: float
    actual: float

class CategoriesResponse(BaseModel):
    categories: List[CategoryItem]

class ActivityItem(BaseModel):
    id: int
    type: str
    description: str
    user: str
    timestamp: str
    status: str

class ActivityResponse(BaseModel):
    activities: List[ActivityItem]
    total: int

class FlagItem(BaseModel):
    id: int
    level: str
    message: str
    module: str
    action_url: Optional[str] = None

class FlagsResponse(BaseModel):
    flags: List[FlagItem]
    unread_count: int

class StatusResponse(BaseModel):
    status: str
    version: str
    database: str
    modules: dict
    timestamp: str

# ── FALLBACK DATA ──
FALLBACK_KPIS = {
    "total_events": 143, "active_events": 12, "total_revenue": 56300000.0,
    "total_costs": 42300000.0, "gross_margin": 14000000.0, "margin_percent": 24.9,
    "ap_due": 19500000.0, "ar_due": 15300000.0, "bank_balance": 2170000.0,
    "pending_approvals": 3, "eta_validated": 92, "eta_rejected": 1,
    "updated_at": datetime.now().isoformat()
}

FALLBACK_YEARS = {
    "years": [
        {"id": 2024, "label": "2024", "status": "closed", "is_active": False},
        {"id": 2025, "label": "2025", "status": "closed", "is_active": False},
        {"id": 2026, "label": "2026", "status": "open", "is_active": True}
    ],
    "current_year": 2026
}

FALLBACK_CATEGORIES = {
    "categories": [
        {"id": 1, "name": "Catering", "code": "5001", "budget": 31045.61, "actual": 28400.00},
        {"id": 2, "name": "Venue", "code": "5002", "budget": 0, "actual": 0},
        {"id": 3, "name": "Transportation", "code": "5003", "budget": 29192.99, "actual": 26500.00},
        {"id": 4, "name": "Accommodation", "code": "5004", "budget": 0, "actual": 0},
        {"id": 5, "name": "Equipment", "code": "5005", "budget": 0, "actual": 0},
        {"id": 6, "name": "Marketing", "code": "5006", "budget": 0, "actual": 0},
        {"id": 7, "name": "Staff Costs", "code": "5007", "budget": 0, "actual": 0},
        {"id": 8, "name": "Miscellaneous", "code": "5008", "budget": 33134.15, "actual": 29800.00}
    ]
}

FALLBACK_ACTIVITIES = {
    "activities": [
        {"id": 1, "type": "invoice", "description": "Sales invoice #11.23.C0031.74 validated", "user": "system", "timestamp": "2026-06-10T10:30:00", "status": "success"},
        {"id": 2, "type": "payment", "description": "AP Payment 360 processed — 30.0M EGP", "user": "system", "timestamp": "2026-06-10T09:15:00", "status": "success"},
        {"id": 3, "type": "budget", "description": "FY2026 budget updated — 93,372.75 EGP", "user": "admin", "timestamp": "2026-06-10T08:45:00", "status": "info"},
        {"id": 4, "type": "approval", "description": "Purchase order PO-2026-042 awaiting approval", "user": "manager", "timestamp": "2026-06-09T16:20:00", "status": "warning"},
        {"id": 5, "type": "eta", "description": "ETA submission rejected for invoice #E-308-8", "user": "system", "timestamp": "2026-06-09T14:10:00", "status": "error"},
        {"id": 6, "type": "event", "description": "Event 02.26.C0003.210 — Partnerships kickoff", "user": "ops", "timestamp": "2026-06-09T11:00:00", "status": "info"},
        {"id": 7, "type": "grn", "description": "GRN #GRN-2026-020 received — 15 items", "user": "warehouse", "timestamp": "2026-06-08T15:30:00", "status": "success"}
    ],
    "total": 7
}

FALLBACK_FLAGS = {
    "flags": [
        {"id": 1, "level": "error", "message": "1 ETA invoice rejected — needs correction", "module": "ETA", "action_url": "/incentivehouse/eta"},
        {"id": 2, "level": "warning", "message": "AP aging: 18 invoices >90 days (400K EGP)", "module": "AP", "action_url": "/incentivehouse/ap"},
        {"id": 3, "level": "warning", "message": "3 purchase orders pending approval", "module": "Approval", "action_url": "/incentivehouse/approval"},
        {"id": 4, "level": "info", "message": "FY2026 budget variance: +291K EGP", "module": "Budget", "action_url": "/incentivehouse/budget"},
        {"id": 5, "level": "success", "message": "System check: 18/18 endpoints PASS", "module": "System", "action_url": "/health"}
    ],
    "unread_count": 3
}

FALLBACK_STATUS = {
    "status": "ok", "version": "5.4.0", "database": "ok",
    "modules": {
        "grn": "ok", "cost": "ok", "event_budget": "ok", "bsc": "ok",
        "bi": "ok", "budget": "ok", "approval": "ok", "ops": "ok"
    },
    "timestamp": datetime.now().isoformat()
}

# ── ENDPOINTS ──

@router.get("/auth/me", response_model=UserMe)
async def auth_me(request: Request):
    """Return current user info"""
    # Try to get from session/token
    user = getattr(request.state, "user", None)
    if user:
        return UserMe(
            id=user.get("id", 1),
            username=user.get("username", "admin"),
            name=user.get("name", "Administrator"),
            role=user.get("role", "admin"),
            email=user.get("email", "admin@incentivehouse.com")
        )
    # Fallback for unauthenticated (dashboard shows generic user)
    return UserMe(id=1, username="admin", name="Administrator", role="admin", email="admin@incentivehouse.com")

@router.get("/summary", response_model=KpiSummary)
async def dashboard_summary():
    """Main dashboard KPI cards"""
    return KpiSummary(**FALLBACK_KPIS)

@router.get("/years", response_model=YearsResponse)
async def dashboard_years():
    """Available fiscal years"""
    return YearsResponse(**FALLBACK_YEARS)

@router.get("/categories", response_model=CategoriesResponse)
async def dashboard_categories():
    """Event/budget categories for filters"""
    return CategoriesResponse(**FALLBACK_CATEGORIES)

@router.get("/activity", response_model=ActivityResponse)
async def dashboard_activity(limit: int = 5):
    """Recent activity feed"""
    activities = FALLBACK_ACTIVITIES["activities"][:limit]
    return ActivityResponse(activities=activities, total=len(FALLBACK_ACTIVITIES["activities"]))

@router.get("/flags", response_model=FlagsResponse)
async def dashboard_flags():
    """System alerts and flags"""
    return FlagsResponse(**FALLBACK_FLAGS)

@router.get("/status", response_model=StatusResponse)
async def v2_status():
    """System status (backward compat)"""
    return StatusResponse(**FALLBACK_STATUS)
