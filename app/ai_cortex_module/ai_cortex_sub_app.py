"""
Ai Cortex Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/aic in Bio-ERP main.py
"""

from fastapi import FastAPI
from .ai_cortex_router import router as ai_cortex_router


def create_ai_cortex_app() -> FastAPI:
    """Factory function to create the Ai Cortex stub sub-application."""
    app = FastAPI(
        title="Ai Cortex Module (Stub)",
        description="ERP ai_cortex module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(ai_cortex_router)

    @app.get("/")
    async def root():
        return {
            "module": "ai_cortex",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
