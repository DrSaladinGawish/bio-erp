"""
Hs Code Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/hsc in Bio-ERP main.py
"""

from fastapi import FastAPI
from .hs_code_router import router as hs_code_router


def create_hs_code_app() -> FastAPI:
    """Factory function to create the Hs Code stub sub-application."""
    app = FastAPI(
        title="Hs Code Module (Stub)",
        description="ERP hs_code module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(hs_code_router)

    @app.get("/")
    async def root():
        return {
            "module": "hs_code",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
