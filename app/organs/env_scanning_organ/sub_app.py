"""
Environmental Scanning & Analysis Sub-Application for BIO-ERP v5.3.0
=====================================================================
Mount at: app.mount("/api/v1/env-scanning", env_scanning_app)

10 Techniques:
  1. PESTEL Analysis
  2. SWOT Analysis
  3. Scenario Planning
  4. Competitor Intelligence
  5. Customer Analysis
  6. Trend Analysis
  7. Benchmarking
  8. Market Research
  9. Stakeholder Mapping
  10. Environmental Assessment
"""

from fastapi import FastAPI
from datetime import datetime

from app.organs.env_scanning_organ.router import router as env_router

env_scanning_app = FastAPI(
    title="Environmental Scanning & Analysis Microservice",
    description=(
        "BIO-ERP v5.3.0 — 10 environmental scanning techniques with real business logic. "
        "PESTEL, SWOT, Scenario Planning, Competitor Intelligence, Customer Analysis, "
        "Trend Analysis, Benchmarking, Market Research, Stakeholder Mapping, "
        "Environmental Assessment"
    ),
    version="5.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

env_scanning_app.include_router(env_router)


@env_scanning_app.get("/info")
def module_info():
    return {
        "module": "Environmental Scanning",
        "version": "5.3.0",
        "techniques_count": 10,
        "techniques": {
            "macro_analysis": [
                "PESTEL Analysis",
                "SWOT Analysis",
                "Environmental Assessment",
            ],
            "competitive_analysis": [
                "Competitor Intelligence",
                "Customer Analysis",
                "Stakeholder Mapping",
            ],
            "forward_looking": [
                "Scenario Planning",
                "Trend Analysis",
                "Benchmarking",
                "Market Research",
            ],
        },
        "engine_pattern": "stateless static methods — no DB required for calculations",
        "persistence": "Optional DB models for audit trail (es_* tables)",
        "timestamp": datetime.now().isoformat(),
    }
