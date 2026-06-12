#!/usr/bin/env python3
"""FIX 1 (P0): Remove hardcoded password from run_migration.py"""

import sys
import pathlib

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
DRY = "--dry-run" in sys.argv
p = BASE / "run_migration.py"

print("FIX 1: Remove hardcoded password from run_migration.py")
if not p.exists():
    print("  [SKIP] run_migration.py not found at", p)
    sys.exit(0)
src = p.read_text(encoding="utf-8", errors="ignore")
new_src = src.replace(
    'password="postgres123"',
    'password=os.environ.get("PG_PASSWORD", "")  # moved to .env by audit fix 12.5',
)
if src == new_src:
    print("  [OK]  no hardcoded password found (already fixed)")
    sys.exit(0)
if DRY:
    print("  [DRY] would replace hardcoded password with os.environ.get(...)")
else:
    p.write_text(new_src, encoding="utf-8")
    print("  [FIX] line 30: hardcoded password -> os.environ.get('PG_PASSWORD', '')")
    print("        Also update .env with:  PG_PASSWORD=postgres123")
print("  Done.")
