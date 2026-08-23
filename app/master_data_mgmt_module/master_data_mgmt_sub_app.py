"""
Master Data Mgmt Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/mdm in Bio-ERP main.py
"""

from fastapi import FastAPI
from .master_data_mgmt_router import router as master_data_mgmt_router


def create_master_data_mgmt_app() -> FastAPI:
    """Factory function to create the Master Data Mgmt stub sub-application."""
    app = FastAPI(
        title="Master Data Mgmt Module (Stub)",
        description="ERP master_data_mgmt module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(master_data_mgmt_router)

    @app.get("/")
    async def root():
        return {
            "module": "master_data_mgmt",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
