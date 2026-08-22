"""
Mobile Platform Module — Stub FastAPI Router
Auto-generated — 0 tables deployed yet.
Mounted at /api/v1/mob
"""

from fastapi import APIRouter

router = APIRouter(prefix="/mob", tags=["Mobile Platform"])


@router.get("/health")
async def health_check():
    """Health check for stub module."""
    return {
        "status": "healthy",
        "module": "mobile_platform",
        "version": "3.0.0",
        "tables": 0,
        "note": "Stub module — no tables deployed",
        "database": "SQL Server 2022",
    }


@router.get("/info")
async def module_info():
    """Return module information."""
    return {
        "module": "mobile_platform",
        "version": "3.0.0",
        "tables": 0,
        "status": "stub",
        "description": "Module not yet deployed — add tables and re-run generator",
    }
