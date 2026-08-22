"""
Performance Mgmt Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/perf in Bio-ERP main.py
"""

from fastapi import FastAPI
from .performance_mgmt_router import router as performance_mgmt_router


def create_performance_mgmt_app() -> FastAPI:
    """Factory function to create the Performance Mgmt stub sub-application."""
    app = FastAPI(
        title="Performance Mgmt Module (Stub)",
        description="ERP performance_mgmt module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(performance_mgmt_router)

    @app.get("/")
    async def root():
        return {
            "module": "performance_mgmt",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
