"""
Compliance Agent Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/cpl in Bio-ERP main.py
"""

from fastapi import FastAPI
from .compliance_agent_router import router as compliance_agent_router


def create_compliance_agent_app() -> FastAPI:
    """Factory function to create the Compliance Agent stub sub-application."""
    app = FastAPI(
        title="Compliance Agent Module (Stub)",
        description="ERP compliance_agent module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(compliance_agent_router)

    @app.get("/")
    async def root():
        return {
            "module": "compliance_agent",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
