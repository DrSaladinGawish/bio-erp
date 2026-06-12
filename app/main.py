from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select, text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.logging_middleware import CorrelationIDMiddleware
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.metrics import PrometheusMiddleware

from app.config import settings
from app.database import get_async_engine, get_db
import app.models.manufacturing  # noqa: F401  — register tables with Base
import app.ai_ingest.models  # noqa: F401  — register AI ingestion tables with Base
import app.models.neural.prediction  # noqa: F401  — register neural tables with Base

# OR-ERP Sub-Application
from app.organs.or_organ.sub_app import or_app

# SCM Costing & Performance Sub-Application
from app.organs.scm_organ.sub_app import scm_app

# IncentiveHouse module routers (BNK, SAL, PUR, EVN, ENV — must be imported BEFORE sub_app
# to ensure models_production is loaded before models_empty_modules)
from app.organs.incentivehouse_organ.routers.bnk_router import router as ih_bnk_router
from app.organs.incentivehouse_organ.routers.sal_router import router as ih_sal_router
from app.organs.incentivehouse_organ.routers.pur_router import router as ih_pur_router
from app.organs.incentivehouse_organ.routers.evn_router import router as ih_evn_router
from app.organs.incentivehouse_organ.routers.env_router import router as ih_env_router
# Empty-module routers (GRN, Cost, Event Budget, BSC, BI, Budget)
from app.organs.incentivehouse_organ.routers.grn_router import router as ih_grn_router
from app.organs.incentivehouse_organ.routers.cost_router import router as ih_cost_router
from app.organs.incentivehouse_organ.routers.event_budget_router import router as ih_eb_router
from app.organs.incentivehouse_organ.routers.bsc_router import router as ih_bsc_router
from app.organs.incentivehouse_organ.routers.bi_router import router as ih_bi_router
from app.organs.incentivehouse_organ.routers.budget_router import router as ih_budget_router
from app.organs.incentivehouse_organ.routers.approval_router import router as ih_approval_router
from app.organs.incentivehouse_organ.routers.ops_router import router as ih_ops_router
# IncentiveHouse ERP Legacy Migration Sub-Application (import AFTER production routers
# so models_production is loaded before models_empty_modules)
from app.organs.incentivehouse_organ.sub_app import incentivehouse_app

# Admin Router with role-based permissions
from app.organs.incentivehouse_organ.admin_router import router as ih_admin_router

from app.routers import (
    accounting,
    documents,
    admin,
    dashboard_api,
    status_v2,
    ai_bridge,
    approval,
    auth,
    bank_recon,
    batches,
    bio_entities,
    branch,
    budget,
    budget_lifecycle,
    calculators,
    clients,
    coa,
    cost_management,
    costing,
    currency,
    dashboard,
    dashboard_v2,
    eta,
    eventcore_bridge,
    events,
    finance,
    grdslab,
    htmx_dashboard,
    items,
    petty_cash,
    procurement,
    reports,
    strategic_routers,
    suppliers,
    system,
    websocket_alerts,
)
from app.routers.gl_router import router as gl_router
from app.routers.search import router as search_router
from app.routers.export import router as export_router
from app.routers.currency import conversion_router
from app.routers.intelligence_router import router as intelligence_router
from app.routers.neural.ai_api import router as neural_router
from app.routers.roles import router as roles_router
from app.routers.event_ops import router as event_ops_router
from app.evops.router import router as evops_router
from app.cells.rbac_cell.router import router as rbac_router
from app.copilot.router import router as copilot_router

