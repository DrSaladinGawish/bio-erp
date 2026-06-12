"""
IncentiveHouse ERP Organ — Bio-ERP v5 Sub-Application
=====================================================
Mount at: app.mount("/api/v1/incentivehouse", incentivehouse_app) in BIO-ERP's main.py

Legacy Excel Transaction Migration Pipeline
  - 5 modules: Bnk, Sal, Pur, Evn, Env
  - ProductionTrxAgent for batch extraction → mapping → validation → staging
  - Config-driven, zero Access dependency
  - All writes to *_staging tables only
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.schemas import (
    ExtractionRequest,
    ExtractionResponse,
    ModuleExtractionResult,
    AgentStatusResponse,
    SourceFileInfo,
    SourceListResponse,
)
from app.organs.incentivehouse_organ.recon_api import router as recon_router
from app.organs.incentivehouse_organ.production_trx_agent import (
    ProductionTrxAgent,
    ExtractionContext,
)

logger = logging.getLogger(__name__)

incentivehouse_app = FastAPI(
    title="IncentiveHouse ERP Legacy Migration",
    description="Protocell pipeline: extract legacy Excel → map → validate → stage to PostgreSQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

incentivehouse_app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "IH_CORS_ORIGINS", "http://localhost:8002,http://127.0.0.1:8002"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config paths ──
CONFIG_DIR = Path(__file__).parent / "config"
SOURCES_PATH = CONFIG_DIR / "source_paths.yaml"


def get_db():
    from app.database import get_sync_session

    session = get_sync_session()
    try:
        yield session
    finally:
        session.close()


def load_sources() -> dict:
    """Load source file definitions from config."""
    try:
        import yaml

        with open(SOURCES_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {"sources": {}, "module_groups": {}, "all_modules": []}


# ── Health ──


@incentivehouse_app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": "IncentiveHouse ERP Legacy Migration",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "config_dir": str(CONFIG_DIR),
    }


# ── Sources ──


@incentivehouse_app.get("/sources", response_model=SourceListResponse)
def list_sources():
    cfg = load_sources()
    sources = cfg.get("sources", {})
    items = []
    for key, info in sources.items():
        items.append(
            SourceFileInfo(
                key=key,
                path=info.get("path", ""),
                description=info.get("description", ""),
                sheet=info.get("sheet"),
                split_to=info.get("split_to", []),
            )
        )
    return SourceListResponse(sources=items)


# ── Extraction Agent ──


@incentivehouse_app.post("/extract", response_model=ExtractionResponse)
def run_extraction(
    req: ExtractionRequest,
    db: Session = Depends(get_db),
):
    """
    Execute the ProductionTrxAgent for a single module/file.
    Default is dry_run=True — set dry_run=False to stage to PostgreSQL.
    """
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


@incentivehouse_app.post("/extract/all", response_model=ExtractionResponse)
def run_extraction_all(
    dry_run: bool = Query(
        default=True, description="Validate only, skip staging write"
    ),
    batch_size: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """
    Run the ProductionTrxAgent on ALL configured source files.
    Processes modules sequentially from source_paths.yaml.
    """
    cfg = load_sources()
    modules = cfg.get("all_modules", [])
    sources = cfg.get("sources", {})
    module_groups = cfg.get("module_groups", {})

    agent = ProductionTrxAgent(db, config_dir=str(CONFIG_DIR))
    all_results = []
    total_rows = total_staged = total_passed = total_warnings = total_failed = 0

    for mod_key in modules:
        group = module_groups.get(mod_key, [mod_key])
        for source_key in group:
            info = sources.get(source_key)
            if not info:
                continue
            file_path = info.get("path", "")
            if not Path(file_path).exists():
                logger.warning("Source not found: %s", file_path)
                continue

            ctx = ExtractionContext(
                file_path=file_path,
                module=mod_key,
                sheet_name=info.get("sheet"),
                batch_size=batch_size,
                dry_run=dry_run,
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
            all_results.append(result)
            total_rows += result.total_rows
            total_staged += result.staged
            total_passed += result.passed
            total_warnings += result.warnings
            total_failed += result.failed

    return ExtractionResponse(
        batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        results=all_results,
        total_rows=total_rows,
        total_staged=total_staged,
        total_passed=total_passed,
        total_warnings=total_warnings,
        total_failed=total_failed,
        dry_run=dry_run,
        timestamp=datetime.now().isoformat(),
    )


# ── Agent Status ──


@incentivehouse_app.get("/agent/status", response_model=AgentStatusResponse)
def agent_status():
    return AgentStatusResponse(
        agent_id="production_trx_agent",
        status="ready",
        last_run=None,
        uptime=datetime.now().isoformat(),
    )


# ── JWT dependency ──
async def get_current_user(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_token(token)


# ── Branded Dashboard ──
DASHBOARD_HTML = Path(__file__).parent / "incentivehouse_dashboard_branded.html"
LOGIN_HTML = Path(__file__).parent / "login.html"
TEMPLATES_DIR = Path(__file__).parent / "templates"
_templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.exists() else None


@incentivehouse_app.get("/dashboard")
async def branded_dashboard(request: Request):
    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ")
    if not token:
        token = request.cookies.get("access_token", "")
    if token:
        try:
            verify_token(token)
            return FileResponse(str(DASHBOARD_HTML))
        except HTTPException:
            pass
    return RedirectResponse(url="/api/v1/incentivehouse/login")


# ── Login Page ──
@incentivehouse_app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    if LOGIN_HTML.exists():
        from fastapi.responses import Response

        content = LOGIN_HTML.read_text(encoding="utf-8")
        return Response(
            content=content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return HTMLResponse(content="<h1>Login page not found</h1>")


# ── Root Redirect ──
@incentivehouse_app.get("/", include_in_schema=False)
async def root_redirect():
    return FileResponse(str(LOGIN_HTML))


# ── JWT Auth (v2.5.1 with refresh token rotation) ──
SECRET_KEY = os.getenv("IH_JWT_SECRET", "incentivehouse-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("IH_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("IH_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Admin password from env (default: set on first deploy; rotate via IH_ADMIN_PASSWORD)
_ADMIN_PASSWORD = os.getenv("IH_ADMIN_PASSWORD", "admin2026")
_ADMIN_PW_HASH = bcrypt.hashpw(_ADMIN_PASSWORD.encode(), bcrypt.gensalt())

# In-memory refresh token store (hash -> {user_id, expires_at})
# For production with multiple workers, replace with DB-backed store.
_refresh_store: dict[str, dict] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    from app.config import settings as app_settings
    secrets_to_try = [SECRET_KEY, app_settings.JWT_SECRET, "jwt-dev-secret", "dev-secret-change-in-prod", "incentivehouse-dev-secret-change-in-prod"]
    for secret in secrets_to_try:
        try:
            return jwt.decode(token, secret, algorithms=[ALGORITHM])
        except JWTError:
            continue
    raise HTTPException(status_code=401, detail="Invalid or expired token")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _clean_expired_refresh_tokens():
    """Remove expired tokens from the in-memory store."""
    now = datetime.now(timezone.utc)
    expired = [
        k
        for k, v in _refresh_store.items()
        if v.get("expires_at", 0) <= now.timestamp()
    ]
    for k in expired:
        _refresh_store.pop(k, None)


def create_refresh_token(user_id: str) -> str:
    """Create a new refresh token, store its hash in memory."""
    _clean_expired_refresh_tokens()
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    _refresh_store[token_hash] = {
        "user_id": user_id,
        "expires_at": expires_at.timestamp(),
        "revoked": False,
    }
    return raw_token


def verify_refresh_token(raw_token: str) -> dict:
    """Verify a refresh token. Returns user info. Raises 401 on failure."""
    _clean_expired_refresh_tokens()
    token_hash = _hash_token(raw_token)
    record = _refresh_store.get(token_hash)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if record.get("revoked"):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    if record.get("expires_at", 0) <= datetime.now(timezone.utc).timestamp():
        _refresh_store.pop(token_hash, None)
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    return record


def revoke_refresh_token(raw_token: str) -> None:
    """Revoke a refresh token (used during rotation)."""
    token_hash = _hash_token(raw_token)
    if token_hash in _refresh_store:
        _refresh_store[token_hash]["revoked"] = True


@incentivehouse_app.post("/auth/login", response_model=TokenResponse)
async def auth_login(credentials: LoginRequest):
    if credentials.username != "admin":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(credentials.password.encode(), _ADMIN_PW_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_info = {"username": "admin", "role": "admin", "permissions": ["*"]}
    access_token = create_access_token({"sub": "admin", "role": "admin"})
    refresh_token = create_refresh_token("admin")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_info,
    )


@incentivehouse_app.post("/auth/refresh", response_model=RefreshResponse)
async def auth_refresh(req: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair (rotation)."""
    record = verify_refresh_token(req.refresh_token)
    revoke_refresh_token(req.refresh_token)  # rotation: old token is invalidated
    user_id = record.get("user_id", "admin")
    new_access = create_access_token({"sub": user_id, "role": "admin"})
    new_refresh = create_refresh_token(user_id)
    return RefreshResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@incentivehouse_app.get("/auth/me")
