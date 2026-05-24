from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import get_async_engine, get_db, init_db
import app.models.manufacturing  # noqa: F401  — register tables with Base
from app.routers import (
    accounting,
    admin,
    ai_bridge,
    approval,
    auth,
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
    yield
    logger.info("Shutting down BIO_ERP v5.2...")


app = FastAPI(
    title="BIO_ERP v5",
    version="5.2.0",
    lifespan=lifespan,
)

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
app.include_router(currency.router)
app.include_router(branch.router)
app.include_router(clients.router)
app.include_router(suppliers.router)
app.include_router(items.router)

# Events & budget
app.include_router(events.router)
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

# AI bridge
app.include_router(ai_bridge.router)

# WebSocket alerts
app.include_router(websocket_alerts.router)

# Reports
app.include_router(reports.router)


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
async def root():
    return {"message": "BIO_ERP v5", "version": "5.2.0"}


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
        "version": "5.2.0",
        "database": db_status,
    }
