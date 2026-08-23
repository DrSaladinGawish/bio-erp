"""
Or Erp Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/ore in Bio-ERP main.py
"""

from fastapi import FastAPI
from .or_erp_router import router as or_erp_router


def create_or_erp_app() -> FastAPI:
    """Factory function to create the Or Erp stub sub-application."""
    app = FastAPI(
        title="Or Erp Module (Stub)",
        description="ERP or_erp module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(or_erp_router)

    @app.get("/")
    async def root():
        return {
            "module": "or_erp",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
