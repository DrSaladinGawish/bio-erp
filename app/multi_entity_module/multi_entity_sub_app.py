"""
Multi Entity Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/mte in Bio-ERP main.py
"""

from fastapi import FastAPI
from .multi_entity_router import router as multi_entity_router


def create_multi_entity_app() -> FastAPI:
    """Factory function to create the Multi Entity stub sub-application."""
    app = FastAPI(
        title="Multi Entity Module (Stub)",
        description="ERP multi_entity module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(multi_entity_router)

    @app.get("/")
    async def root():
        return {
            "module": "multi_entity",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
