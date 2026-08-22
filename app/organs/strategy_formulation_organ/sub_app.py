"""
Strategy Formulation Sub-Application for BIO-ERP v5.3.0
========================================================
Mount at: app.mount("/api/v1/strategy-formulation", strategy_formulation_app)

12 Techniques:
   1. BCG Matrix (Growth-Share)
   2. Ansoff Matrix (Product-Market Growth Vector)
   3. Blue Ocean Strategy (ERRC Grid + Value Curve)
   4. Porter's Generic Strategies
   5. TOWS Strategy (SWOT-to-Strategy Bridge)
   6. Competitive Advantage Assessment
   7. Core Competency (Prahalad & Hamel)
   8. Strategic Intent (Stretch Goals & Alignment)
   9. Value Innovation (Cost-Value Frontier)
  10. Disruptive Innovation (Christensen)
  11. Platform Strategy (Network Effects & WTA)
  12. Ecosystem Strategy (Health & Resilience Mapping)
"""

from fastapi import FastAPI
from datetime import datetime

from app.organs.strategy_formulation_organ.router import router as strategy_router

strategy_formulation_app = FastAPI(
    title="Strategy Formulation Microservice",
    description=(
        "BIO-ERP v5.3.0 — 12 strategy formulation techniques with real business logic. "
        "BCG Matrix, Ansoff Matrix, Blue Ocean Strategy, Porter's Generic Strategies, "
        "TOWS Strategy, Competitive Advantage, Core Competency, Strategic Intent, "
        "Value Innovation, Disruptive Innovation, Platform Strategy, Ecosystem Strategy"
    ),
    version="5.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

strategy_formulation_app.include_router(strategy_router)


@strategy_formulation_app.get("/info")
def module_info():
    return {
        "module": "Strategy Formulation",
        "version": "5.3.0",
        "techniques_count": 12,
        "categories": {
            "portfolio_analysis": [
                "BCG Matrix",
                "Ansoff Matrix",
            ],
            "competitive_positioning": [
                "Blue Ocean Strategy",
                "Porter's Generic Strategies",
                "Competitive Advantage",
                "Core Competency",
            ],
            "strategy_synthesis": [
                "TOWS Strategy",
                "Strategic Intent",
                "Value Innovation",
            ],
            "innovation_and_platforms": [
                "Disruptive Innovation",
                "Platform Strategy",
                "Ecosystem Strategy",
            ],
        },
        "engine_pattern": "stateless static methods — no DB required for calculations",
        "persistence": "Optional DB models for audit trail (sf_* tables)",
        "timestamp": datetime.now().isoformat(),
    }
