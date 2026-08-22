"""
Strategic Decision-Making Sub-Application for BIO-ERP v5.3.0
=============================================================
Mount at: app.mount("/api/v1/strategic-decision", strategic_decision_app)

10 Techniques:
  1. AHP (Analytic Hierarchy Process)
  2. Real Options Analysis
  3. Decision Trees
  4. Cost-Benefit Analysis
  5. MCDA (Multi-Criteria Decision Analysis)
  6. Game Theory
  7. Sensitivity Analysis
  8. Risk-Reward Analysis
  9. Delphi Method
  10. Strategic Choice
"""

from fastapi import FastAPI
from datetime import datetime

from app.organs.strategic_decision_organ.router import router as sd_router

strategic_decision_app = FastAPI(
    title="Strategic Decision-Making Microservice",
    description=(
        "BIO-ERP v5.3.0 — 10 strategic decision-making techniques with real business logic. "
        "AHP, Real Options, Decision Trees, Cost-Benefit, MCDA, Game Theory, "
        "Sensitivity, Risk-Reward, Delphi, Strategic Choice"
    ),
    version="5.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

strategic_decision_app.include_router(sd_router)


@strategic_decision_app.get("/info")
def module_info():
    return {
        "module": "Strategic Decision-Making",
        "version": "5.3.0",
        "techniques_count": 10,
        "techniques": {
            "analytical": ["AHP", "MCDA"],
            "financial": ["Real Options", "Cost-Benefit", "Risk-Reward"],
            "structural": ["Decision Trees", "Game Theory"],
            "qualitative": ["Delphi", "Sensitivity Analysis", "Strategic Choice"],
        },
        "engine_pattern": "stateless static methods — no DB required for calculations",
        "persistence": "Optional DB models for audit trail (sd_* tables)",
        "numpy_required": True,
        "timestamp": datetime.now().isoformat(),
    }
