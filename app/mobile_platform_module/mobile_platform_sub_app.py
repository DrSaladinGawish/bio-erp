"""
Mobile Platform Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/mob in Bio-ERP main.py
"""

from fastapi import FastAPI
from .mobile_platform_router import router as mobile_platform_router


def create_mobile_platform_app() -> FastAPI:
    """Factory function to create the Mobile Platform stub sub-application."""
    app = FastAPI(
        title="Mobile Platform Module (Stub)",
        description="ERP mobile_platform module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(mobile_platform_router)

    @app.get("/")
    async def root():
        return {
            "module": "mobile_platform",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