# Meta Layer v2 — dashboard, list, nav, report, export, drill-down
from app.meta_layer import MetaLayerInjectorMiddleware, meta_router, meta_v2_router

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BIO_ERP v5.2...")
    engine = get_async_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS dbo"))
            await conn.commit()
    except Exception as e:
        logger.warning("Could not create dbo schema (may already exist): %s", e)

    try:
        from app.models import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()
    except Exception as e:
        logger.warning("Could not create app tables (may already exist): %s", e)

    try:
        from app.database import IHEBase

        async with engine.begin() as conn:
            await conn.run_sync(IHEBase.metadata.create_all)
            await conn.commit()
    except Exception as e:
        logger.warning("Could not create IHE tables (may already exist): %s", e)

    from app.auth import hash_password
    from app.models import User, Branch

    async for db in get_db():
        try:
            # Ensure at least one branch exists (User.branch_id defaults to 1)
            branch = await db.get(Branch, 1)
            if not branch:
                db.add(
                    Branch(
                        id=1,
                        code="HO",
                        name_en="Head Office",
                        name_ar="المكتب الرئيسي",
                        is_hq=True,
                    )
                )
                await db.commit()

            result = await db.execute(
                select(User).where(User.username == settings.ADMIN_USERNAME)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                admin = User(
                    username=settings.ADMIN_USERNAME,
                    email=settings.ADMIN_EMAIL,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    full_name_en=settings.ADMIN_FULL_NAME,
                    is_superuser=True,
                )
                db.add(admin)
                await db.commit()
                logger.info("Admin user created: %s", settings.ADMIN_USERNAME)

            # Seed Flask-compatible roles & permissions
            from app.seed import seed_all

            await seed_all(db)
            logger.info("Roles and permissions seeded")
        finally:
            await db.close()
        break

    # Start APScheduler for Time-of-Day tasks
    from apscheduler.triggers.cron import CronTrigger
    from app.services.cbe_sync import start_cbe_scheduler
    from app.services.document_service import run_nightly_verify

    _scheduler = start_cbe_scheduler()
    _scheduler.add_job(
        run_nightly_verify,
        CronTrigger(hour=2, minute=0, timezone="Africa/Cairo"),
        id="nightly_doc_verify",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("CBE scheduler started — daily at 06:00 Cairo")
    logger.info("Nightly document verify scheduled — 02:00 Cairo")

    yield
    _scheduler.shutdown(wait=False)
    logger.info("Shutting down BIO_ERP v5.2...")


app = FastAPI(
    title="BIO_ERP v5",
    version="5.3.0",
    lifespan=lifespan,
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response


# Middleware stack (last added = outermost/first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(MetaLayerInjectorMiddleware)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Core accounting (merged: login + HTMX ledger + financial reports)
app.include_router(accounting.router)

# Manufacturing (ERP-PC unique)
app.include_router(batches.router)
app.include_router(bio_entities.router)
app.include_router(calculators.router)

# Auth & admin
app.include_router(auth.router)
app.include_router(admin.router)

# Financial modules
app.include_router(finance.router)
app.include_router(coa.router)
app.include_router(bank_recon.router)
app.include_router(currency.router)
app.include_router(conversion_router)
app.include_router(branch.router)
app.include_router(clients.router)
app.include_router(suppliers.router)
app.include_router(items.router)

# Events & budget
app.include_router(events.router)
app.include_router(event_ops_router)
app.include_router(evops_router, prefix="/api/v1/evops", tags=["Event Operations v2"])
app.include_router(budget.router)
app.include_router(budget_lifecycle.router)

# Procurement
app.include_router(procurement.router)

# Costing
app.include_router(costing.router)
app.include_router(cost_management.router)
app.include_router(strategic_routers.router)

# Dashboard & HTMX
app.include_router(dashboard.router)
app.include_router(dashboard_v2.router)
app.include_router(htmx_dashboard.router)
app.include_router(dashboard_api.router)
app.include_router(status_v2.router)

# ETA e-invoicing
app.include_router(eta.router)

# Petty cash
app.include_router(petty_cash.router)

# Approval workflow
app.include_router(approval.router)

# GRDSLAB calculator
app.include_router(grdslab.router)

# System utilities
app.include_router(system.router)

# Documents
app.include_router(documents.router)

# AI bridge
app.include_router(ai_bridge.router)

# Neural AI Module
app.include_router(neural_router)

# AI Ingestion Module
from app.ai_ingest.router import router as ai_ingest_router

app.include_router(ai_ingest_router)

# Intelligence (AI, email, etc.)
app.include_router(intelligence_router)

# WebSocket alerts
app.include_router(websocket_alerts.router)

# Reports
app.include_router(reports.router)

# GL Module (accounts, employees, vouchers)
app.include_router(gl_router)

# Search API
app.include_router(search_router)

# Export API
app.include_router(export_router)

# RBAC Cell (Casbin)
app.include_router(rbac_router)

# User Roles & Permissions
app.include_router(roles_router)

# Co-Pilot Smart Modules (19 endpoints at /copilot)
app.include_router(copilot_router)

# EventCore Bridge
app.include_router(eventcore_bridge.router)

# Meta Layer v2 — dashboard, list, nav, report, export, drill-down
app.include_router(meta_router)
app.include_router(meta_v2_router)

# OR-ERP Operations Research Module (mounted at /api/v1/or)
app.mount("/api/v1/or", or_app)

# SCM Costing & Performance Module (mounted at /api/v1/scm)
app.mount("/api/v1/scm", scm_app)

# IncentiveHouse ERP module routers (BNK, SAL, PUR, EVN, ENV — provide own /api/v1/* prefixes)
app.include_router(ih_bnk_router)
app.include_router(ih_sal_router)
app.include_router(ih_pur_router)
app.include_router(ih_evn_router)
app.include_router(ih_env_router)
# Empty-module routers (GRN, Cost, Event Budget, BSC, BI, Budget, Approval)
app.include_router(ih_grn_router)
app.include_router(ih_cost_router)
app.include_router(ih_eb_router)
app.include_router(ih_bsc_router)
app.include_router(ih_bi_router)
app.include_router(ih_budget_router)
app.include_router(ih_approval_router)
app.include_router(ih_ops_router)
# Admin module with role-based permissions
app.include_router(ih_admin_router)
# In-house sub-app (auth, events/create, dashboard, recon)
app.mount("/api/v1/incentivehouse", incentivehouse_app)

# P2 Reverse Flow — Doctor (BIO-ERP) -> Patient (EventCore)
from app.p2_reverse_flow.reverse_flow import reverse_router

app.include_router(reverse_router, prefix="/api/v1")

# Jinja2 Page Router — All HTML templates
from app.routers.pages import router as pages_router
from app.routers.doctor_reports import router as doctor_reports_router

app.include_router(pages_router)
app.include_router(doctor_reports_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    if "HX-Request" in request.headers:
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            "<div class='alert alert-danger'>An unexpected error occurred.</div>",
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return FileResponse(str(BASE_DIR / "static" / "index.html"))
    return {
        "message": "BIO_ERP v5",
        "version": "5.3.0",
        "linked_systems": [
            {"name": "BIO_ERP v5", "url": "http://localhost:8000"},
            {"name": "EventCore ERP", "url": "http://localhost:8001/dashboard"},
        ],
    }


@app.get("/transactions", response_class=FileResponse)
async def transactions_page():
    return FileResponse(str(BASE_DIR / "static" / "transactions.html"))


@app.get("/app/{catchall:path}", response_class=FileResponse)
async def app_spa(catchall: str):
    path = BASE_DIR / "static" / catchall
    if path.is_file():
        return FileResponse(str(path))
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.get("/ai-ingest")
async def ai_ingest_page():
    from app.template_engine import render_template

    return render_template("ai_ingest.html", {"current_user": None})


@app.get("/health")
async def health():
    try:
        async for db in get_db():
            await db.execute(select(1))
            await db.close()
        db_status = "ok"
    except Exception as e:
        logger.warning("Health check DB failure: %s", e)
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "5.3.0",
        "database": db_status,
    }
