"""
Scm Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/scm in Bio-ERP main.py
"""

from fastapi import FastAPI
from .scm_router import router as scm_router


def create_scm_app() -> FastAPI:
    """Factory function to create the Scm stub sub-application."""
    app = FastAPI(
        title="Scm Module (Stub)",
        description="ERP scm module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(scm_router)

    @app.get("/")
    async def root():
        return {
            "module": "scm",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
