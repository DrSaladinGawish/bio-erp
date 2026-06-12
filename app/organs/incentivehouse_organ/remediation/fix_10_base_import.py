#!/usr/bin/env python3
"""FIX 10 (P0): Replace 'Base' with 'IncentiveBase' in models_production.py
This is the bug fix for:  NameError: name 'Base' is not defined

Root cause: The earlier fix_06_scm_staging.py injected 3 staging models
using 'class ScmStagingCostEstimate(Base):' but the actual declarative
base in this project is 'IncentiveBase' (defined in models.py as:
    IncentiveBase = declarative_base()
All other models in models_production.py use (IncentiveBase), so the
injected code was inconsistent and crashed the server.
"""

import sys
import pathlib
import shutil
import re

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
IH = BASE / "app" / "organs" / "incentivehouse_organ"
DRY = "--dry-run" in sys.argv
mp = IH / "models_production.py"

print("FIX 10: Replace 'Base' with 'IncentiveBase' in models_production.py")
if not mp.exists():
    print(f"  [SKIP] {mp} not found")
    sys.exit(0)
src = mp.read_text(encoding="utf-8", errors="ignore")
broken = re.findall(r"class\s+(\w+)\(Base\):", src)
if not broken:
    print("  [OK]  no (Base) classes found - already fixed")
    sys.exit(0)
backup = mp.with_suffix(".py.bak.fix10")
if DRY:
    print(f"  [DRY] would replace {len(broken)} (Base) -> (IncentiveBase)")
    print(f"         classes: {broken}")
    print(f"         backup would be: {backup.name}")
else:
    shutil.copy2(mp, backup)
    new_src = src.replace("(Base):", "(IncentiveBase):")
    mp.write_text(new_src, encoding="utf-8")
    print(f"  [FIX] replaced {len(broken)} (Base) -> (IncentiveBase)")
    print(f"         classes: {broken}")
    print(f"  [OK]  backup: {backup.name}")
    print(f"  [OK]  file written: {mp.name}")
print("  Done.")
print()
print("Verify by running:")
print('  cd "D:\\ERP System\\BIO_ERP"')
print("  python -m uvicorn app.main:app --host 0.0.0.0 --port 9001")
