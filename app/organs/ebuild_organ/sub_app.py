"""
Ebuild System Sub-Application for BIO-ERP v5
=============================================
Mount at: app.mount("/api/v1/ebuild", ebuild_app) in BIO-ERP's main.py
"""

from fastapi import FastAPI

from app.organs.ebuild_organ.router import router as ebuild_router

ebuild_app = FastAPI(
    title="Ebuild System Organ",
    description="Universal ERP Meta-Builder — assemble any ERP for any company based on activity profile, cycles, and modules",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

ebuild_app.include_router(ebuild_router)


@ebuild_app.get("/")
def root():
    return {
        "service": "Ebuild System Organ",
        "version": "1.0.0",
        "profiles": "/api/v1/ebuild/profiles",
        "cycles": "/api/v1/ebuild/cycles",
        "modules": "/api/v1/ebuild/modules",
        "builds": "/api/v1/ebuild/builds",
        "companies": "/api/v1/ebuild/companies",
        "docs": "/docs",
        "health": "/health",
    }


@ebuild_app.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "ebuild-system",
        "version": "1.0.0",
    }
