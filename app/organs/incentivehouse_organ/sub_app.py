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
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

from app.organs.incentivehouse_organ.schemas import (
    ExtractionRequest, ExtractionResponse, ModuleExtractionResult,
    AgentStatusResponse, SourceFileInfo, SourceListResponse,
)
from app.organs.incentivehouse_organ.recon_api import router as recon_router
from app.organs.incentivehouse_organ.production_trx_agent import (
    ProductionTrxAgent, ExtractionContext,
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
    allow_origins=["*"],
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
        items.append(SourceFileInfo(
            key=key,
            path=info.get("path", ""),
            description=info.get("description", ""),
            sheet=info.get("sheet"),
            split_to=info.get("split_to", []),
        ))
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
    dry_run: bool = Query(default=True, description="Validate only, skip staging write"),
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


# ── Include staging + promote sub-routers ──
from app.organs.incentivehouse_organ.router import router as incentivehouse_router
incentivehouse_app.include_router(incentivehouse_router)


# --- Reconciliation Module ---
incentivehouse_app.include_router(recon_router)
