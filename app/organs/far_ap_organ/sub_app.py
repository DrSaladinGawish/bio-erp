from fastapi import FastAPI
from app.organs.far_ap_organ.router import router as ap_router

ap_app = FastAPI(title="FAR-AP Accounts Payable",
    description="Vendor management, bills, payments, credit notes, aging, approval queue",
    version="1.0.0", docs_url="/docs", redoc_url="/redoc")
ap_app.include_router(ap_router)

@ap_app.get("/")
def root():
    return {"service": "FAR-AP Accounts Payable", "version": "1.0.0",
            "standards": ["IFRS 9", "IAS 37"], "docs": "/docs", "health": "/health"}

@ap_app.get("/health")
def health():
    return {"status": "healthy", "module": "far-ap", "version": "1.0.0"}
