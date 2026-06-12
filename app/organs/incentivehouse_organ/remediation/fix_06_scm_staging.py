#!/usr/bin/env python3
"""FIX 6 (P0): Inject scm_staging_* models into IH models.py"""

import sys
import pathlib

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
IH = BASE / "app" / "organs" / "incentivehouse_organ"
DRY = "--dry-run" in sys.argv

print("FIX 6: Add scm_staging_* ORM models")

SCM_BLOCK = """

# AUTO-INJECTED by audit fix 4.8 - SCM staging tables
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

class ScmStagingCostEstimate(Base):
    __tablename__ = "scm_staging_cost_estimates"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, index=True)
    cost_category = Column(String(64))
    estimated_amount = Column(Float)
    currency = Column(String(8), default="EGP")
    created_at = Column(DateTime, server_default=func.now())


class ScmStagingJobMaterial(Base):
    __tablename__ = "scm_staging_job_materials"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, index=True)
    item_code = Column(String(64))
    qty = Column(Float)
    unit_cost = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class ScmStagingReconRow(Base):
    __tablename__ = "scm_staging_recon_rows"
    id = Column(Integer, primary_key=True)
    trnx_id = Column(String(64), index=True)
    amount = Column(Float)
    matched = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
"""

# Try production models first, then regular models
candidates = [IH / "models_production.py", IH / "models.py"]
target = None
for c in candidates:
    if c.exists():
        target = c
        break

if not target:
    print("  [SKIP] IH models.py/models_production.py not found")
    sys.exit(0)
src = target.read_text(encoding="utf-8", errors="ignore")
if "scm_staging" in src:
    print(f"  [OK]  scm_staging already present in {target.name}")
    sys.exit(0)
# Ensure Base is imported
if "from sqlalchemy" in src and "Base" in src and "declarative_base" not in src:
    # If Base is defined elsewhere (likely)
    pass
if DRY:
    print(f"  [DRY] would inject 3 scm_staging_* models into {target.name}")
else:
    target.write_text(src + SCM_BLOCK, encoding="utf-8")
    print(f"  [FIX] injected 3 scm_staging_* models into {target.name}")
    print(
        "         Tables: scm_staging_cost_estimates, scm_staging_job_materials, scm_staging_recon_rows"
    )
print("  Done.")
