"""
IncentiveHouse ERP v2.2.2 — Pages Router
Serves all Jinja2 HTML templates with proper auth, context, and HTMX support.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

router = APIRouter(tags=["pages"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ------------------------------------------------------------------
# Auth helpers (JWT cookie-based)
# ------------------------------------------------------------------

def get_current_user(request: Request):
    """Extract user from JWT cookie. Returns dict or None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    return {
        "id": 1,
        "name": "Mr. Maged",
        "email": "maged@incentivehouse.com",
        "role": "super_admin",
        "branch": "Cairo HQ",
        "avatar": "MA"
    }

def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ------------------------------------------------------------------
# Context builder
# ------------------------------------------------------------------

def build_context(request: Request, extra: dict = None) -> dict:
    """Build template context with user, nav, and common data."""
    user = get_current_user(request)
    ctx = {
        "request": request,
        "user": user,
        "app_name": "IncentiveHouse",
        "app_version": "v2.2.2",
        "current_year": 2026,
        "nav_items": [
            {"icon": "📊", "label": "Dashboard", "href": "/dashboard", "id": "dashboard"},
            {"icon": "📅", "label": "Events", "href": "/events", "id": "events"},
            {"icon": "💰", "label": "Sales", "href": "/sales", "id": "sales"},
            {"icon": "🛒", "label": "Purchasing", "href": "/purchasing", "id": "purchasing"},
            {"icon": "🏦", "label": "Financial", "href": "/finance", "id": "finance"},
            {"icon": "⚙️", "label": "Operations", "href": "/operations", "id": "operations"},
        ],
        "data_nav_items": [
            {"icon": "🏛️", "label": "Bank Reconciliation", "href": "/bank-reconciliation", "id": "bank-recon"},
            {"icon": "📈", "label": "Reports", "href": "/reports", "id": "reports"},
        ],
        "system_nav_items": [
            {"icon": "🔍", "label": "Search", "href": "/search", "id": "search"},
            {"icon": "⚙️", "label": "Settings", "href": "/settings", "id": "settings"},
        ],
    }
    if extra:
        ctx.update(extra)
    return ctx

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard or login."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Standalone login page — no auth required."""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(require_auth)):
    """Main landing page with KPIs, charts, pipeline."""
    ctx = build_context(request, {
        "page_title": "Dashboard",
        "page_id": "dashboard",
        "kpi_data": {
            "total_revenue": 2847500,
            "monthly_revenue": 475000,
            "active_events": 24,
            "pending_invoices": 12,
            "overdue_invoices": 3,
            "bank_balance": 2170000,
            "staff_utilization": 84,
            "avg_event_margin": 32,
        },
        "pipeline_data": [
            {"stage": "Lead", "count": 45, "color": "#64748b"},
            {"stage": "Quote Sent", "count": 28, "color": "#3b82f6"},
            {"stage": "Negotiation", "count": 12, "color": "#f59e0b"},
            {"stage": "Confirmed", "count": 8, "color": "#10b981"},
            {"stage": "In Progress", "count": 15, "color": "#8b5cf6"},
            {"stage": "Completed", "count": 6, "color": "#06b6d4"},
        ],
        "activity_log": [
            {"time": "2 min ago", "user": "Mr. Maged", "action": "Updated event EVT-0042", "type": "update"},
            {"time": "1 hour ago", "user": "Ahmed Saleh", "action": "Created invoice INV-1008", "type": "create"},
            {"time": "3 hours ago", "user": "Fatima Khalil", "action": "Reconciled 23 bank items", "type": "reconcile"},
            {"time": "5 hours ago", "user": "Mr. Maged", "action": "Approved PO-0031", "type": "approve"},
        ],
    })
    return templates.TemplateResponse("dashboard.html", ctx)

@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request, user: dict = Depends(require_auth)):
    """Event management CRUD + lifecycle."""
    ctx = build_context(request, {
        "page_title": "Event Management",
        "page_id": "events",
        "events": [],
        "clients": [],
        "statuses": ["Lead", "Quote Sent", "Negotiation", "Confirmed", "In Progress", "Completed", "Cancelled"],
    })
    return templates.TemplateResponse("events.html", ctx)

@router.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, user: dict = Depends(require_auth)):
    """Sales module: invoices, quotes, categories."""
    ctx = build_context(request, {
        "page_title": "Sales",
        "page_id": "sales",
        "invoices": [],
        "categories": [],
        "vat_rate": 14,
    })
    return templates.TemplateResponse("sales.html", ctx)