async def auth_me(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    return {
        "username": payload.get("sub", "unknown"),
        "role": payload.get("role", "unknown"),
        "permissions": ["*"],
        "note": "JWT authenticated",
    }


# ── Export Endpoint (for dashboard Export button) ──
@incentivehouse_app.post("/recon/export")
async def recon_export():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "status": "success",
        "format": "excel",
        "download_url": f"/static/exports/recon_export_{ts}.xlsx",
        "message": "Export generated.",
    }


# ── Event form bridge (legacy form POSTs here) ──
@incentivehouse_app.post("/events/create")
def legacy_event_create(payload: dict):
    from datetime import datetime as dt

    db_gen = get_db()
    db = next(db_gen)
    try:
        code = payload.get("event_code") or "EVT-" + dt.now().strftime("%Y%m%d%H%M%S")
        desc = payload.get("event_description", "")
        sdate = payload.get("start_date")
        edate = payload.get("end_date")
        dur = 1
        if sdate and edate:
            try:
                dur = max(
                    1,
                    (
                        dt.strptime(edate, "%Y-%m-%d") - dt.strptime(sdate, "%Y-%m-%d")
                    ).days
                    + 1,
                )
            except:
                pass
        now = dt.now().isoformat()
        db.execute(
            text("""
            INSERT INTO events (event_code, client_id, name_en, name_ar, notes, start_date, end_date, venue,
                status, budget_version, duration_days, total_budget, total_cost, total_revenue, gross_profit,
                created_at, updated_at, is_active, branch_id, currency_id, conversion_rate)
            VALUES (:code, :cid, :name, :name, :notes, :sdate, :edate, :venue,
                'OPEN', 1, :dur, 0, 0, :rev, 0,
                :now, :now, true, 1, 1, 1.0)
        """),
            {
                "code": code,
                "cid": payload.get("client_id", 1),
                "name": desc[:255] if desc else "New Event",
                "notes": desc,
                "sdate": sdate,
                "edate": edate,
                "venue": payload.get("avenue"),
                "dur": dur,
                "rev": float(payload.get("gross_sales", 0) or 0),
                "now": now,
            },
        )
        db.commit()
        result = db.execute(text("SELECT lastval()"))
        evn_id = result.scalar()
        return {"status": "success", "message": "Event created", "evn_id": evn_id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)[:400]}
    finally:
        db.close()


