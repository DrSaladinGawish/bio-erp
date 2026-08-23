"""
Customer Portal Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/cpt in Bio-ERP main.py
"""

from fastapi import FastAPI
from .customer_portal_router import router as customer_portal_router


def create_customer_portal_app() -> FastAPI:
    """Factory function to create the Customer Portal stub sub-application."""
    app = FastAPI(
        title="Customer Portal Module (Stub)",
        description="ERP customer_portal module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(customer_portal_router)

    @app.get("/")
    async def root():
        return {
            "module": "customer_portal",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
