"""
Carbon Accounting Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/crb in Bio-ERP main.py
"""

from fastapi import FastAPI
from .carbon_accounting_router import router as carbon_accounting_router


def create_carbon_accounting_app() -> FastAPI:
    """Factory function to create the Carbon Accounting stub sub-application."""
    app = FastAPI(
        title="Carbon Accounting Module (Stub)",
        description="ERP carbon_accounting module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(carbon_accounting_router)

    @app.get("/")
    async def root():
        return {
            "module": "carbon_accounting",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
