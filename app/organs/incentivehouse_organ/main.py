"""
IncentiveHouse ERP - FastAPI Server Bootstrap
==============================================
Self-contained runnable FastAPI app. Three ways to start:
  1. Standalone: uvicorn app.organs.incentivehouse_organ.main:app --port 8001
  2. As sub-app: app.mount("/api/v1/incentivehouse", ih_app)
  3. As script:  python -m app.organs.incentivehouse_organ.main

Wires DB session middleware, static files, Jinja2 templates, all routers,
alembic-friendly first boot (Base.metadata.create_all safety net so the
container stays up), CORS, security headers, lifespan startup/shutdown.

This is the critical path - every other router (BNK variance, event API,
etc.) plugs in via include_router.
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse, HTMLResponse, JSONResponse, RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.organs.incentivehouse_organ.db import (
    get_async_db, get_async_session_factory, get_db,
    get_sync_engine, get_sync_session_factory,
)
from app.organs.incentivehouse_organ.models import (
    IncentiveBase, PRODUCTION_TABLE_NAMES, STAGING_TABLE_NAMES,
)
from app.organs.incentivehouse_organ.schemas import (
    AgentStatusResponse, ExtractionRequest, ExtractionResponse,
    ModuleExtractionResult, PromoteRequest, PromoteResponse,
    SourceFileInfo, SourceListResponse, StagingListResponse,
    StagingQuery, StagingRecord,
)
from app.organs.incentivehouse_organ.router import router as incentivehouse_router
from app.organs.incentivehouse_organ.routers.bnk_router import router as bnk_router
from app.organs.incentivehouse_organ.sub_app import incentivehouse_app

# New module routers (added by deploy_all.py)
from app.organs.incentivehouse_organ.routers.sal_router import router as sal_router
from app.organs.incentivehouse_organ.routers.pur_router import router as pur_router
from app.organs.incentivehouse_organ.routers.evn_router import router as evn_router
from app.organs.incentivehouse_organ.routers.env_router import router as env_router
from app.organs.incentivehouse_organ.routers.recon_router import router as recon_router

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("incentivehouse_organ.main")

# Paths
ORGAN_DIR: Path = Path(__file__).parent
TEMPLATES_DIR: Path = ORGAN_DIR / "templates"
STATIC_DIR: Path = ORGAN_DIR / "static"
CONFIG_DIR: Path = ORGAN_DIR / "config"
SOURCES_PATH: Path = CONFIG_DIR / "source_paths.yaml"

# Settings
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./protocell_staging.db")
SYNC_DATABASE_URL: str = os.getenv(
    "SYNC_DATABASE_URL",
    DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", ""),
)
ALLOW_AUTO_CREATE: bool = os.getenv("ALLOW_AUTO_CREATE", "true").lower() == "true"

# Ensure template/static dirs exist
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Legacy dev users
AUTH_USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "accountant": {"password": "acc123", "role": "Accountant"},
    "event_mgr": {"password": "evn123", "role": "EventManager"},
    "viewer": {"password": "view123", "role": "Viewer"},
}


# ============================================================================
# Middleware
# ============================================================================

class DBSessionMiddleware(BaseHTTPMiddleware):
    """Stash a per-request sync DB session in request.state.db_session."""

    async def dispatch(self, request: Request, call_next):
        factory = get_sync_session_factory()
        session = factory()
        request.state.db_session = session
        try:
            response = await call_next(request)
        finally:
            session.close()
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = datetime.now()
        response = await call_next(request)
        dur_ms = (datetime.now() - start).total_seconds() * 1000.0
        logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path,
                    response.status_code, dur_ms)
        return response


# ============================================================================
# First-boot table creation (alembic safety net)
# ============================================================================

AUX_TABLES_SQL = [
    """CREATE TABLE IF NOT EXISTS extraction_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT NOT NULL,
        source_file TEXT, user_id TEXT, status TEXT, extracted_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS validation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, extract_id INTEGER, user_id TEXT,
        status TEXT, quality_score REAL, validated_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS staging_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, validate_id INTEGER,
        target_table TEXT, user_id TEXT, snapshot_id TEXT, status TEXT,
        staged_at TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS reconcile_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, stage_id INTEGER, module TEXT,
        user_id TEXT, status TEXT, total_records INTEGER DEFAULT 0,
        reconciled_count INTEGER DEFAULT 0, mismatch_count INTEGER DEFAULT 0,
        unmatched_count INTEGER DEFAULT 0, reconciled_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS approval_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, recon_id INTEGER, approver_id TEXT,
        approval_level TEXT, status TEXT, approved_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS promotion_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, approve_id INTEGER, user_id TEXT,
        rollback_token TEXT, status TEXT, promoted_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS observe_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, promote_id INTEGER, user_id TEXT,
        status TEXT, metrics TEXT, observed_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS bnk_reconciliation (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT,
        check_book_id INTEGER, check_book_name TEXT, bank_amount REAL,
        gl_amount REAL, variance REAL, recon_status TEXT,
        user_sub_led TEXT, user_type TEXT, user_keyword TEXT, user_notes TEXT)""",
]


def _ensure_tables_sync() -> None:
    if not ALLOW_AUTO_CREATE:
        logger.info("ALLOW_AUTO_CREATE=false - skipping create_all")
        return
    try:
        eng = get_sync_engine()
        IncentiveBase.metadata.create_all(bind=eng)
        with eng.begin() as conn:
            for sql in AUX_TABLES_SQL:
                conn.execute(text(sql))
        logger.info("Organ tables ensured (Base.metadata.create_all + aux SQL).")
    except Exception as exc:
        logger.warning("ensure_tables failed: %s", exc)


# ============================================================================
# Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 72)
    logger.info("IncentiveHouse ERP FastAPI starting up")
    logger.info("DATABASE_URL=%s", DATABASE_URL.split("@")[-1])
    logger.info("TEMPLATES_DIR=%s", TEMPLATES_DIR)
    logger.info("STATIC_DIR=%s", STATIC_DIR)
    _ensure_tables_sync()
    try:
        eng = get_sync_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connectivity OK")
    except Exception as exc:
        logger.error("Database connectivity FAILED at startup: %s", exc)
    logger.info("=" * 72)
    yield
    logger.info("IncentiveHouse ERP FastAPI shutting down")


# ============================================================================
# App factory
# ============================================================================

def create_app() -> FastAPI:
    app = FastAPI(
        title="IncentiveHouse ERP",
        description=(
            "Legacy Excel -> PostgreSQL migration pipeline. "
            "5 modules: Bnk, Sal, Pur, Evn, Env. All writes to *_staging "
            "tables only; production requires explicit promote."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    # Middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(DBSessionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    # Static + templates
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    # Routers
    _mount_legacy_v2(app)
    _mount_extraction(app)
    _mount_jinja_pages(app, templates)
    _mount_api_routers(app)
    # Health + errors
    _register_exception_handlers(app)
    _register_health(app)
    return app


# ============================================================================
# Legacy /v2/* routes (imported from legacy_routes.py)
# ============================================================================

def _mount_legacy_v2(app: FastAPI) -> None:
    from app.organs.incentivehouse_organ.legacy_routes import (
        mount_legacy_v2_routes,
    )
    mount_legacy_v2_routes(app)


# ============================================================================
# New extraction agent routes (delegate to production_trx_agent)
# ============================================================================

def _load_sources() -> dict:
    try:
        import yaml
        with open(SOURCES_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {"sources": {}, "module_groups": {}, "all_modules": []}


def _mount_extraction(app: FastAPI) -> None:

    @app.get("/sources", response_model=SourceListResponse)
    def list_sources():
        cfg = _load_sources()
        items = [
            SourceFileInfo(
                key=k, path=v.get("path", ""), description=v.get("description", ""),
                sheet=v.get("sheet"), split_to=v.get("split_to", []),
            )
            for k, v in cfg.get("sources", {}).items()
        ]
        return SourceListResponse(sources=items)

    @app.post("/extract", response_model=ExtractionResponse)
    async def run_extraction(
        req: ExtractionRequest, db: Session = Depends(get_db),
    ):
        from app.organs.incentivehouse_organ.production_trx_agent import (
            ProductionTrxAgent, ExtractionContext,
        )
        agent = ProductionTrxAgent(db, config_dir=str(CONFIG_DIR))
        ctx = ExtractionContext(
            file_path=req.file_path, module=req.module,
            sheet_name=req.sheet_name, header_row=req.header_row,
            batch_size=req.batch_size, dry_run=req.dry_run,
        )
        manifest = agent.execute(ctx)
        result = ModuleExtractionResult(
            agent_id=manifest.agent_id, module=manifest.module,
            source_file=manifest.source_file, total_rows=manifest.total_rows,
            passed=manifest.passed, warnings=manifest.warnings,
            failed=manifest.failed, staged=manifest.staged,
            summary=manifest.summary, errors=manifest.errors[:20],
            started_at=manifest.started_at,
            completed_at=datetime.now().isoformat(),
        )
        return ExtractionResponse(
            batch_id=manifest.agent_id, results=[result],
            total_rows=result.total_rows, total_staged=result.staged,
            total_passed=result.passed, total_warnings=result.warnings,
            total_failed=result.failed, dry_run=req.dry_run,
            timestamp=datetime.now().isoformat(),
        )

    @app.post("/extract/all", response_model=ExtractionResponse)
    async def run_extraction_all(
        dry_run: bool = Query(default=True),
        batch_size: int = Query(default=500, ge=1, le=5000),
        db: Session = Depends(get_db),
    ):
        from app.organs.incentivehouse_organ.production_trx_agent import (
            ProductionTrxAgent, ExtractionContext,
        )
        cfg = _load_sources()
        agent = ProductionTrxAgent(db, config_dir=str(CONFIG_DIR))
        all_results = []
        tr = ts = tp = tw = tf = 0
        for mod_key in cfg.get("all_modules", []):
            group = cfg.get("module_groups", {}).get(mod_key, [mod_key])
            for source_key in group:
                info = cfg.get("sources", {}).get(source_key)
                if not info:
                    continue
                fp = info.get("path", "")
                if not Path(fp).exists():
                    continue
                ctx = ExtractionContext(
                    file_path=fp, module=mod_key, sheet_name=info.get("sheet"),
                    batch_size=batch_size, dry_run=dry_run,
                )
                m = agent.execute(ctx)
                r = ModuleExtractionResult(
                    agent_id=m.agent_id, module=m.module, source_file=m.source_file,
                    total_rows=m.total_rows, passed=m.passed, warnings=m.warnings,
                    failed=m.failed, staged=m.staged, summary=m.summary,
                    errors=m.errors[:20], started_at=m.started_at,
                    completed_at=datetime.now().isoformat(),
                )
                all_results.append(r)
                tr += r.total_rows; ts += r.staged; tp += r.passed
                tw += r.warnings; tf += r.failed
        return ExtractionResponse(
            batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            results=all_results, total_rows=tr, total_staged=ts,
            total_passed=tp, total_warnings=tw, total_failed=tf,
            dry_run=dry_run, timestamp=datetime.now().isoformat(),
        )

    @app.get("/agent/status", response_model=AgentStatusResponse)
    def agent_status():
        return AgentStatusResponse(
            agent_id="production_trx_agent", status="ready",
            last_run=None, uptime=datetime.now().isoformat(),
        )


# ============================================================================
# Jinja2 page routes (HTML pages)
# ============================================================================

def _mount_jinja_pages(app: FastAPI, templates: Jinja2Templates) -> None:

    @app.get("/", response_class=HTMLResponse)
    def main_dashboard(request: Request):
        return templates.TemplateResponse("main_dashboard.html", {"request": request})

    @app.get("/api/v1/incentivehouse/events/new", response_class=HTMLResponse)
    def new_event_form(request: Request):
        return templates.TemplateResponse("event_form.html", {"request": request})

    @app.get("/api/v1/incentivehouse/recon/form", response_class=HTMLResponse)
    def recon_form(request: Request):
        return templates.TemplateResponse("bank_recon_form.html", {"request": request})

    @app.get("/api/v1/incentivehouse/purchasing", response_class=HTMLResponse)
    def purchasing_page(request: Request):
        return templates.TemplateResponse("purchasing.html", {"request": request})

    @app.get("/api/v1/incentivehouse/search", response_class=HTMLResponse)
    def search_page(request: Request):
        return templates.TemplateResponse("search.html", {"request": request})

    @app.get("/api/v1/incentivehouse/docs")
    def api_docs_redirect():
        return RedirectResponse(url="/docs")


# ============================================================================
# API routers (staging + promote + audit + recon)
# ============================================================================

def _mount_api_routers(app: FastAPI) -> None:
    # New-style incentivehouse router (staging query, summary, promote, audit)
    app.include_router(incentivehouse_router)
    # BNK-specific router (transactions, summary, load, reload)
    app.include_router(bnk_router)
    # New module routers
    app.include_router(sal_router)
    app.include_router(pur_router)
    app.include_router(evn_router)
    app.include_router(env_router)
    app.include_router(recon_router)
    # Mount the existing sub-application under /api/v1/incentivehouse
    # (the sub-app defines event_form, etc. as separate routes)
    app.mount("/api/v1/incentivehouse", incentivehouse_app)


# ============================================================================
# Health + error handlers
# ============================================================================

def _register_health(app: FastAPI) -> None:

    @app.get("/health")
    def health_check():
        db_status = "unknown"
        try:
            eng = get_sync_engine()
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            logger.warning("Health check DB failure: %s", exc)
            db_status = "error"
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "version": "1.0.0",
            "database": db_status,
            "modules": ["Bnk", "Sal", "Pur", "Evn", "Env"],
            "staging_tables": list(STAGING_TABLE_NAMES.keys()),
            "production_tables": list(PRODUCTION_TABLE_NAMES.keys()),
        }


def _register_exception_handlers(app: FastAPI) -> None:

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
            return HTMLResponse(
                "<div class='alert alert-danger'>An unexpected error occurred.</div>",
                status_code=500,
            )
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"},
        )


# ============================================================================
# Module-level app for ``uvicorn app.organs.incentivehouse_organ.main:app``
# ============================================================================

app = create_app()


# ============================================================================
# Convenience: count records across all staging tables (used by /health)
# ============================================================================

def _staging_record_counts() -> dict:
    out: dict = {}
    try:
        eng = get_sync_engine()
        with eng.connect() as conn:
            for mod, table in STAGING_TABLE_NAMES.items():
                try:
                    out[mod] = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar() or 0
                except Exception:
                    out[mod] = None
    except Exception:
        pass
    return out


if __name__ == "__main__":
    import uvicorn
    counts = _staging_record_counts()
    logger.info("Starting IncentiveHouse ERP standalone - staging counts: %s", counts)
    uvicorn.run(
        "app.organs.incentivehouse_organ.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8001")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
