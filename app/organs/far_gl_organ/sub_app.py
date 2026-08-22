"""
FAR-GL Sub-Application for BIO-ERP v5
=======================================
Mount at: app.mount("/api/v1/far-gl", far_gl_app) in BIO-ERP's main.py
"""

from fastapi import FastAPI

from app.organs.far_gl_organ.router import router as far_gl_router

far_gl_app = FastAPI(
    title="FAR-GL General Ledger",
    description="Financial Accounting & Reporting: General Ledger — periods, chart of accounts, journals, trial balance, adjusting entries, financial reports, year-end close",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

far_gl_app.include_router(far_gl_router)


@far_gl_app.get("/")
def root():
    return {
        "service": "FAR-GL General Ledger",
        "version": "1.0.0",
        "standards": ["IFRS", "IAS 1", "IAS 8", "IAS 16", "IAS 21", "IAS 36"],
        "docs": "/docs",
        "health": "/health",
    }


@far_gl_app.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "far-gl",
        "version": "1.0.0",
    }
