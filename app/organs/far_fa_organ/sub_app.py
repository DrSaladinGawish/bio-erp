from fastapi import FastAPI
from app.organs.far_fa_organ.router import router as fa_router

far_fa_app = FastAPI(title="FAR-FA Fixed Assets",
    description="Asset management, depreciation (SL/DB/SYD), disposal, revaluation",
    version="1.0.0", docs_url="/docs", redoc_url="/redoc")
far_fa_app.include_router(fa_router)

@far_fa_app.get("/")
def root():
    return {"service": "FAR-FA Fixed Assets", "version": "1.0.0",
            "standards": ["IAS 16", "IAS 36", "IFRS 5"], "docs": "/docs", "health": "/health"}

@far_fa_app.get("/health")
def health():
    return {"status": "healthy", "module": "far-fa", "version": "1.0.0"}
