"""
Subscription Billing Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/sub in Bio-ERP main.py
"""

from fastapi import FastAPI
from .subscription_billing_router import router as subscription_billing_router


def create_subscription_billing_app() -> FastAPI:
    """Factory function to create the Subscription Billing stub sub-application."""
    app = FastAPI(
        title="Subscription Billing Module (Stub)",
        description="ERP subscription_billing module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(subscription_billing_router)

    @app.get("/")
    async def root():
        return {
            "module": "subscription_billing",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
