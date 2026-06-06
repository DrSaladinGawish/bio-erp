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
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.logging_middleware import CorrelationIDMiddleware
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.metrics import PrometheusMiddleware

from app.config import settings
from app.database import get_async_engine, get_db, init_db
import app.models.manufacturing  # noqa: F401  — register tables with Base
import app.ai_ingest.models  # noqa: F401  — register AI ingestion tables with Base
import app.models.neural.prediction  # noqa: F401  — register neural tables with Base

# OR-ERP Sub-Application
from app.organs.or_organ.sub_app import or_app

# SCM Costing & Performance Sub-Application
from app.organs.scm_organ.sub_app import scm_app

# IncentiveHouse ERP Legacy Migration Sub-Application
from app.organs.incentivehouse_organ.sub_app import incentivehouse_app

# IncentiveHouse module routers (BNK, SAL, PUR, EVN, ENV)
from app.organs.incentivehouse_organ.routers.bnk_router import router as ih_bnk_router
from app.organs.incentivehouse_organ.routers.sal_router import router as ih_sal_router
from app.organs.incentivehouse_organ.routers.pur_router import router as ih_pur_router
from app.organs.incentivehouse_organ.routers.evn_router import router as ih_evn_router
from app.organs.incentivehouse_organ.routers.env_router import router as ih_env_router

from app.routers import (
    accounting,
    documents,
    admin,
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
    pages,
    petty_cash,
    procurement,
    reports,
    strategic_routers,
    suppliers,
    system,
    websocket_alerts,
)
from app.routers.currency import conversion_router
from app.routers.intelligence_router import router as intelligence_router
from app.routers.neural.ai_api import router as neural_router
from app.routers.roles import router as roles_router
from app.routers.event_ops import router as event_ops_router
from app.cells.rbac_cell.router import router as rbac_router

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BIO_ERP v5.2...")
    engine = get_async_engine()
    try:
        async with engine.begin() as conn:
            from app.models import Base
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning("Could not create tables (may already exist): %s", e)

    from app.auth import hash_password
    from app.models import User
    async for db in get_db():
        try:
            result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
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
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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

# RBAC Cell (Casbin)
app.include_router(rbac_router)

# User Roles & Permissions
app.include_router(roles_router)

# EventCore Bridge
app.include_router(eventcore_bridge.router)

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
# In-house sub-app (auth, events/create, dashboard, recon)
app.mount("/api/v1/incentivehouse", incentivehouse_app)

# P2 Reverse Flow — Doctor (BIO-ERP) -> Patient (EventCore)
from app.p2_reverse_flow.reverse_flow import reverse_router
app.include_router(reverse_router, prefix="/api/v1")

# Jinja2 Page Router — All HTML templates
from app.routers.pages import router as pages_router
app.include_router(pages_router)

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