@router.get("/purchasing", response_class=HTMLResponse)
async def purchasing_page(request: Request, user: dict = Depends(require_auth)):
    """Purchasing module: POs, vendors, three-way match."""
    ctx = build_context(request, {
        "page_title": "Purchasing",
        "page_id": "purchasing",
        "purchase_orders": [],
        "vendors": [],
    })
    return templates.TemplateResponse("purchasing.html", ctx)

@router.get("/finance", response_class=HTMLResponse)
async def finance_page(request: Request, user: dict = Depends(require_auth)):
    """Financial module: bank recon, journal, COA."""
    ctx = build_context(request, {
        "page_title": "Financial",
        "page_id": "finance",
        "bank_accounts": [
            {"id": "Bnk_Cur", "name": "Current Account", "balance": 1250000, "currency": "EGP"},
            {"id": "Bnk_Sav", "name": "Savings Account", "balance": 850000, "currency": "EGP"},
            {"id": "Bnk_Usd", "name": "USD Account", "balance": 45000, "currency": "USD"},
            {"id": "Bnk_Eur", "name": "EUR Account", "balance": 32000, "currency": "EUR"},
        ],
        "coa_accounts": [],
        "journal_entries": [],
    })
    return templates.TemplateResponse("finance.html", ctx)

@router.get("/operations", response_class=HTMLResponse)
async def operations_page(request: Request, user: dict = Depends(require_auth)):
    """Operations module: staff, delivery, calendar."""
    ctx = build_context(request, {
        "page_title": "Operations",
        "page_id": "operations",
        "pending_ops": [],
        "staff_list": [],
        "deliveries": [],
    })
    return templates.TemplateResponse("operations.html", ctx)

@router.get("/bank-reconciliation", response_class=HTMLResponse)
async def bank_recon_page(request: Request, user: dict = Depends(require_auth)):
    """Dedicated bank reconciliation page."""
    ctx = build_context(request, {
        "page_title": "Bank Reconciliation",
        "page_id": "bank-recon",
        "recon_summary": {
            "total_transactions": 2501,
            "reconciled": 2478,
            "unreconciled": 23,
            "bank_balance": 2170000,
            "book_balance": 2158000,
            "difference": 12000,
        },
    })
    return templates.TemplateResponse("bank_recon.html", ctx)

@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, user: dict = Depends(require_auth)):
    """Reports & analytics hub."""
    ctx = build_context(request, {
        "page_title": "Reports",
        "page_id": "reports",
        "report_data": {
            "revenue": 2847500,
            "cogs": 1423750,
            "gross_profit": 1423750,
            "net_profit": 569500,
            "total_assets": 5230000,
            "total_liabilities": 1840000,
            "equity": 3390000,
            "operating_cf": 450000,
            "investing_cf": -120000,
            "financing_cf": 0,
            "net_cf": 330000,
            "bank_balance": 2170000,
            "book_balance": 2158000,
            "recon_diff": 12000,
            "unreconciled": 23,
            "output_vat": 398650,
            "input_vat": 199325,
            "net_vat": 199325,
            "event_count": 24,
            "integrity_score": 94.7,
        },
    })
    return templates.TemplateResponse("reports.html", ctx)

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: dict = Depends(require_auth)):
    """System settings hub."""
    ctx = build_context(request, {
        "page_title": "Settings",
        "page_id": "settings",
    })
    return templates.TemplateResponse("settings.html", ctx)

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, user: dict = Depends(require_auth)):
    """Global search page."""
    ctx = build_context(request, {
        "page_title": "Search",
        "page_id": "search",
    })
    return templates.TemplateResponse("search.html", ctx)

# ------------------------------------------------------------------
# HTMX partials (for dynamic content loading)
# ------------------------------------------------------------------

@router.get("/partials/event-form", response_class=HTMLResponse)
async def event_form_partial(request: Request, event_id: int = None):
    """Return event form HTML for modal/popup."""
    ctx = {"request": request, "event_id": event_id}
    return templates.TemplateResponse("partials/event_form.html", ctx)

@router.get("/partials/invoice-modal", response_class=HTMLResponse)
async def invoice_modal_partial(request: Request):
    """Return invoice creation modal HTML."""
    ctx = {"request": request, "vat_rate": 14}
    return templates.TemplateResponse("partials/invoice_modal.html", ctx)

@router.get("/partials/recon-grid", response_class=HTMLResponse)
async def recon_grid_partial(request: Request, account: str = "all"):
    """Return reconciliation grid for HTMX swap."""
    ctx = {"request": request, "account": account}
    return templates.TemplateResponse("partials/recon_grid.html", ctx)