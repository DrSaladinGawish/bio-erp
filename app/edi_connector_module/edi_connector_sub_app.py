"""
Edi Connector Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/edi in Bio-ERP main.py
"""

from fastapi import FastAPI
from .edi_connector_router import router as edi_connector_router


def create_edi_connector_app() -> FastAPI:
    """Factory function to create the Edi Connector stub sub-application."""
    app = FastAPI(
        title="Edi Connector Module (Stub)",
        description="ERP edi_connector module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(edi_connector_router)

    @app.get("/")
    async def root():
        return {
            "module": "edi_connector",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
