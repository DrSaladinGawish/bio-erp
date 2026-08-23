from __future__ import annotations

import logging
import os
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
from app.middleware.csrf import CSRFMiddleware

from app.config import settings
from app.database import get_async_engine, get_db
import app.models.manufacturing  # noqa: F401  — register tables with Base
import app.ai_ingest.models  # noqa: F401  — register AI ingestion tables with Base
import app.models.neural.prediction  # noqa: F401  — register neural tables with Base
import app.models.vibe_coding  # noqa: F401  — register VCA tables with Base
import app.organs.multi_entity_organ.models  # noqa: F401  — register multi-entity tables
import app.organs.ebuild_organ.models  # noqa: F401  — register ebuild tables with Base

# MSSQL ERP Module Sub-Applications (auto-generated, 40 modules: 17 full + 23 stub)
from app.ap_ar_module.ap_ar_sub_app import create_ap_ar_app
from app.financial_module.financial_sub_app import create_financial_app
from app.fixed_assets_module.fixed_assets_sub_app import create_fixed_assets_app
from app.foundation_module.foundation_sub_app import create_foundation_app
from app.hr_payroll_module.hr_payroll_sub_app import create_hr_payroll_app
from app.integration_module.integration_sub_app import create_integration_app
from app.inventory_module.inventory_sub_app import create_inventory_app
from app.items_module.items_sub_app import create_items_app
from app.manufacturing_module.manufacturing_sub_app import create_manufacturing_app
from app.new_p0_module.new_p0_sub_app import create_new_p0_app
from app.new_p1_module.new_p1_sub_app import create_new_p1_app
from app.partners_module.partners_sub_app import create_partners_app
from app.procurement_module.procurement_sub_app import create_procurement_app
from app.project_mgmt_module.project_mgmt_sub_app import create_project_mgmt_app
from app.registry_module.registry_sub_app import create_registry_app
from app.sales_module.sales_sub_app import create_sales_app
from app.banking_treasury_module.banking_treasury_sub_app import create_banking_treasury_app
# Stub modules (23 — 0 tables, placeholder endpoints)
from app.or_erp_module.or_erp_sub_app import create_or_erp_app
from app.scm_module.scm_sub_app import create_scm_app
from app.multi_entity_module.multi_entity_sub_app import create_multi_entity_app
from app.hs_code_module.hs_code_sub_app import create_hs_code_app
from app.ai_cortex_module.ai_cortex_sub_app import create_ai_cortex_app
from app.esg_sustainability_module.esg_sustainability_sub_app import create_esg_sustainability_app
from app.carbon_accounting_module.carbon_accounting_sub_app import create_carbon_accounting_app
from app.compliance_agent_module.compliance_agent_sub_app import create_compliance_agent_app
from app.cybersecurity_core_module.cybersecurity_core_sub_app import create_cybersecurity_core_app
from app.mobile_platform_module.mobile_platform_sub_app import create_mobile_platform_app
from app.customer_portal_module.customer_portal_sub_app import create_customer_portal_app
from app.vendor_portal_module.vendor_portal_sub_app import create_vendor_portal_app
from app.document_management_module.document_management_sub_app import create_document_management_app
from app.workflow_engine_module.workflow_engine_sub_app import create_workflow_engine_app
from app.master_data_mgmt_module.master_data_mgmt_sub_app import create_master_data_mgmt_app
from app.demand_planning_module.demand_planning_sub_app import create_demand_planning_app
from app.warehouse_mgmt_module.warehouse_mgmt_sub_app import create_warehouse_mgmt_app
from app.recruitment_talent_module.recruitment_talent_sub_app import create_recruitment_talent_app
from app.performance_mgmt_module.performance_mgmt_sub_app import create_performance_mgmt_app
from app.subscription_billing_module.subscription_billing_sub_app import create_subscription_billing_app
from app.revenue_recognition_module.revenue_recognition_sub_app import create_revenue_recognition_app
from app.contract_lifecycle_module.contract_lifecycle_sub_app import create_contract_lifecycle_app
from app.edi_connector_module.edi_connector_sub_app import create_edi_connector_app

# OR-ERP Sub-Application
from app.organs.or_organ.sub_app import or_app

# SCM Costing & Performance Sub-Application
from app.organs.scm_organ.sub_app import scm_app

# Multi-Entity Consolidation Sub-Application
from app.organs.multi_entity_organ.sub_app import me_app

# FAR-GL General Ledger Sub-Application
from app.organs.far_gl_organ.sub_app import far_gl_app

# FAR-AR Accounts Receivable Sub-Application
from app.organs.far_ar_organ.sub_app import ar_app

# FAR-AP Accounts Payable Sub-Application
from app.organs.far_ap_organ.sub_app import ap_app

