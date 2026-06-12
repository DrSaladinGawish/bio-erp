"""
fix_client_endpoint.py
======================
Diagnoses and fixes the /api/v1/env/clients → 0 count anomaly.

Run:  python fix_client_endpoint.py [--apply]
      --apply   actually patches env_router.py in place (backs up first)
"""

import sys
import re
import shutil
import importlib
import argparse
from pathlib import Path
from datetime import datetime

# ── config ────────────────────────────────────────────────────────────────────
ROUTER_CANDIDATES = [
    "routers/env_router.py",
    "app/routers/env_router.py",
    "api/routers/env_router.py",
    "backend/routers/env_router.py",
]

# Table/model names to probe
TABLE_CANDIDATES = [
    "Clnt_Mtbl", "Client", "clients", "client",
    "Env_Client", "EnvClient", "ClientMaster",
]

# ── helpers ───────────────────────────────────────────────────────────────────

def find_router() -> Path | None:
    for p in ROUTER_CANDIDATES:
        path = Path(p)
        if path.exists():
            return path
    # fallback: walk cwd
    for path in Path(".").rglob("env_router.py"):
        return path
    return None


def scan_router(router_path: Path) -> dict:
    """Return a diagnostic dict about the router file."""
    src = router_path.read_text(encoding="utf-8")
    lines = src.splitlines()

    report = {
        "path": str(router_path),
        "total_lines": len(lines),
        "client_route_line": None,
        "model_used": None,
        "filter_detected": None,
        "suggested_fix": None,
    }

    for i, line in enumerate(lines, 1):
        if "clients" in line.lower() and ("def " in line or "@router" in line):
            report["client_route_line"] = i

        for tbl in TABLE_CANDIDATES:
            if tbl in line:
                report["model_used"] = tbl

        # detect over-restrictive filters
        if "is_active" in line or "status ==" in line or "deleted" in line.lower():
            report["filter_detected"] = line.strip()

    # decide suggested fix
    if report["model_used"] and report["model_used"] != "Clnt_Mtbl":
        report["suggested_fix"] = (
            f"Replace db.query({report['model_used']}) "
            f"with db.query(Clnt_Mtbl) in the /clients route"
        )
    elif report["filter_detected"]:
        report["suggested_fix"] = (
            f"Remove or broaden the filter: {report['filter_detected']}"
        )
    else:
        report["suggested_fix"] = (
            "Endpoint may be querying wrong table; "
            "verify model import matches Clnt_Mtbl"
        )

    return report


def patch_router(router_path: Path, dry_run: bool = True) -> list[str]:
    """
    Attempt targeted patches:
      1. Replace wrong model references with Clnt_Mtbl
      2. Comment out over-restrictive filters on client queries
    Returns list of changes made (or would-make).
    """
    src = router_path.read_text(encoding="utf-8")
    original = src
    changes = []

    # Patch 1: wrong model name
    for wrong in TABLE_CANDIDATES:
        if wrong == "Clnt_Mtbl":
            continue
        # only patch inside the /clients endpoint function scope
        pattern = rf'(db\.query\()({re.escape(wrong)})(\))'
        if re.search(pattern, src):
            src = re.sub(pattern, r'\1Clnt_Mtbl\3', src)
            changes.append(f"Replaced db.query({wrong}) → db.query(Clnt_Mtbl)")

    # Patch 2: remove is_active filter that might hide records
    filter_pattern = r'\.filter\([\w.]+\.is_active\s*==\s*True\)'
    if re.search(filter_pattern, src):
        src = re.sub(filter_pattern, '', src)
        changes.append("Removed .filter(is_active == True) from client query")

    if changes and not dry_run:
        backup = router_path.with_suffix(
            f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        )
        shutil.copy2(router_path, backup)
        router_path.write_text(src, encoding="utf-8")
        changes.append(f"Backup saved → {backup}")

    return changes


# ── direct DB probe (fallback) ────────────────────────────────────────────────

def probe_db_directly() -> dict:
    """Try to import the app's DB session and count clients directly."""
    result = {"attempted": False, "count": None, "error": None, "table": None}
    try:
        # Try common project layouts
        for mod_path in ["app.database", "database", "db.session", "core.database"]:
            try:
                db_mod = importlib.import_module(mod_path)
                result["attempted"] = True
                break
            except ImportError:
                continue

        if not result["attempted"]:
            result["error"] = "Could not locate database module"
            return result

        SessionLocal = getattr(db_mod, "SessionLocal", None)
        if not SessionLocal:
            result["error"] = "SessionLocal not found in db module"
            return result

        db = SessionLocal()
        try:
            from sqlalchemy import text
            for tbl in ["Clnt_Mtbl", "clients", "client"]:
                try:
                    row = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()
                    result["count"] = row[0]
                    result["table"] = tbl
                    break
                except Exception:
                    continue
        finally:
            db.close()

    except Exception as e:
        result["error"] = str(e)

    return result


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fix /api/v1/env/clients count=0")
    parser.add_argument("--apply", action="store_true",
                        help="Apply patches to env_router.py (backs up first)")
    args = parser.parse_args()

    print("=" * 60)
    print("  CLIENT ENDPOINT DIAGNOSTIC")
    print("=" * 60)

    # 1. Find router
    router_path = find_router()
    if not router_path:
        print("❌ env_router.py not found. Check ROUTER_CANDIDATES paths.")
        sys.exit(1)
    print(f"✅ Router found: {router_path}")

    # 2. Scan
    report = scan_router(router_path)
    print(f"\n📄 Router stats:")
    print(f"   Lines          : {report['total_lines']}")
    print(f"   Client route @ : line {report['client_route_line'] or 'NOT FOUND'}")
    print(f"   Model used     : {report['model_used'] or 'UNKNOWN'}")
    print(f"   Filter detected: {report['filter_detected'] or 'None'}")
    print(f"\n💡 Suggested fix : {report['suggested_fix']}")

    # 3. DB probe
    print("\n🔍 Probing database directly...")
    db_result = probe_db_directly()
    if db_result["count"] is not None:
        print(f"   ✅ Found {db_result['count']} records in table '{db_result['table']}'")
    elif db_result["error"]:
        print(f"   ⚠️  DB probe skipped: {db_result['error']}")

    # 4. Patch
    print(f"\n{'🔧 APPLYING' if args.apply else '🧪 DRY RUN'} patches...")
    changes = patch_router(router_path, dry_run=not args.apply)
    if changes:
        for c in changes:
            print(f"   → {c}")
    else:
        print("   No automatic patches found. Manual review required.")
        print(f"   Open {router_path} and verify the query near line "
              f"{report['client_route_line'] or '~30'}.")

    if not args.apply and changes:
        print("\n   Re-run with --apply to write changes.")

    print("\n✅ Diagnostic complete.")
    print("   After fix: restart server and GET /api/v1/env/clients → expect 49")


if __name__ == "__main__":
    main()
