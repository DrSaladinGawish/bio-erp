"""
Vendor Portal Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/vpt in Bio-ERP main.py
"""

from fastapi import FastAPI
from .vendor_portal_router import router as vendor_portal_router


def create_vendor_portal_app() -> FastAPI:
    """Factory function to create the Vendor Portal stub sub-application."""
    app = FastAPI(
        title="Vendor Portal Module (Stub)",
        description="ERP vendor_portal module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(vendor_portal_router)

    @app.get("/")
    async def root():
        return {
            "module": "vendor_portal",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
