"""
Resource & Capability Analysis Sub-Application for BIO-ERP v5.3.0
==================================================================
Mount at: app.mount("/api/v1/resource-capability", resource_capability_app)

8 Techniques:
  1. VRIO Framework (Barney)
  2. Value Chain Analysis (Porter)
  3. Core Competency Assessment (Prahalad & Hamel)
  4. Dynamic Capabilities (Teece sensing/seizing/reconfiguring)
  5. Resource Audit (tangible/intangible/human)
  6. Capability Mapping (heat map + build/buy/ally)
  7. Knowledge Assets Assessment (intellectual capital)
  8. Outsourcing Analysis (make/buy/ally decision matrix)
"""

from datetime import datetime

from fastapi import FastAPI

from app.organs.resource_capability_organ.router import (
    router as resource_capability_router,
)

resource_capability_app = FastAPI(
    title="Resource & Capability Analysis Microservice",
    description=(
        "BIO-ERP v5.3.0 — 8 resource & capability analysis techniques with real business logic. "
        "VRIO, Value Chain, Core Competency, Dynamic Capabilities, Resource Audit, "
        "Capability Mapping, Knowledge Assets, Outsourcing Analysis"
    ),
    version="5.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

resource_capability_app.include_router(resource_capability_router)


@resource_capability_app.get("/info")
async def module_info():
    return {
        "module": "Resource & Capability Analysis",
        "version": "5.3.0",
        "techniques_count": 8,
        "categories": {
            "internal_analysis": [
                "VRIO Framework",
                "Value Chain Analysis",
                "Core Competency Assessment",
                "Knowledge Assets Assessment",
            ],
            "capability_management": [
                "Dynamic Capabilities",
                "Capability Mapping",
                "Resource Audit",
            ],
            "sourcing_decisions": [
                "Outsourcing Analysis",
            ],
        },
        "engine_pattern": "stateless static methods — no DB required for calculations",
        "persistence": "Optional DB models for audit trail (rc_* tables)",
        "timestamp": datetime.now().isoformat(),
    }
