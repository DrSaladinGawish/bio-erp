"""
anomaly_scan.py
===============
Full anomaly diagnostic for the ERP system.
Checks every live endpoint, cross-references with dashboard KPIs,
flags schema mismatches, dead routes, and data integrity issues.

Run:  python anomaly_scan.py [--base-url http://localhost:9001] [--json]
      --json   emit machine-readable JSON report in addition to console output
"""

import json
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests


# ── expected KPIs from your last confirmed dashboard ─────────────────────────
EXPECTED = {
    "pnr_total":          143,
    "pnr_active":         12,
    "purchase_orders":    93,
    "vendor_invoices":    386,
    "sales_invoices":     93,
    "bank_transactions":  2501,
    "grn_receipts":       20,
    "clients":            49,
    "suppliers":          175,
    "eta_validated":      92,
    "eta_rejected":       1,
    "revenue_egp":        56_300_000,
    "costs_egp":          42_300_000,
    "gross_margin_egp":   14_000_000,
    "ap_due_egp":         19_500_000,
    "ar_due_egp":         15_300_000,
    "bank_balance_egp":   2_170_000,
}

# ── endpoint probe definitions ────────────────────────────────────────────────
# (label, path, extractor_lambda_src, tolerance_pct)
#   extractor receives the parsed JSON and returns an int/float
#   tolerance_pct: allow this % deviation before flagging (useful for financials)

PROBES = [
    # Entity counts
    ("clients [env]",       "/api/v1/env/clients",
        lambda d: d.get("total") or (len(d) if isinstance(d, list) else 0),
        0, "clients"),

    ("suppliers [env]",     "/api/v1/env/suppliers",
        lambda d: d.get("total") or (len(d) if isinstance(d, list) else 0),
        0, "suppliers"),

    ("purchase_orders",     "/api/v1/pur/summary",
        lambda d: d.get("total", 0), 0, "purchase_orders"),

    ("vendor_invoices",     "/api/v1/api/vendor-invoices",
        lambda d: d.get("total", 0) or (len(d.get("data", d if isinstance(d, list) else [])) ),
        0, "vendor_invoices"),

    ("sales_invoices",      "/api/v1/sal/summary",
        lambda d: d.get("total", 0), 0, "sales_invoices"),

    ("bank_transactions",   "/api/v1/acc/bank-transactions",
        lambda d: d.get("total", 0) or len(d.get("data", [])),
        0, "bank_transactions"),

    ("grn_receipts",        "/api/v1/grn/summary",
        lambda d: d.get("total_receipts", d.get("total", 0)),
        0, "grn_receipts"),

    ("pnr_total",           "/api/v1/evn/summary",
        lambda d: d.get("total", 0), 0, "pnr_total"),

    ("pnr_active",          "/api/v1/evn/summary",
        lambda d: d.get("active", 0), 0, "pnr_active"),

    ("eta_validated",       "/api/v1/eta/summary",
        lambda d: d.get("total_validated", d.get("validated", 0)),
        0, "eta_validated"),

    # Financial KPIs (5% tolerance)
    ("revenue",             "/api/v1/fin/dashboard",
        lambda d: d.get("revenue", d.get("total_revenue", 0)),
        5, "revenue_egp"),

    ("costs",               "/api/v1/fin/dashboard",
        lambda d: d.get("costs", d.get("total_costs", 0)),
        5, "costs_egp"),

    ("gross_margin",        "/api/v1/fin/dashboard",
        lambda d: d.get("gross_margin", 0),
        5, "gross_margin_egp"),

    ("ap_due",              "/api/v1/fin/dashboard",
        lambda d: d.get("ap_due", 0),
        5, "ap_due_egp"),

    ("ar_due",              "/api/v1/fin/dashboard",
        lambda d: d.get("ar_due", 0),
        5, "ar_due_egp"),

    ("bank_balance",        "/api/v1/acc/bank-balance",
        lambda d: d.get("balance", d.get("total_balance", 0)),
        2, "bank_balance_egp"),
]


# ── probe runner ──────────────────────────────────────────────────────────────

