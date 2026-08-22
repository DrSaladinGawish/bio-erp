"""
Warehouse Mgmt Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/wms in Bio-ERP main.py
"""

from fastapi import FastAPI
from .warehouse_mgmt_router import router as warehouse_mgmt_router


def create_warehouse_mgmt_app() -> FastAPI:
    """Factory function to create the Warehouse Mgmt stub sub-application."""
    app = FastAPI(
        title="Warehouse Mgmt Module (Stub)",
        description="ERP warehouse_mgmt module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(warehouse_mgmt_router)

    @app.get("/")
    async def root():
        return {
            "module": "warehouse_mgmt",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
