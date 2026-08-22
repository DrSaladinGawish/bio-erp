"""
Recruitment Talent Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/rec in Bio-ERP main.py
"""

from fastapi import FastAPI
from .recruitment_talent_router import router as recruitment_talent_router


def create_recruitment_talent_app() -> FastAPI:
    """Factory function to create the Recruitment Talent stub sub-application."""
    app = FastAPI(
        title="Recruitment Talent Module (Stub)",
        description="ERP recruitment_talent module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(recruitment_talent_router)

    @app.get("/")
    async def root():
        return {
            "module": "recruitment_talent",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