class AnomalyScanner:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"
        self._cache: dict[str, tuple] = {}   # url → (status_code, json)
        self.anomalies: list[dict] = []
        self.passes: list[dict] = []

    def _get(self, path: str, timeout: int = 6) -> tuple[int, dict | None]:
        url = self.base + path
        if url in self._cache:
            return self._cache[url]
        try:
            r = self.session.get(url, timeout=timeout)
            try:
                data = r.json()
            except Exception:
                data = None
            result = (r.status_code, data)
        except requests.exceptions.ConnectionError:
            result = (0, None)
        except Exception as e:
            result = (-1, {"error": str(e)})
        self._cache[url] = result
        return result

    def _pct_diff(self, actual, expected) -> float | None:
        if expected == 0:
            return None
        return abs(actual - expected) / expected * 100

    def run(self) -> list[dict]:
        all_results = []

        for label, path, extractor, tolerance, expected_key in PROBES:
            status_code, data = self._get(path)

            row = {
                "label": label,
                "endpoint": path,
                "http": status_code,
                "value": None,
                "expected": EXPECTED.get(expected_key),
                "tolerance_pct": tolerance,
                "anomaly": False,
                "reason": None,
            }

            if status_code == 0:
                row["anomaly"] = True
                row["reason"] = "CONNECTION_REFUSED"
            elif status_code != 200:
                row["anomaly"] = True
                row["reason"] = f"HTTP_{status_code}"
            elif data is None:
                row["anomaly"] = True
                row["reason"] = "INVALID_JSON"
            else:
                try:
                    val = extractor(data)
                    row["value"] = val
                    if row["expected"] is not None:
                        diff = self._pct_diff(val, row["expected"])
                        if diff is not None and diff > tolerance:
                            row["anomaly"] = True
                            row["reason"] = (
                                f"VALUE_MISMATCH: got {val:,}, "
                                f"expected {row['expected']:,} "
                                f"({diff:.1f}% off)"
                            )
                except Exception as e:
                    row["anomaly"] = True
                    row["reason"] = f"EXTRACTOR_ERROR: {e}"

            all_results.append(row)
            if row["anomaly"]:
                self.anomalies.append(row)
            else:
                self.passes.append(row)

        return all_results


# ── report printer ────────────────────────────────────────────────────────────

def print_report(results: list[dict], scanner: AnomalyScanner):
    print("\n" + "=" * 70)
    print("  FULL ANOMALY DIAGNOSTIC REPORT")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    print(f"\n{'Label':<22} {'Endpoint':<35} {'Got':>10} {'Exp':>10}  Status")
    print("-" * 90)

    for r in results:
        got = f"{r['value']:,}" if r['value'] is not None else "—"
        exp = f"{r['expected']:,}" if r['expected'] is not None else "—"
        flag = "❌ ANOMALY" if r["anomaly"] else "✅ OK"
        print(f"  {r['label']:<20} {r['endpoint']:<35} {got:>10} {exp:>10}  {flag}")
        if r["anomaly"] and r["reason"]:
            print(f"    ↳ {r['reason']}")

    print("\n" + "=" * 70)
    total = len(results)
    n_ok  = len(scanner.passes)
    n_bad = len(scanner.anomalies)
    print(f"  SUMMARY: {n_ok}/{total} checks passed  |  {n_bad} anomalies found")
    print("=" * 70)

    if scanner.anomalies:
        print("\n🔧 ANOMALY DETAILS & REMEDIATION")
        for i, a in enumerate(scanner.anomalies, 1):
            print(f"\n  [{i}] {a['label']}")
            print(f"      Endpoint : {a['endpoint']}")
            print(f"      HTTP     : {a['http']}")
            print(f"      Reason   : {a['reason']}")
            # specific advice
            if "CONNECTION" in (a["reason"] or ""):
                print("      Fix      : Server not responding on this route. "
                      "Check router registration in main.py.")
            elif "HTTP_404" in (a["reason"] or ""):
                print("      Fix      : Route not registered. "
                      "Add router include in main.py.")
            elif "HTTP_500" in (a["reason"] or ""):
                print("      Fix      : Server error. Check server logs for traceback.")
            elif "VALUE_MISMATCH" in (a["reason"] or "") and "clients" in a["label"]:
                print("      Fix      : Run fix_client_endpoint.py --apply")
            elif "VALUE_MISMATCH" in (a["reason"] or "") and "grn" in a["label"].lower():
                print("      Fix      : Run update_module_status.py --apply")
    else:
        print("\n🎉 No anomalies found. All counts match expected values.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Full ERP anomaly diagnostic")
    parser.add_argument("--base-url", default="http://localhost:9001")
    parser.add_argument("--json", action="store_true",
                        help="Also write anomaly_report.json")
    args = parser.parse_args()

    print(f"🔍 Scanning {args.base_url} ...")
    t0 = time.time()

    scanner = AnomalyScanner(args.base_url)
    results = scanner.run()
    elapsed = time.time() - t0

    print_report(results, scanner)
    print(f"\n  Scan completed in {elapsed:.1f}s")

    if args.json:
        out = {
            "scanned_at": datetime.utcnow().isoformat() + "Z",
            "server": args.base_url,
            "summary": {
                "total_checks": len(results),
                "passed": len(scanner.passes),
                "anomalies": len(scanner.anomalies),
            },
            "results": results,
        }
        p = Path("anomaly_report.json")
        p.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"  JSON report → {p}")

    sys.exit(1 if scanner.anomalies else 0)


if __name__ == "__main__":
    main()
