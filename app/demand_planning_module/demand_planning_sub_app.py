"""
Demand Planning Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/dp in Bio-ERP main.py
"""

from fastapi import FastAPI
from .demand_planning_router import router as demand_planning_router


def create_demand_planning_app() -> FastAPI:
    """Factory function to create the Demand Planning stub sub-application."""
    app = FastAPI(
        title="Demand Planning Module (Stub)",
        description="ERP demand_planning module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(demand_planning_router)

    @app.get("/")
    async def root():
        return {
            "module": "demand_planning",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