# FAR-FA Fixed Assets Sub-Application
from app.organs.far_fa_organ.sub_app import far_fa_app

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
            try:
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
            except Exception as seed_e:
                await db.rollback()
                logger.warning("Branch seed skipped: %s", seed_e)

            try:
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
            except Exception as user_e:
                await db.rollback()
                logger.warning("Admin user seed skipped: %s", user_e)

            try:
                from app.seed import seed_all
                await seed_all(db)
                logger.info("Roles and permissions seeded")
            except Exception as seed_e:
                await db.rollback()
                logger.warning("Role seeding skipped: %s", seed_e)
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
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
_allowed_hosts = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,.localhost").split(",")
    if h.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
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

# AI Agent Bridge (EBA — n8n integration)
from app.routers.ai_agent import router as ai_agent_router
from app.routers.ai_agent import launcher_router

app.include_router(ai_agent_router)
app.include_router(launcher_router)

# Library Compliance Checker (EBA Module 5)
from app.routers.library_compliance import router as library_compliance_router

app.include_router(library_compliance_router, prefix="/api/v1/ai-agent")

# Vibe Coding Agent (VCA — EBA Module 6)
from app.routers.vibe_coding import router as vibe_coding_router

app.include_router(vibe_coding_router, prefix="/api/v1/ai-agent")

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

# Multi-Entity Consolidation Module (mounted at /api/v1/me)
app.mount("/api/v1/me", me_app)

# FAR-GL General Ledger Module (mounted at /api/v1/far-gl)
app.mount("/api/v1/far-gl", far_gl_app)

# FAR-AR Accounts Receivable Module (mounted at /api/v1/ar)
app.mount("/api/v1/ar", ar_app)

# FAR-AP Accounts Payable Module (mounted at /api/v1/ap)
app.mount("/api/v1/ap", ap_app)

# FAR-FA Fixed Assets Module (mounted at /api/v1/fa)
app.mount("/api/v1/fa", far_fa_app)

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

# Ebuild System Organ — Universal ERP Meta-Builder
from app.organs.ebuild_organ.sub_app import ebuild_app
app.mount("/api/v1/ebuild", ebuild_app)

# =============================================================================
# STRATEGIC MANAGEMENT CATEGORY ORGANS (20 categories)
# =============================================================================
# 1. Environmental Scanning & Analysis (10 techniques)
from app.organs.env_scanning_organ.sub_app import env_scanning_app
app.mount("/api/v1/env-scanning", env_scanning_app)

# 2. Strategy Formulation (12 techniques)
from app.organs.strategy_formulation_organ.sub_app import strategy_formulation_app
app.mount("/api/v1/strategy-formulation", strategy_formulation_app)

# 3. Resource & Capability Analysis (8 techniques)
from app.organs.resource_capability_organ.sub_app import resource_capability_app
app.mount("/api/v1/resource-capability", resource_capability_app)

# 4. Portfolio & Growth Strategies (9 techniques)
from app.organs.portfolio_growth_organ.sub_app import portfolio_growth_app
app.mount("/api/v1/portfolio-growth", portfolio_growth_app)

# 5. Cost Management (24 techniques)
from app.organs.cost_management_organ.sub_app import cost_management_app
app.mount("/api/v1/cost-management", cost_management_app)

# 6. Strategic Performance Measurement (15 techniques)
from app.organs.strategic_performance_organ.sub_app import strategic_performance_app
app.mount("/api/v1/strategic-performance", strategic_performance_app)

# 7. Financial & Value-Based Strategy (7 techniques)
from app.organs.financial_value_organ.sub_app import financial_value_app
app.mount("/api/v1/financial-value", financial_value_app)

# 8. Strategy Implementation (10 techniques)
from app.organs.strategy_implementation_organ.sub_app import strategy_implementation_app
app.mount("/api/v1/strategy-implementation", strategy_implementation_app)

# 9. Strategy Monitoring & Control (6 techniques)
from app.organs.strategy_monitoring_organ.sub_app import strategy_monitoring_app
app.mount("/api/v1/strategy-monitoring", strategy_monitoring_app)

# 10. Corporate Strategy (5 techniques)
from app.organs.corporate_strategy_organ.sub_app import corporate_strategy_app
app.mount("/api/v1/corporate-strategy", corporate_strategy_app)

# 11. Business Strategy (13 techniques)
from app.organs.business_strategy_organ.sub_app import business_strategy_app
app.mount("/api/v1/business-strategy", business_strategy_app)

# 12. Functional-Level Strategy (8 techniques)
from app.organs.functional_strategy_organ.sub_app import functional_strategy_app
app.mount("/api/v1/functional-strategy", functional_strategy_app)

# 13. Strategic Thinking Tools (10 techniques)
from app.organs.strategic_thinking_organ.sub_app import strategic_thinking_app
app.mount("/api/v1/strategic-thinking", strategic_thinking_app)

