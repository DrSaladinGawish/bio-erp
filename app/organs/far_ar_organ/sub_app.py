from fastapi import FastAPI
from app.organs.far_ar_organ.router import router as ar_router

ar_app = FastAPI(title="FAR-AR Accounts Receivable",
    description="Customer management, invoicing, payments, credit notes, aging, statements",
    version="1.0.0", docs_url="/docs", redoc_url="/redoc")
ar_app.include_router(ar_router)

@ar_app.get("/")
def root():
    return {"service": "FAR-AR Accounts Receivable", "version": "1.0.0",
            "standards": ["IFRS 9", "IFRS 15"], "docs": "/docs", "health": "/health"}

@ar_app.get("/health")
def health():
    return {"status": "healthy", "module": "far-ar", "version": "1.0.0"}
