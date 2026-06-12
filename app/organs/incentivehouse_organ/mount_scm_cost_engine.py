"""
Mount SCM Cost Engine into Bio-ERP main.py
Add these lines to integrate with existing /api/v1/scm prefix.

Current state (from your report):
  Line 70:  import scm_bio_bridge
  Line 705: app.include_router(scm_bridge_router, prefix="/api/v1/scm")

Add AFTER line 705:
"""

# === ADD TO app/main.py AFTER line 705 (after SCM bridge mount) ===
from app.organs.incentivehouse_organ.scm_cost_engine import (
    router as scm_cost_engine_router,
)

app.include_router(scm_cost_engine_router, prefix="/api/v1/scm")  # noqa: F821

# This creates the full route tree:
#   /api/v1/scm/scm-bridge/*   (from hardened bridge)
#   /api/v1/scm/cost-engine/*  (from cost engine)
#
# Example endpoints:
#   POST /api/v1/scm/cost-engine/analyze/event/full
#   POST /api/v1/scm/cost-engine/analyze/value-chain
#   POST /api/v1/scm/cost-engine/analyze/target-costing
#   POST /api/v1/scm/cost-engine/analyze/sustainability
#   POST /api/v1/scm/cost-engine/analyze/profitability
#   POST /api/v1/scm/cost-engine/analyze/cvp
#   POST /api/v1/scm/cost-engine/analyze/abc
#   POST /api/v1/scm/cost-engine/analyze/vendor-scorecard
#   GET  /api/v1/scm/cost-engine/engines
#   GET  /api/v1/scm/cost-engine/health
