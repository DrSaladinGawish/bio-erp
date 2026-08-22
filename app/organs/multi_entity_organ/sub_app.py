"""
Multi-Entity Consolidation Sub-Application for BIO-ERP v5
==========================================================
Mount at: app.mount("/api/v1/me", me_app) in BIO-ERP's main.py
"""

from fastapi import FastAPI

from app.organs.multi_entity_organ.router import router as me_router

me_app = FastAPI(
    title="Multi-Entity Consolidation",
    description="Group consolidation, intercompany elimination, currency translation (IFRS 10, IAS 27, IAS 28, IFRS 3)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

me_app.include_router(me_router)

@me_app.get("/")
def root():
    return {
        "service": "Multi-Entity Consolidation",
        "version": "1.0.0",
        "standards": ["IFRS 10", "IAS 27", "IAS 28", "IFRS 3", "IAS 21"],
        "docs": "/docs",
        "health": "/health",
    }


@me_app.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "multi-entity-consolidation",
        "version": "1.0.0",
    }
