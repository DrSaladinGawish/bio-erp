"""
Revenue Recognition Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/rrc in Bio-ERP main.py
"""

from fastapi import FastAPI
from .revenue_recognition_router import router as revenue_recognition_router


def create_revenue_recognition_app() -> FastAPI:
    """Factory function to create the Revenue Recognition stub sub-application."""
    app = FastAPI(
        title="Revenue Recognition Module (Stub)",
        description="ERP revenue_recognition module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(revenue_recognition_router)

    @app.get("/")
    async def root():
        return {
            "module": "revenue_recognition",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
