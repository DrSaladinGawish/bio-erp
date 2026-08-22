"""
Risk & Uncertainty Management Sub-Application for BIO-ERP v5.3.0
================================================================
Mount at: app.mount("/api/v1/risk-uncertainty", risk_uncertainty_app)

6 Techniques:
  1. Value at Risk (VaR) — Parametric, Historical, Monte Carlo
  2. Monte Carlo Simulation — Probabilistic scenario generation
  3. Black Swan Detection — Extreme event identification
  4. Sensitivity Analysis — Variable impact on outcomes
  5. Decision Trees — Sequential decision analysis
  6. Scenario Analysis — Multi-scenario comparison
"""

from fastapi import FastAPI
from datetime import datetime

from app.organs.risk_uncertainty_organ.router import router as risk_router

risk_uncertainty_app = FastAPI(
    title="Risk & Uncertainty Management Microservice",
    description=(
        "BIO-ERP v5.3.0 — 6 risk and uncertainty management techniques with real business logic. "
        "VaR, Monte Carlo, Black Swan Detection, Sensitivity Analysis, "
        "Decision Trees, Scenario Analysis"
    ),
    version="5.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

risk_uncertainty_app.include_router(risk_router)


@risk_uncertainty_app.get("/info")
def module_info():
    return {
        "module": "Risk & Uncertainty Management",
        "version": "5.3.0",
        "techniques_count": 6,
        "categories": {
            "risk_quantification": [
                "Value at Risk (VaR)",
                "Monte Carlo Simulation",
            ],
            "extreme_event_analysis": [
                "Black Swan Detection",
            ],
            "sensitivity_and_impact": [
                "Sensitivity Analysis",
            ],
            "decision_frameworks": [
                "Decision Trees",
                "Scenario Analysis",
            ],
        },
        "engine_pattern": "stateless static methods — numpy/scipy for calculations",
        "persistence": "Optional DB models for audit trail (ru_* tables)",
        "timestamp": datetime.now().isoformat(),
    }
