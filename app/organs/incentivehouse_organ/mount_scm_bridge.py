"""
Mount SCM-BIO Bridge into Bio-ERP (Doctor System)
Add these lines to your Bio-ERP main.py
"""

# === ADD TO TOP OF main.py ===
from app.scm_bridge.scm_bio_bridge_fixed import router as scm_bridge_router

# === ADD AFTER app = FastAPI(...) ===
app.include_router(scm_bridge_router, prefix="/api/v1/scm")  # noqa: F821

# Directory structure expected:
# D:\ERP System\BIO_ERP\
#   app/
#     main.py
#     scm_bridge/
#       __init__.py          (empty or with version)
#       scm_bio_bridge_fixed.py
#
# Access URLs after mount:
#   GET  /api/v1/scm/scm-bridge/production/events
#   GET  /api/v1/scm/scm-bridge/production/events/{id}
#   GET  /api/v1/scm/scm-bridge/production/clients
#   GET  /api/v1/scm/scm-bridge/production/transactions
#   GET  /api/v1/scm/scm-bridge/production/vendors
#   POST /api/v1/scm/scm-bridge/staging/cost-analysis
#   POST /api/v1/scm/scm-bridge/staging/vendor-scorecard
#   POST /api/v1/scm/scm-bridge/staging/budget-forecast
#   POST /api/v1/scm/scm-bridge/staging/request-promotion
#   POST /api/v1/scm/scm-bridge/admin/approve-promotion/{id}
#   GET  /api/v1/scm/scm-bridge/staging/cost-summary
