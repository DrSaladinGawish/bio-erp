"""
Document Management Module — Stub FastAPI Sub-App
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/dms in Bio-ERP main.py
"""

from fastapi import FastAPI
from .document_management_router import router as document_management_router


def create_document_management_app() -> FastAPI:
    """Factory function to create the Document Management stub sub-application."""
    app = FastAPI(
        title="Document Management Module (Stub)",
        description="ERP document_management module — 0 tables, stub",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(document_management_router)

    @app.get("/")
    async def root():
        return {
            "module": "document_management",
            "version": "3.0.0",
            "tables": 0,
            "status": "stub",
            "endpoints": "/docs",
        }

    return app
