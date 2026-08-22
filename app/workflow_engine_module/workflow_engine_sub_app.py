"""
Workflow Engine Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/wf in Bio-ERP main.py
"""

from fastapi import FastAPI
from .workflow_engine_router import router as workflow_engine_router


def create_workflow_engine_app() -> FastAPI:
    """Factory function to create the Workflow Engine stub sub-application."""
    app = FastAPI(
        title="Workflow Engine Module (Stub)",
        description="ERP workflow_engine module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(workflow_engine_router)

    @app.get("/")
    async def root():
        return {
            "module": "workflow_engine",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
