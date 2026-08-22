"""
Cost Management Sub-Application for BIO-ERP v5.3.0
====================================================
Mount at: app.mount("/api/v1/cost-management", cost_management_app)

24 Techniques:
  1. Activity-Based Costing (ABC)
  2. Time-Driven ABC (TDABC)
  3. Resource Consumption Accounting (RCA)
  4. Traditional Costing
  5. Target Costing
  6. Kaizen Costing
  7. Life Cycle Costing
  8. Throughput Accounting
  9. Standard Costing
  10. Variable Costing
  11. Absorption Costing
  12. Marginal Costing
  13. Process Costing
  14. Job Order Costing
  15. Batch Costing
  16. Contract Costing
  17. Service Costing
  18. Joint Product Costing
  19. By-Product Costing
  20. Backflush Costing
  21. Gemba Costing
  22. Quality Costing (COQ)
  23. Environmental Costing
  24. Strategic Cost Management
"""

from fastapi import FastAPI
from datetime import datetime

from app.organs.cost_management_organ.router import router as cost_router

cost_management_app = FastAPI(
    title="Cost Management Microservice",
    description=(
        "BIO-ERP v5.3.0 — 24 cost management techniques with real business logic. "
        "ABC, TDABC, RCA, Target, Kaizen, Life Cycle, Throughput, Standard, "
        "Variable, Absorption, Marginal, Process, Job Order, Batch, Contract, "
        "Service, Joint Product, By-Product, Backflush, Gemba, COQ, "
        "Environmental, Strategic Cost Management"
    ),
    version="5.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

cost_management_app.include_router(cost_router)


@cost_management_app.get("/info")
def module_info():
    return {
        "module": "Cost Management",
        "version": "5.3.0",
        "techniques_count": 24,
        "categories": {
            "costing_systems": [
                "ABC",
                "TDABC",
                "RCA",
                "Traditional",
                "Standard",
                "Variable",
                "Absorption",
                "Marginal",
                "Process",
                "Job Order",
                "Batch",
                "Backflush",
            ],
            "strategic_costing": [
                "Target",
                "Kaizen",
                "Life Cycle",
                "Throughput",
                "Strategic",
            ],
            "specialized": [
                "Contract",
                "Service",
                "Joint Product",
                "By-Product",
                "Gemba",
                "Quality COQ",
                "Environmental",
            ],
        },
        "engine_pattern": "stateless static methods — no DB required for calculations",
        "persistence": "Optional DB models for audit trail (cm_* tables)",
        "timestamp": datetime.now().isoformat(),
    }
