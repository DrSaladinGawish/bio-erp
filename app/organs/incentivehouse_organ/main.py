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

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.organs.incentivehouse_organ.db import (
    get_db,
    get_sync_engine,
    get_sync_session_factory,
)
from app.organs.incentivehouse_organ.models import (
    IncentiveBase,
    PRODUCTION_TABLE_NAMES,
    STAGING_TABLE_NAMES,
)
from app.organs.incentivehouse_organ.schemas import (
    AgentStatusResponse,
    ExtractionRequest,
    ExtractionResponse,
    ModuleExtractionResult,
    SourceFileInfo,
    SourceListResponse,
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
from app.organs.incentivehouse_organ.routers.event_ops import router as event_ops_router
from app.organs.incentivehouse_organ.event_ops_router import (
    router as event_ops_phase5_router,
)

# P0/P1/P2/P3 modules (RBAC, Audit, Backup, Presentations, DMS, Event Bridge, SCM)
from app.organs.incentivehouse_organ.audit_service import router as audit_router
from app.organs.incentivehouse_organ.backup_service import router as backup_router
from app.organs.incentivehouse_organ.presentation_engine import (
    router as presentation_router,
)
from app.organs.incentivehouse_organ.dms_service import router as dms_router
from app.organs.incentivehouse_organ.event_bridge import router as event_bridge_router
from app.organs.incentivehouse_organ.scm_bio_bridge import router as scm_bridge_router
from app.organs.incentivehouse_organ.scm_cost_engine import (
    router as scm_cost_engine_router,
)
from app.organs.incentivehouse_organ.routers.financial_reports import (
    router as financial_reports_router,
)
from app.organs.incentivehouse_organ.routers.e_invoice import (
    router as e_invoice_router,
)

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
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp"
)
SYNC_DATABASE_URL: str = os.getenv(
    "SYNC_DATABASE_URL",
    DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", ""),
)
ALLOW_AUTO_CREATE: bool = os.getenv("ALLOW_AUTO_CREATE", "true").lower() == "true"

# Ensure template/static dirs exist
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


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
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            dur_ms,
        )
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
    # IHE-ERP v2.3 intelligence layer
    """CREATE TABLE IF NOT EXISTS audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT, table_name TEXT NOT NULL,
        record_id TEXT, action TEXT NOT NULL, old_value TEXT, new_value TEXT,
        user_id TEXT, ip_address TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        extra TEXT)""",
    """CREATE INDEX IF NOT EXISTS ix_audit_table_name ON audit_trail(table_name)""",
    """CREATE INDEX IF NOT EXISTS ix_audit_record_id ON audit_trail(record_id)""",
    """CREATE INDEX IF NOT EXISTS ix_audit_timestamp ON audit_trail(timestamp)""",
]

