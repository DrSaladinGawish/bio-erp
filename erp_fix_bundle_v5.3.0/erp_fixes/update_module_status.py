"""
update_module_status.py
=======================
Queries every module's live API endpoint and rebuilds the module
status map with real counts — no more hardcoded EMPTY/ACTIVE flags.

Run:  python update_module_status.py [--base-url http://localhost:9001] [--apply]
      --apply  writes updated status back to module_status.json (or wherever
               your launcher reads it from)
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── module endpoint registry ──────────────────────────────────────────────────
# Format: module_key → (endpoint, count_field_in_json_response)
# Adjust endpoint paths to match your actual router prefixes.

MODULE_ENDPOINTS = {
    "purchase_orders": ("/api/v1/pur/summary",          "total"),
    "vendor_invoices": ("/api/v1/api/vendor-invoices",  "total"),   # adjust prefix
    "sales_invoices":  ("/api/v1/sal/summary",          "total"),
    "bank_transactions": ("/api/v1/acc/bank-transactions", "total"),
    "grn_receipts":    ("/api/v1/grn/summary",          "total_receipts"),
    "clients":         ("/api/v1/env/clients",          "total"),   # the broken one
    "suppliers":       ("/api/v1/env/suppliers",        "total"),
    "pnr_events":      ("/api/v1/evn/summary",          "total"),
    "eta_validations": ("/api/v1/eta/summary",          "total_validated"),
}

# Known-good counts from dashboard (used as cross-check)
DASHBOARD_KNOWN = {
    "purchase_orders":   93,
    "vendor_invoices":   386,
    "sales_invoices":    93,
    "bank_transactions": 2501,
    "grn_receipts":      20,
    "clients":           49,
    "suppliers":         175,
    "pnr_events":        143,
}

# Where your launcher stores the module status map
STATUS_MAP_CANDIDATES = [
    "module_status.json",
    "config/module_status.json",
    "app/config/module_status.json",
    "launcher/module_status.json",
    "static/module_status.json",
]


# ── helpers ───────────────────────────────────────────────────────────────────

def find_status_map() -> Path | None:
    for p in STATUS_MAP_CANDIDATES:
        path = Path(p)
        if path.exists():
            return path
    return None


def probe_endpoint(base_url: str, endpoint: str, count_field: str,
                   timeout: int = 5) -> dict:
    url = base_url.rstrip("/") + endpoint
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            # support nested field like "data.total"
            parts = count_field.split(".")
            val = data
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            count = int(val) if val is not None else _count_list(data)
            return {"status": "ok", "count": count, "http": 200}
        else:
            return {"status": "error", "count": 0, "http": r.status_code}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "count": 0, "http": None}
    except Exception as e:
        return {"status": "error", "count": 0, "http": None, "detail": str(e)}


def _count_list(data) -> int:
    """If response is a list or has a 'data' list, count it."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("data", "items", "results", "records"):
            if isinstance(data.get(key), list):
                return len(data[key])
    return 0


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rebuild module status map from live counts")
    parser.add_argument("--base-url", default="http://localhost:9001",
                        help="ERP server base URL")
    parser.add_argument("--apply", action="store_true",
                        help="Write updated status map to disk")
    args = parser.parse_args()

    print("=" * 65)
    print("  MODULE STATUS MAP UPDATER")
    print(f"  Target: {args.base_url}")
    print("=" * 65)

    results = {}
    mismatches = []

    for module, (endpoint, count_field) in MODULE_ENDPOINTS.items():
        probe = probe_endpoint(args.base_url, endpoint, count_field)
        live_count = probe["count"]
        known = DASHBOARD_KNOWN.get(module)
        status = "ACTIVE" if live_count > 0 else "EMPTY"

        match_flag = ""
        if known is not None and live_count != known:
            match_flag = f"  ⚠️  expected {known}"
            mismatches.append((module, live_count, known))

        http_label = f"HTTP {probe['http']}" if probe["http"] else probe["status"]
        print(f"  {module:<22} [{http_label:<8}]  count={live_count:<6}  → {status}{match_flag}")

        results[module] = {
            "status": status,
            "live_count": live_count,
            "endpoint": endpoint,
            "last_checked": datetime.utcnow().isoformat() + "Z",
        }

    # ── summary ───────────────────────────────────────────────────────────────
    print()
    if mismatches:
        print("⚠️  COUNT MISMATCHES (live vs dashboard):")
        for mod, live, known in mismatches:
            print(f"   {mod}: live={live}, dashboard={known}")
    else:
        print("✅ All live counts match dashboard expectations.")

    # ── write output ──────────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "server": args.base_url,
        "modules": results,
    }

    output_path = Path("module_status_updated.json")
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\n📄 Updated map written → {output_path}")

    if args.apply:
        target = find_status_map()
        if target:
            import shutil
            backup = target.with_suffix(
                f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(target, backup)
            target.write_text(json.dumps(output, indent=2), encoding="utf-8")
            print(f"✅ Applied → {target}  (backup: {backup})")
        else:
            print("⚠️  No existing status map found; place module_status_updated.json "
                  "manually into your launcher config directory.")

    print("\nDone. Restart your launcher/scanner to pick up new counts.")


if __name__ == "__main__":
    main()
