"""
Esg Sustainability Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/esg in Bio-ERP main.py
"""

from fastapi import FastAPI
from .esg_sustainability_router import router as esg_sustainability_router


def create_esg_sustainability_app() -> FastAPI:
    """Factory function to create the Esg Sustainability stub sub-application."""
    app = FastAPI(
        title="Esg Sustainability Module (Stub)",
        description="ERP esg_sustainability module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(esg_sustainability_router)

    @app.get("/")
    async def root():
        return {
            "module": "esg_sustainability",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
