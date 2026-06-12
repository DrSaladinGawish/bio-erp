#!/usr/bin/env python3
"""FIX 9 (P0): Remove hardcoded passwords in scripts/seed_realistic_ops_data.py and scripts/schema_aligner.py"""

import sys
import pathlib
import re

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
SCRIPTS = BASE / "scripts"
DRY = "--dry-run" in sys.argv

print("FIX 9: Scrub hardcoded passwords in scripts/")

# Common env-var pattern
PWD_RE = re.compile(r"""password\s*=\s*['"][^'"]+['"]""", re.IGNORECASE)


def scrub(p: pathlib.Path):
    if not p.exists():
        print(f"  [SKIP] {p.name} not found")
        return
    src = p.read_text(encoding="utf-8", errors="ignore")
    new = PWD_RE.sub(
        'password=os.environ.get("PG_PASSWORD", "")  # moved to .env by audit fix 12.5',
        src,
    )
    if new == src:
        print(f"  [OK]  {p.name}: no hardcoded password found")
        return
    if DRY:
        print(f"  [DRY] would scrub password in {p.relative_to(BASE)}")
    else:
        p.write_text(new, encoding="utf-8")
        # Ensure os is imported
        if "import os" not in new.split("\n")[0:30].__repr__():
            new_with_os = "import os\n" + new
            p.write_text(new_with_os, encoding="utf-8")
        print(f"  [FIX] scrubbed password in {p.relative_to(BASE)}")


for fname in ["seed_realistic_ops_data.py", "schema_aligner.py"]:
    scrub(SCRIPTS / fname)

# Also check run_migration.py (already fixed in fix_01 but verify)
scrub(BASE / "run_migration.py")
print("  Done.")
