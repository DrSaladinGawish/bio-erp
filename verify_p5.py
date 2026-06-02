"""
P5 — HTMX Prescription Job Page Verification
"""
import json, os, sys, py_compile

EC = r"D:\EventCore_ERP\backend"
BIO = r"D:\ERP System\BIO_ERP"
results = []

def log(s, st, d=""):
    results.append({"stage": s, "status": st, "detail": d})
    print(f"  [{s}] {st}" + (f"  {d}" if d else ""))

print("=" * 60)
print("P5 HTMX JOB PAGE — VERIFICATION")
print("=" * 60)

print("\nPHASE 1: FILE EXISTENCE")
files = [
    ("prescriptions_htmx.py", EC + r"\app\routers\prescriptions_htmx.py"),
    ("p5_integration_snippet.py", BIO + r"\p5_integration_snippet.py"),
]
for n, p in files:
    if os.path.exists(p):
        log(f"FILE: {n}", "PASS", f"{os.path.getsize(p)} bytes")
    else:
        log(f"FILE: {n}", "FAIL", f"Missing: {p}")

print("\nPHASE 2: SYNTAX")
for n, p in files:
    if p.endswith(".py") and os.path.exists(p):
        try:
            py_compile.compile(p, doraise=True)
            log(f"SYNTAX: {n}", "PASS")
        except py_compile.PyCompileError as e:
            log(f"SYNTAX: {n}", "FAIL", str(e))

print("\nPHASE 3: IMPORT")
import subprocess
r = subprocess.run([sys.executable, "-c",
    "from app.routers.prescriptions_htmx import router; "
    "routes = [r.path for r in router.routes]; "
    "print('prefix:', router.prefix); "
    "print('routes:', routes)"],
    cwd=EC, capture_output=True, text=True, timeout=15)
if r.returncode == 0:
    log("IMPORT: prescriptions_htmx", "PASS", r.stdout.strip()[:100])
    routes = r.stdout.strip()
else:
    log("IMPORT: prescriptions_htmx", "FAIL", r.stderr.strip()[:200])
    routes = ""

expected = ["/job/{job_id}", "/{prescription_id}/status", "/badge/{job_id}"]
for exp in expected:
    found = exp in routes
    log(f"ROUTE: {exp}", "PASS" if found else "FAIL")

print("\nPHASE 4: HTML CONTENT")
with open(EC + r"\app\routers\prescriptions_htmx.py") as f:
    src = f.read()
    checks = [
        ("Apply button", "Apply" in src),
        ("Reject button", "Reject" in src),
        ("In Progress button", "In Progress" in src),
        ("hx-patch", "hx-patch" in src),
        ("savings display", "estimated_savings" in src),
        ("badge function", "_badge_html" in src),
        ("card function", "_card_html" in src),
    ]
    for name, ok in checks:
        log(f"HTML: {name}", "PASS" if ok else "FAIL")

print("\nPHASE 5: MAIN.PY WIRING")
with open(EC + r"\app\main.py") as f:
    has_import = "prescriptions_htmx" in f.read()
log("WIRING: main.py import", "PASS" if has_import else "FAIL")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed}")

if failed == 0:
    print("\n  P5 HTMX JOB PAGE — FULLY VERIFIED")
else:
    for r in results:
        if r["status"] == "FAIL":
            print(f"    - {r['stage']}: {r['detail']}")

json.dump({"results": results, "passed": passed, "failed": failed},
          open(BIO + r"\p5_verify_report.json", "w"), indent=2)
print(f"\n  Report: {BIO}\\p5_verify_report.json")