# IHE-ERP v2.5.0: Event Lifecycle Operations — idempotent column migrations
MIGRATIONS_SQL = [
    # Add lifecycle_status column (v2.5.0)
    "ALTER TABLE events ADD COLUMN lifecycle_status VARCHAR(20) DEFAULT 'DRAFT'",
    "ALTER TABLE events ADD COLUMN ops_team_id INTEGER REFERENCES staff_mtbl(id)",
    "ALTER TABLE events ADD COLUMN execution_date DATETIME",
    "ALTER TABLE events ADD COLUMN actual_pax INTEGER",
    "ALTER TABLE events ADD COLUMN actual_cost NUMERIC(15,2)",
    # Event operations table (v2.5.0)
    """CREATE TABLE IF NOT EXISTS event_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL UNIQUE REFERENCES events(id),
        ops_manager_id INTEGER REFERENCES staff_mtbl(id),
        briefing_completed INTEGER DEFAULT 0,
        load_in_time DATETIME,
        sound_check_done INTEGER DEFAULT 0,
        catering_final_count INTEGER,
        run_sheet TEXT DEFAULT '[]',
        post_event_notes TEXT,
        client_signatory_name VARCHAR(100),
        client_signature_path VARCHAR(255),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    # Document Management System tables
    """CREATE TABLE IF NOT EXISTS supporting_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_name VARCHAR(32) NOT NULL,
        function_name VARCHAR(32) NOT NULL,
        transaction_table VARCHAR(64) NOT NULL,
        transaction_id VARCHAR(64) NOT NULL,
        original_usb_path TEXT,
        archive_path TEXT NOT NULL,
        file_hash_sha256 VARCHAR(64) NOT NULL,
        file_size_bytes BIGINT NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_ext VARCHAR(10) NOT NULL,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verified_at TIMESTAMP,
        status VARCHAR(16) DEFAULT 'linked',
        uploaded_by VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS document_modules (
        module_name VARCHAR(32) NOT NULL,
        function_name VARCHAR(32) NOT NULL,
        transaction_table VARCHAR(64) NOT NULL,
        description TEXT,
        filename_pattern VARCHAR(255),
        PRIMARY KEY (module_name, function_name)
    )""",
    # Phase 3-5: Event checkpoints table
    """CREATE TABLE IF NOT EXISTS event_checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
        checkpoint_id VARCHAR(50) NOT NULL,
        label VARCHAR(200) NOT NULL,
        stage VARCHAR(20) NOT NULL DEFAULT 'ops_assigned',
        required INTEGER DEFAULT 1,
        completed_at DATETIME,
        completed_by VARCHAR(100),
        notes TEXT,
        due_date DATETIME,
        sort_order INTEGER DEFAULT 0,
        linked_document_id INTEGER,
        linked_po_id INTEGER,
        linked_invoice_id INTEGER,
        extra_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_checkpoints_event_stage ON event_checkpoints(event_id, stage)""",
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
            for sql in MIGRATIONS_SQL:
                try:
                    conn.execute(text(sql))
                except Exception:
                    pass  # Column likely already exists, or table exists
        logger.info(
            "Organ tables ensured (Base.metadata.create_all + aux SQL + migrations)."
        )
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
        allow_origins=os.getenv(
            "CORS_ALLOW_ORIGINS", "http://localhost:8002,http://127.0.0.1:8002"
        ).split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Static + templates
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    # Routers
    _mount_extraction(app)
    _mount_jinja_pages(app, templates)
    _mount_api_routers(app, templates)
    # Health + errors
    _register_exception_handlers(app)
    _register_health(app)
    return app


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
                key=k,
                path=v.get("path", ""),
                description=v.get("description", ""),
                sheet=v.get("sheet"),
                split_to=v.get("split_to", []),
            )
            for k, v in cfg.get("sources", {}).items()
        ]
        return SourceListResponse(sources=items)

    @app.post("/extract", response_model=ExtractionResponse)
    async def run_extraction(
        req: ExtractionRequest,
        db: Session = Depends(get_db),
    ):
        from app.organs.incentivehouse_organ.production_trx_agent import (
            ProductionTrxAgent,
            ExtractionContext,
        )

        agent = ProductionTrxAgent(db, config_dir=str(CONFIG_DIR))
        ctx = ExtractionContext(
            file_path=req.file_path,
            module=req.module,
            sheet_name=req.sheet_name,
            header_row=req.header_row,
            batch_size=req.batch_size,
            dry_run=req.dry_run,
        )
        manifest = agent.execute(ctx)
        result = ModuleExtractionResult(
            agent_id=manifest.agent_id,
            module=manifest.module,
            source_file=manifest.source_file,
            total_rows=manifest.total_rows,
            passed=manifest.passed,
            warnings=manifest.warnings,
            failed=manifest.failed,
            staged=manifest.staged,
            summary=manifest.summary,
            errors=manifest.errors[:20],
            started_at=manifest.started_at,
            completed_at=datetime.now().isoformat(),
        )
        return ExtractionResponse(
            batch_id=manifest.agent_id,
            results=[result],
            total_rows=result.total_rows,
            total_staged=result.staged,
            total_passed=result.passed,
            total_warnings=result.warnings,
            total_failed=result.failed,
            dry_run=req.dry_run,
            timestamp=datetime.now().isoformat(),
        )

    @app.post("/extract/all", response_model=ExtractionResponse)
    async def run_extraction_all(
        dry_run: bool = Query(default=True),
        batch_size: int = Query(default=500, ge=1, le=5000),
        db: Session = Depends(get_db),
    ):
        from app.organs.incentivehouse_organ.production_trx_agent import (
            ProductionTrxAgent,
            ExtractionContext,
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
                    file_path=fp,
                    module=mod_key,
                    sheet_name=info.get("sheet"),
                    batch_size=batch_size,
                    dry_run=dry_run,
                )
                m = agent.execute(ctx)
                r = ModuleExtractionResult(
                    agent_id=m.agent_id,
                    module=m.module,
                    source_file=m.source_file,
                    total_rows=m.total_rows,
                    passed=m.passed,
                    warnings=m.warnings,
                    failed=m.failed,
                    staged=m.staged,
                    summary=m.summary,
                    errors=m.errors[:20],
                    started_at=m.started_at,
                    completed_at=datetime.now().isoformat(),
                )
                all_results.append(r)
                tr += r.total_rows
                ts += r.staged
                tp += r.passed
                tw += r.warnings
                tf += r.failed
        return ExtractionResponse(
            batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            results=all_results,
            total_rows=tr,
            total_staged=ts,
            total_passed=tp,
            total_warnings=tw,
            total_failed=tf,
            dry_run=dry_run,
            timestamp=datetime.now().isoformat(),
        )

    @app.get("/agent/status", response_model=AgentStatusResponse)
    def agent_status():
        return AgentStatusResponse(
            agent_id="production_trx_agent",
            status="ready",
            last_run=None,
            uptime=datetime.now().isoformat(),
        )


# ============================================================================
# Jinja2 page routes (HTML pages)
# ============================================================================


def _mount_jinja_pages(app: FastAPI, templates: Jinja2Templates) -> None:

    @app.get("/", response_class=HTMLResponse)
    def main_dashboard(request: Request):
        # IHE-ERP v2.4: serve the new Chart.js-powered dashboard if it exists
        if (TEMPLATES_DIR / "dashboard.html").exists():
            return templates.TemplateResponse("dashboard.html", {"request": request})
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

    # --- IHE-ERP v2.3: Module pages served at root paths ---
    # Each module page reuses main_dashboard.html (the base layout container)
    # via {% extends %} and overrides the content block.  The base.html layout
    # is intentionally not yet wired into the running container, so we serve
    # the existing per-module HTML files for backward compatibility.

    @app.get("/evn", response_class=HTMLResponse)
    def evn_page(request: Request):
        return (
            templates.TemplateResponse("evn.html", {"request": request})
            if (TEMPLATES_DIR / "evn.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "evn"}
            )
        )

    @app.get("/sal", response_class=HTMLResponse)
    def sal_page(request: Request):
        return (
            templates.TemplateResponse("sal.html", {"request": request})
            if (TEMPLATES_DIR / "sal.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "sal"}
            )
        )

    @app.get("/pur", response_class=HTMLResponse)
    def pur_page(request: Request):
        return (
            templates.TemplateResponse("pur.html", {"request": request})
            if (TEMPLATES_DIR / "pur.html").exists()
            else templates.TemplateResponse("purchasing.html", {"request": request})
        )

    @app.get("/bnk", response_class=HTMLResponse)
    def bnk_page(request: Request):
        return (
            templates.TemplateResponse("bnk.html", {"request": request})
            if (TEMPLATES_DIR / "bnk.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "bnk"}
            )
        )

    @app.get("/gl", response_class=HTMLResponse)
    def gl_page(request: Request):
        return (
            templates.TemplateResponse("gl.html", {"request": request})
            if (TEMPLATES_DIR / "gl.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "gl"}
            )
        )

    @app.get("/grn", response_class=HTMLResponse)
    def grn_page(request: Request):
        return (
            templates.TemplateResponse("grn.html", {"request": request})
            if (TEMPLATES_DIR / "grn.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "grn"})
        )

    @app.get("/cost", response_class=HTMLResponse)
    def cost_page(request: Request):
        return (
            templates.TemplateResponse("cost.html", {"request": request})
            if (TEMPLATES_DIR / "cost.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "cost"})
        )

    @app.get("/budget", response_class=HTMLResponse)
    def bud_page(request: Request):
        return (
            templates.TemplateResponse("budget.html", {"request": request})
            if (TEMPLATES_DIR / "budget.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "budget"})
        )

    @app.get("/bsc", response_class=HTMLResponse)
    def bsc_page(request: Request):
        return (
            templates.TemplateResponse("bsc.html", {"request": request})
            if (TEMPLATES_DIR / "bsc.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "bsc"})
        )

    @app.get("/ops", response_class=HTMLResponse)
    def ops_page(request: Request):
        return (
            templates.TemplateResponse("ops.html", {"request": request})
            if (TEMPLATES_DIR / "ops.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "ops"})
        )

    @app.get("/bi", response_class=HTMLResponse)
    def bi_page(request: Request):
        return (
            templates.TemplateResponse("bi.html", {"request": request})
            if (TEMPLATES_DIR / "bi.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "bi"})
        )

    @app.get("/approval", response_class=HTMLResponse)
    def approval_page(request: Request):
        return (
            templates.TemplateResponse("approval.html", {"request": request})
            if (TEMPLATES_DIR / "approval.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "approval"})
        )

    @app.get("/workflow", response_class=HTMLResponse)
    def workflow_page(request: Request):
        return (
            templates.TemplateResponse("workflow.html", {"request": request})
            if (TEMPLATES_DIR / "workflow.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "workflow"})
        )

    @app.get("/event-budget", response_class=HTMLResponse)
    def event_budget_page(request: Request):
        return (
            templates.TemplateResponse("event_budget.html", {"request": request})
            if (TEMPLATES_DIR / "event_budget.html").exists()
            else templates.TemplateResponse("main_dashboard.html", {"request": request, "page": "event-budget"})
        )

    @app.get("/documents", response_class=HTMLResponse)
    def documents_page(request: Request):
        return (
            templates.TemplateResponse("documents.html", {"request": request})
            if (TEMPLATES_DIR / "documents.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "documents"}
            )
        )

    @app.get("/einvoice", response_class=HTMLResponse)
    def einvoice_page(request: Request):
        return (
            templates.TemplateResponse("einvoice.html", {"request": request})
            if (TEMPLATES_DIR / "einvoice.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "einvoice"}
            )
        )

    @app.get("/reports", response_class=HTMLResponse)
    def reports_page(request: Request):
        return (
            templates.TemplateResponse("reports.html", {"request": request})
            if (TEMPLATES_DIR / "reports.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "reports"}
            )
        )

    @app.get("/neural", response_class=HTMLResponse)
    def neural_page(request: Request):
        return (
            templates.TemplateResponse("neural.html", {"request": request})
            if (TEMPLATES_DIR / "neural.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "neural"}
            )
        )

    @app.get("/intelligence", response_class=HTMLResponse)
    def intelligence_page(request: Request):
        return (
            templates.TemplateResponse(
                "intelligence/dashboard.html", {"request": request}
            )
            if (TEMPLATES_DIR / "intelligence" / "dashboard.html").exists()
            else templates.TemplateResponse(
                "main_dashboard.html", {"request": request, "page": "intelligence"}
            )
        )

    @app.get("/intelligence/audit", response_class=HTMLResponse)
    def intelligence_audit_page(request: Request):
        return (
            templates.TemplateResponse(
                "intelligence/audit_log.html", {"request": request}
            )
            if (TEMPLATES_DIR / "intelligence" / "audit_log.html").exists()
            else HTMLResponse("<h1>Audit Trail</h1><p>Template not yet built.</p>")
        )

    @app.get("/intelligence/or", response_class=HTMLResponse)
    def intelligence_or_page(request: Request):
        return (
            templates.TemplateResponse(
                "intelligence/or_workbench.html", {"request": request}
            )
            if (TEMPLATES_DIR / "intelligence" / "or_workbench.html").exists()
            else HTMLResponse("<h1>OR Workbench</h1><p>Template not yet built.</p>")
        )

    @app.get("/intelligence/scm", response_class=HTMLResponse)
    def intelligence_scm_page(request: Request):
        return (
            templates.TemplateResponse(
                "intelligence/scm_workbench.html", {"request": request}
            )
            if (TEMPLATES_DIR / "intelligence" / "scm_workbench.html").exists()
            else HTMLResponse("<h1>SCM Workbench</h1><p>Template not yet built.</p>")
        )

    # ------------------------------------------------------------------
    # Financial Reports pages
    # ------------------------------------------------------------------
    @app.get("/reports/financial", response_class=HTMLResponse)
    def financial_reports_index(request: Request):
        return (
            templates.TemplateResponse("reports/financial/index.html", {"request": request})
            if (TEMPLATES_DIR / "reports" / "financial" / "index.html").exists()
            else HTMLResponse("<h1>Financial Reports</h1><p>Template not yet built.</p>")
        )

    @app.get("/reports/financial/trial-balance", response_class=HTMLResponse)
    def trial_balance_page(request: Request):
        return (
            templates.TemplateResponse("reports/financial/trial_balance.html", {"request": request})
            if (TEMPLATES_DIR / "reports" / "financial" / "trial_balance.html").exists()
            else HTMLResponse("<h1>Trial Balance</h1><p>Template not yet built.</p>")
        )

    @app.get("/reports/financial/profit-loss", response_class=HTMLResponse)
    def profit_loss_page(request: Request):
        return (
            templates.TemplateResponse("reports/financial/profit_loss.html", {"request": request})
            if (TEMPLATES_DIR / "reports" / "financial" / "profit_loss.html").exists()
            else HTMLResponse("<h1>Profit & Loss</h1><p>Template not yet built.</p>")
        )

    @app.get("/reports/financial/balance-sheet", response_class=HTMLResponse)
    def balance_sheet_page(request: Request):
        return (
            templates.TemplateResponse("reports/financial/balance_sheet.html", {"request": request})
            if (TEMPLATES_DIR / "reports" / "financial" / "balance_sheet.html").exists()
            else HTMLResponse("<h1>Balance Sheet</h1><p>Template not yet built.</p>")
        )

    @app.get("/reports/financial/cash-flow", response_class=HTMLResponse)
    def cash_flow_page(request: Request):
        return (
            templates.TemplateResponse("reports/financial/cash_flow.html", {"request": request})
            if (TEMPLATES_DIR / "reports" / "financial" / "cash_flow.html").exists()
            else HTMLResponse("<h1>Cash Flow</h1><p>Template not yet built.</p>")
        )

    @app.get("/ops-dashboard", response_class=HTMLResponse)
    async def ops_dashboard_page(request: Request):
        return templates.TemplateResponse("ops_dashboard.html", {"request": request})

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        return (
            templates.TemplateResponse("login.html", {"request": request})
            if (TEMPLATES_DIR / "login.html").exists()
            else HTMLResponse(
                "<h1>Login</h1><form method='post' action='/api/v1/incentivehouse/auth/login'>"
                "<input name='username'><input name='password' type='password'>"
                "<button>Login</button></form>"
            )
        )

    # --- IHE-ERP v2.3: New-form routes (Path A UI remediation) ---
    @app.get("/evn/new", response_class=HTMLResponse)
    def evn_new_page(request: Request):
        return (
            templates.TemplateResponse("pnr_form.html", {"request": request})
            if (TEMPLATES_DIR / "pnr_form.html").exists()
            else HTMLResponse("<h1>New PNR</h1><p>Form template not yet built.</p>")
        )

    @app.get("/sal/new", response_class=HTMLResponse)
    def sal_new_page(request: Request):
        return (
            templates.TemplateResponse("sales_form.html", {"request": request})
            if (TEMPLATES_DIR / "sales_form.html").exists()
            else HTMLResponse("<h1>New Invoice</h1><p>Form template not yet built.</p>")
        )

    @app.get("/pur/new", response_class=HTMLResponse)
    def pur_new_page(request: Request):
        return (
            templates.TemplateResponse("purchases_form.html", {"request": request})
            if (TEMPLATES_DIR / "purchases_form.html").exists()
            else HTMLResponse("<h1>New Voucher</h1><p>Form template not yet built.</p>")
        )

    @app.get("/bnk/new", response_class=HTMLResponse)
    def bnk_new_page(request: Request):
        return (
            templates.TemplateResponse("banking_form.html", {"request": request})
            if (TEMPLATES_DIR / "banking_form.html").exists()
            else HTMLResponse(
                "<h1>New Transaction</h1><p>Form template not yet built.</p>"
            )
        )

    @app.get("/gl/new", response_class=HTMLResponse)
    def gl_new_page(request: Request):
        return (
            templates.TemplateResponse("gl_form.html", {"request": request})
            if (TEMPLATES_DIR / "gl_form.html").exists()
            else HTMLResponse(
                "<h1>New GL Voucher</h1><p>Form template not yet built.</p>"
            )
        )


# ============================================================================
# API routers (staging + promote + audit + recon)
# ============================================================================


def _mount_api_routers(app: FastAPI, templates: Jinja2Templates) -> None:
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
    # IHE-ERP v2.5.0: Event Lifecycle Operations
    try:
        app.include_router(event_ops_router)
        logger.info("Event Ops router mounted at /api/v1/event-ops")
    except Exception as exc:
        logger.warning("Event Ops router not mounted: %s", exc)
    # IHE-ERP v3.0: Event Operations Phase 5 (execution queue, checkpoints, etc.)
    try:
        app.include_router(event_ops_phase5_router)
        logger.info("Event Ops Phase 5 router mounted at /event-ops")
    except Exception as exc:
        logger.warning("Event Ops Phase 5 router not mounted: %s", exc)
    # Document Management System
    try:
        from app.organs.incentivehouse_organ.routers.documents import (
            router as doc_router,
        )

        app.include_router(doc_router)
        logger.info("Document system router mounted at /api/v1/documents")
    except Exception as exc:
        logger.warning("Document system router not mounted: %s", exc)
    # IHE-ERP v2.3: Intelligence layer (audit, health, gap, neural, OR, SCM)
    try:
        from app.organs.incentivehouse_organ.intelligence.router import (
            router as intelligence_router,
        )

        app.include_router(intelligence_router)
        logger.info("Intelligence layer router mounted at /api/v1/ih-intelligence")
    except Exception as exc:
        logger.warning("Intelligence layer router not mounted: %s", exc)
    # IHE-ERP v2.3.2: Dashboard data API (real SQL queries + date filters)
    try:
        from app.organs.incentivehouse_organ.dashboard import router as dashboard_router

        app.include_router(dashboard_router)
        logger.info("Dashboard router mounted at /api/dashboard")
    except Exception as exc:
        logger.warning("Dashboard router not mounted: %s", exc)
    # P0-A1: RBAC (mounts under /rbac)
    try:
        from app.organs.incentivehouse_organ.rbac import router as rbac_router

        app.include_router(rbac_router)
        logger.info("RBAC router mounted at /rbac")
    except Exception as exc:
        logger.warning("RBAC router not mounted: %s", exc)
    # P0-A2: Audit Service (mounts under /audit)
    try:
        app.include_router(audit_router)
        logger.info("Audit service router mounted at /audit")
    except Exception as exc:
        logger.warning("Audit service router not mounted: %s", exc)
    # P0-A3: Backup Service (mounts under /backup)
    try:
        app.include_router(backup_router)
        logger.info("Backup service router mounted at /backup")
    except Exception as exc:
        logger.warning("Backup service router not mounted: %s", exc)
    # P1-B3: Presentation Engine (mounts under /presentations)
    try:
        app.include_router(presentation_router)
        logger.info("Presentation engine router mounted at /presentations")
    except Exception as exc:
        logger.warning("Presentation engine router not mounted: %s", exc)
    # P1-B4: Document Management System (mounts under /documents)
    try:
        app.include_router(dms_router)
        logger.info("DMS router mounted at /documents")
    except Exception as exc:
        logger.warning("DMS router not mounted: %s", exc)
    # P2-C2: Event Bridge (mounts under /event-bridge)
    try:
        app.include_router(event_bridge_router)
        logger.info("Event bridge router mounted at /event-bridge")
    except Exception as exc:
        logger.warning("Event bridge router not mounted: %s", exc)
    # P3-D2: SCM-BIO Bridge (mounts under /scm-bridge)
    try:
        app.include_router(scm_bridge_router)
        logger.info("SCM-BIO bridge router mounted at /scm-bridge")
    except Exception as exc:
        logger.warning("SCM-BIO bridge router not mounted: %s", exc)
    # SCM Cost Engine (mounts under /scm-bridge — cost-engine/* routes)
    try:
        app.include_router(scm_cost_engine_router)
        logger.info("SCM cost engine router mounted at /scm-bridge/cost-engine/*")
    except Exception as exc:
        logger.warning("SCM cost engine router not mounted: %s", exc)

    # Financial Reports (Trial Balance, P&L, Balance Sheet, Cash Flow)
    try:
        app.include_router(financial_reports_router)
        logger.info("Financial reports router mounted at /api/v1/financial-reports")
    except Exception as exc:
        logger.warning("Financial reports router not mounted: %s", exc)

    # E-Invoice XML Generator
    try:
        app.include_router(e_invoice_router)
        logger.info("E-Invoice router mounted at /api/v1/einvoice")
    except Exception as exc:
        logger.warning("E-Invoice router not mounted: %s", exc)

    # EGP currency formatter for Jinja2 templates
    def _format_egp(value):
        try:
            return "EGP " + ("{:,.2f}".format(float(value or 0)))
        except (TypeError, ValueError):
            return "EGP 0.00"

    templates.env.filters["format_egp"] = _format_egp
    # Mount the existing sub-application under /api/v1/incentivehouse
    # (the sub-app defines event_form, etc. as separate routes)
    app.mount("/api/v1/incentivehouse", incentivehouse_app)


# ============================================================================
# Health + error handlers
# ============================================================================


def _register_health(app: FastAPI) -> None:

    @app.get("/health")
    @app.get("/api/health")
    def health_check():
        """Health check at both /health and /api/health (IHE-ERP v2.3 spec)."""
        db_status = "unknown"
        pnr_count = None
        try:
            eng = get_sync_engine()
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
            # Best-effort PNR count (graceful when table missing)
            try:
                pnr_count = conn.execute(
                    text("SELECT COUNT(*) FROM pnr_master")
                ).scalar()
            except Exception:
                try:
                    pnr_count = conn.execute(
                        text("SELECT COUNT(*) FROM events")
                    ).scalar()
                except Exception:
                    pnr_count = None
        except Exception as exc:
            logger.warning("Health check DB failure: %s", exc)
            db_status = "error"
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "version": "2.3.0",
            "database": db_status,
            "pnr_count": pnr_count,
            "modules": ["Bnk", "Sal", "Pur", "Evn", "Env"],
            "staging_tables": list(STAGING_TABLE_NAMES.keys()),
            "production_tables": list(PRODUCTION_TABLE_NAMES.keys()),
        }

    @app.get("/api/ai/assist", include_in_schema=False)
    @app.post("/api/ai/assist", include_in_schema=False)
    async def ai_assist(request: Request):
        """
        Lightweight AI assist endpoint used by the floating AI widget in
        base.html.  Accepts either GET (returns service status) or POST
        with JSON body {message, page_context, current_form_data}.

        For v2.3 the endpoint is a stateless rule-based responder that
        looks at the page context and returns a contextual hint.  Swap
        the body of ``_ai_reply()`` for an LLM call in v2.4.
        """
        if request.method == "GET":
            return {
                "status": "ok",
                "service": "ai-assist",
                "version": "2.3.0",
                "hint": "POST {message, page_context, current_form_data} to get a reply.",
            }
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        message = (payload.get("message") or "").strip()
        page = payload.get("page_context") or "unknown"
        reply = _ai_reply(message, page)
        return {
            "status": "ok",
            "reply": reply,
            "page_context": page,
            "echoed": message,
        }


def _ai_reply(message: str, page: str) -> str:
    """AI reply — uses local intent engine, optionally LLM via env var."""
    from app.organs.incentivehouse_organ.intelligence.ai_assist import (
        ai_reply as smart_reply,
    )

    return smart_reply(message, page)


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
            status_code=500,
            content={"detail": "Internal server error"},
        )


# ============================================================================
# Module-level app for ``uvicorn app.organs.incentivehouse_organ.main:app``
# ============================================================================

app = create_app()


# ============================================================================
# IHE-ERP: Wire all 8 empty modules (GRN, Cost, Event Budget, Budget, BSC, Ops, BI, Approval)
# ============================================================================
try:
    from fastapi.templating import Jinja2Templates as _Jinja2Templates
    _wire_templates = _Jinja2Templates(directory=str(TEMPLATES_DIR))
    from app.organs.incentivehouse_organ.wire_empty_modules import wire as _wire_empties
    _wire_empties(app, _wire_templates)
    logger.info("All 8 empty-modules wiring complete")
except Exception as _wire_exc:
    logger.warning("Empty-modules wire-up failed: %s", _wire_exc)


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
                    out[mod] = (
                        conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                        or 0
                    )
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