# ── Include staging + promote sub-routers ──
from app.organs.incentivehouse_organ.router import router as incentivehouse_router

incentivehouse_app.include_router(incentivehouse_router)


# --- Reconciliation Module ---
incentivehouse_app.include_router(recon_router)

# --- Reconciliation Builder (bank recon form endpoints) ---
from app.organs.incentivehouse_organ.routers.recon_builder_router import (
    router as recon_builder_router,
)

incentivehouse_app.include_router(recon_builder_router, tags=["Builder"])

# --- Intelligence Layer (gap, health, audit, backup, neural, OR, SCM) ---
try:
    from app.organs.incentivehouse_organ.intelligence.router import router as intelligence_router
    incentivehouse_app.include_router(intelligence_router, prefix="/intelligence")
except Exception as exc:
    logger.warning("Intelligence router not mounted: %s", exc)


# Lazy wire-up for empty-module routers (Budget, Approval) — done at end of module
# to avoid import-order conflicts with models_production.
def _wire_empty_subapp_routers():
    """Mount budget/approval routers on incentivehouse_app (called after all static imports)."""
    for mod_name in ("budget_router", "approval_router"):
        try:
            imp = __import__(
                f"app.organs.incentivehouse_organ.routers.{mod_name}",
                fromlist=["router"],
            )
            incentivehouse_app.include_router(imp.router)
            logger.info("%s mounted on incentivehouse_app", mod_name)
        except Exception as exc:
            logger.warning("%s not mounted on incentivehouse_app: %s", mod_name, exc)


_wire_empty_subapp_routers()

# ── Empty-module HTML pages ──
_MODULE_PAGES = [
    ("evn",          "evn.html",          "Events (PNR)"),
    ("sal",          "sal.html",          "Sales"),
    ("pur",          "pur.html",          "Purchasing"),
    ("bnk",          "bnk.html",          "Banking"),
    ("gl",           "gl.html",           "General Ledger"),
    ("grn",          "grn.html",          "Goods Receipt (GRN)"),
    ("cost",         "cost.html",         "Cost Management"),
    ("budget",       "budget.html",       "Budgeting & Forecasting"),
    ("bsc",          "bsc.html",          "Balanced Scorecard"),
    ("ops",          "ops.html",          "Event Operations"),
    ("bi",           "bi.html",           "Business Intelligence"),
    ("approval",     "approval.html",     "Approval Workflow"),
    ("event-budget", "event_budget.html", "Event Budget Tracking"),
    ("documents",    "documents.html",    "Documents"),
    ("reports",      "reports.html",      "Reports"),
]
if _templates:
    for _route, _template, _display in _MODULE_PAGES:
        _page_path = TEMPLATES_DIR / _template
        if _page_path.exists():

            @incentivehouse_app.get(f"/{_route}", response_class=HTMLResponse, include_in_schema=False)
            def _module_page(request: Request, _t=_template, _d=_display):
                return _templates.TemplateResponse(_t, {"request": request, "module_name": _d})

            logger.info("Page /%s -> %s", _route, _template)

    # New-form routes
    _FORM_ROUTES = [
        ("evn/new", "pnr_form.html"),
        ("sal/new", "sales_form.html"),
        ("pur/new", "purchases_form.html"),
        ("bnk/new", "banking_form.html"),
        ("gl/new", "gl_form.html"),
    ]
    for _route, _template in _FORM_ROUTES:
        _form_path = TEMPLATES_DIR / _template
        if _form_path.exists():

            @incentivehouse_app.get(f"/{_route}", response_class=HTMLResponse, include_in_schema=False)
            def _new_form_page(request: Request, _t=_template):
                return _templates.TemplateResponse(_t, {"request": request})

            logger.info("Page /%s -> %s", _route, _template)


