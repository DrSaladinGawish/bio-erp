#!/usr/bin/env python3
"""
IH ERP REMEDIATION ORCHESTRATOR
Runs all 8 fix scripts in order.
Usage:  python run_all_fixes.py [--dry-run]
"""

import sys
import subprocess
import pathlib

HERE = pathlib.Path(__file__).parent
DRY = "--dry-run" in sys.argv

FIXES = [
    "fix_01_password.py",  # P0 - run_migration.py
    "fix_02_event_form_fields.py",  # P0 - event_form.html
    "fix_03_recon_features.py",  # P0 - bank_recon_form.html
    "fix_04_sales_api.py",  # P0 - IH sal_router
    "fix_05_ai_window.py",  # P0 - base.html
    "fix_06_scm_staging.py",  # P0 - IH models
    "fix_07_variance.py",  # P0 - new file
    "fix_08_fix_scripts.py",  # P1 - tools/
]

print("=" * 70)
print("IH ERP REMEDIATION ORCHESTRATOR")
print(f"Mode: {'DRY-RUN' if DRY else 'APPLY'}")
print(f"Fixes: {len(FIXES)}")
print("=" * 70)

results = []
for fix in FIXES:
    path = HERE / fix
    if not path.exists():
        print(f"  [MISS] {fix} not found, skipping")
        results.append((fix, "MISS"))
        continue
    print(f"\n>>> Running {fix}")
    cmd = [sys.executable, str(path)] + (["--dry-run"] if DRY else [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
    results.append((fix, "OK" if r.returncode == 0 else "FAIL"))

print("\n" + "=" * 70)
print("REMEDIATION SUMMARY")
print("=" * 70)
for fix, status in results:
    icon = "OK" if status == "OK" else ("-- " if status == "MISS" else "FAIL")
    print(f"  [{icon:4s}] {fix}")

ok = sum(1 for _, s in results if s == "OK")
print(f"\nCompleted: {ok}/{len(FIXES)} fixes")
print(
    "\nNEXT: Re-run audit:  python ..\\ih_erp_audit_v2.py --base ..\\..\\..\\.. --port 9001"
)
