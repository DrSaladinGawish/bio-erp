"""
Contract Lifecycle Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/clm in Bio-ERP main.py
"""

from fastapi import FastAPI
from .contract_lifecycle_router import router as contract_lifecycle_router


def create_contract_lifecycle_app() -> FastAPI:
    """Factory function to create the Contract Lifecycle stub sub-application."""
    app = FastAPI(
        title="Contract Lifecycle Module (Stub)",
        description="ERP contract_lifecycle module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(contract_lifecycle_router)

    @app.get("/")
    async def root():
        return {
            "module": "contract_lifecycle",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
