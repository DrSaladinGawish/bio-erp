"""
Cybersecurity Core Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/sec in Bio-ERP main.py
"""

from fastapi import FastAPI
from .cybersecurity_core_router import router as cybersecurity_core_router


def create_cybersecurity_core_app() -> FastAPI:
    """Factory function to create the Cybersecurity Core stub sub-application."""
    app = FastAPI(
        title="Cybersecurity Core Module (Stub)",
        description="ERP cybersecurity_core module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(cybersecurity_core_router)

    @app.get("/")
    async def root():
        return {
            "module": "cybersecurity_core",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