# 14. Industry & Market Analysis (8 techniques)
from app.organs.industry_market_organ.sub_app import industry_market_app
app.mount("/api/v1/industry-market", industry_market_app)

# 15. Global & International Strategy (7 techniques)
from app.organs.global_international_organ.sub_app import global_international_app
app.mount("/api/v1/global-international", global_international_app)

# 16. Digital & Innovation Strategy (9 techniques)
from app.organs.digital_innovation_organ.sub_app import digital_innovation_app
app.mount("/api/v1/digital-innovation", digital_innovation_app)

# 17. Strategic Decision-Making (10 techniques)
from app.organs.strategic_decision_organ.sub_app import strategic_decision_app
app.mount("/api/v1/strategic-decision", strategic_decision_app)

# 18. Risk & Uncertainty Management (6 techniques)
from app.organs.risk_uncertainty_organ.sub_app import risk_uncertainty_app
app.mount("/api/v1/risk-uncertainty", risk_uncertainty_app)

# 19. Knowledge & Learning Strategy (4 techniques)
from app.organs.knowledge_learning_organ.sub_app import knowledge_learning_app
app.mount("/api/v1/knowledge-learning", knowledge_learning_app)

# 20. Ethics & Social Responsibility (6 techniques)
from app.organs.ethics_social_organ.sub_app import ethics_social_app
app.mount("/api/v1/ethics-social", ethics_social_app)

# MSSQL ERP Module Mounts (40 modules: 17 full + 23 stub, 198 tables)
app.mount("/api/v1/apa", create_ap_ar_app())
app.mount("/api/v1/fin", create_financial_app())
app.mount("/api/v1/fxa", create_fixed_assets_app())
app.mount("/api/v1/fou", create_foundation_app())
app.mount("/api/v1/hrp", create_hr_payroll_app())
app.mount("/api/v1/int", create_integration_app())
app.mount("/api/v1/inv", create_inventory_app())
app.mount("/api/v1/ite", create_items_app())
app.mount("/api/v1/mfg", create_manufacturing_app())
app.mount("/api/v1/p0", create_new_p0_app())
app.mount("/api/v1/p1", create_new_p1_app())
app.mount("/api/v1/par", create_partners_app())
app.mount("/api/v1/prc", create_procurement_app())
app.mount("/api/v1/prj", create_project_mgmt_app())
app.mount("/api/v1/reg", create_registry_app())
app.mount("/api/v1/sal", create_sales_app())
app.mount("/api/v1/bnk", create_banking_treasury_app())
# Stub module mounts (23)
app.mount("/api/v1/ore", create_or_erp_app())
app.mount("/api/v1/scm", create_scm_app())
app.mount("/api/v1/mte", create_multi_entity_app())
app.mount("/api/v1/hsc", create_hs_code_app())
app.mount("/api/v1/aic", create_ai_cortex_app())
app.mount("/api/v1/esg", create_esg_sustainability_app())
app.mount("/api/v1/crb", create_carbon_accounting_app())
app.mount("/api/v1/cpl", create_compliance_agent_app())
app.mount("/api/v1/sec", create_cybersecurity_core_app())
app.mount("/api/v1/mob", create_mobile_platform_app())
app.mount("/api/v1/cpt", create_customer_portal_app())
app.mount("/api/v1/vpt", create_vendor_portal_app())
app.mount("/api/v1/dms", create_document_management_app())
app.mount("/api/v1/wf", create_workflow_engine_app())
app.mount("/api/v1/mdm", create_master_data_mgmt_app())
app.mount("/api/v1/dp", create_demand_planning_app())
app.mount("/api/v1/wms", create_warehouse_mgmt_app())
app.mount("/api/v1/rec", create_recruitment_talent_app())
app.mount("/api/v1/perf", create_performance_mgmt_app())
app.mount("/api/v1/sub", create_subscription_billing_app())
app.mount("/api/v1/rrc", create_revenue_recognition_app())
app.mount("/api/v1/clm", create_contract_lifecycle_app())
app.mount("/api/v1/edi", create_edi_connector_app())

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
        headers=getattr(exc, "headers", None),
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


@app.get("/eba")
async def eba_dashboard():
    """EBA Agent Modules Dashboard"""
    return FileResponse(str(BASE_DIR / "static" / "agent_modules_dashboard.html"))

@app.get("/vca")
async def vibe_coding_ui():
    """Vibe Coding Agent UI"""
    return FileResponse(str(BASE_DIR / "static" / "vibe_coding_agent_ui.html"))

@app.get("/launcher")
async def ai_agent_launcher():
    """AI Agent Cortex Launcher"""
    return FileResponse(str(BASE_DIR / "static" / "ai_agent_launcher.html"))

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
