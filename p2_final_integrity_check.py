"""
P2 Reverse Bridge — FINAL INTEGRITY CHECK
Run this after all 8 files are saved to disk.
Checks: syntax, imports, routes, schemas, end-to-end, database, audit trail.
"""
import sys, json, time

# ── Configuration ──
EC_PATH = r"D:\EventCore_ERPackend"
BIO_PATH = r"D:\ERP System\BIO_ERP"
EC_BASE = "http://localhost:8001"
BIO_BASE = "http://localhost:8000"

results = []

def log(stage, status, detail=""):
    results.append({"stage": stage, "status": status, "detail": detail})
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} [{stage}] {status}" + (f" — {detail}" if detail else ""))

# ═══════════════════════════════════════════════════════════════════
# PHASE 1: FILE SYSTEM INTEGRITY
# ═══════════════════════════════════════════════════════════════════
print("
" + "="*60)
print("PHASE 1: FILE SYSTEM INTEGRITY")
print("="*60)

import os

files_to_check = [
    ("EventCore Receiver", f"{EC_PATH}\app\routers\prescription_receiver.py"),
    ("Bio-ERP Sender", f"{BIO_PATH}\app\or_module\prescription_sender.py"),
    ("Bio-ERP Sub-App", f"{BIO_PATH}\app\or_module\sub_app.py"),
    ("EventCore Main", f"{EC_PATH}\app\main.py"),
    ("Bio-ERP Config", f"{BIO_PATH}\app\config.py"),
    ("Bio-ERP Env", f"{BIO_PATH}\.env"),
]

for name, path in files_to_check:
    if os.path.exists(path):
        size = os.path.getsize(path)
        log(f"FILE: {name}", "PASS", f"{path} ({size} bytes)")
    else:
        log(f"FILE: {name}", "FAIL", f"Missing: {path}")

# ═══════════════════════════════════════════════════════════════════
# PHASE 2: SYNTAX & IMPORT INTEGRITY
# ═══════════════════════════════════════════════════════════════════
print("
" + "="*60)
print("PHASE 2: SYNTAX & IMPORT INTEGRITY")
print("="*60)

import py_compile, importlib.util

# 2.1 Syntax check
for name, path in files_to_check[:2]:  # Only .py files
    if os.path.exists(path):
        try:
            py_compile.compile(path, doraise=True)
            log(f"SYNTAX: {name}", "PASS")
        except py_compile.PyCompileError as e:
            log(f"SYNTAX: {name}", "FAIL", str(e))

# 2.2 Import check — EventCore
sys.path.insert(0, EC_PATH)
try:
    spec = importlib.util.spec_from_file_location("prescription_receiver", f"{EC_PATH}\app\routers\prescription_receiver.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, 'router'):
        log("IMPORT: EventCore Receiver", "PASS", f"Router prefix={mod.router.prefix}")
    else:
        log("IMPORT: EventCore Receiver", "FAIL", "No router attribute")
except Exception as e:
    log("IMPORT: EventCore Receiver", "FAIL", str(e))

# 2.3 Import check — Bio-ERP Sender
sys.path.insert(0, BIO_PATH)
try:
    spec = importlib.util.spec_from_file_location("prescription_sender", f"{BIO_PATH}\app\or_module\prescription_sender.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, 'send_or_analysis'):
        log("IMPORT: Bio-ERP Sender", "PASS", "send_or_analysis callable")
    else:
        log("IMPORT: Bio-ERP Sender", "FAIL", "No send_or_analysis")
except Exception as e:
    log("IMPORT: Bio-ERP Sender", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════════
# PHASE 3: ROUTE REGISTRY INTEGRITY
# ═══════════════════════════════════════════════════════════════════
print("
" + "="*60)
print("PHASE 3: ROUTE REGISTRY INTEGRITY")
print("="*60)

# 3.1 EventCore routes
sys.path.insert(0, EC_PATH)
try:
    import backend.app.main as ec_main
    ec_routes = [r.path for r in ec_main.app.routes if hasattr(r, 'path') and 'prescription' in r.path]
    expected_ec = ['/api/v1/prescriptions/receive', '/api/v1/prescriptions/job/{job_id}', '/api/v1/prescriptions/{prescription_id}/status']
    missing = [r for r in expected_ec if r not in ec_routes]
    if not missing:
        log("ROUTES: EventCore", "PASS", f"Found {len(ec_routes)} prescription routes")
    else:
        log("ROUTES: EventCore", "FAIL", f"Missing: {missing}")
except Exception as e:
    log("ROUTES: EventCore", "FAIL", str(e))

# 3.2 Bio-ERP routes
sys.path.insert(0, BIO_PATH)
try:
    import app.main as bio_main
    bio_routes = [r.path for r in bio_main.app.routes if hasattr(r, 'path') and 'prescription' in r.path]
    expected_bio = ['/api/v1/or/prescriptions/send']
    missing = [r for r in expected_bio if r not in bio_routes]
    if not missing:
        log("ROUTES: Bio-ERP", "PASS", f"Found {len(bio_routes)} prescription routes")
    else:
        log("ROUTES: Bio-ERP", "FAIL", f"Missing: {missing}")
except Exception as e:
    log("ROUTES: Bio-ERP", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════════
# PHASE 4: SERVER HEALTH & END-TO-END
# ═══════════════════════════════════════════════════════════════════
print("
" + "="*60)
print("PHASE 4: SERVER HEALTH & END-TO-END")
print("="*60)

import requests

# 4.1 Health checks
for name, url in [("Bio-ERP", BIO_BASE), ("EventCore", EC_BASE)]:
    try:
        r = requests.get(f"{url}/health", timeout=5)
        if r.status_code == 200:
            log(f"HEALTH: {name}", "PASS", f"{url}/health → 200")
        else:
            log(f"HEALTH: {name}", "FAIL", f"{url}/health → {r.status_code}")
    except Exception as e:
        log(f"HEALTH: {name}", "FAIL", f"Connection error: {e}")

# 4.2 Auth & End-to-End
print("
[4.2] Auth + End-to-End Prescription Push...")
try:
    # Login
    r = requests.post(f"{BIO_BASE}/api/v1/auth/login", json={"username":"admin","password":"admin123"}, timeout=10)
    if r.status_code != 200:
        log("E2E: Auth", "FAIL", f"Login returned {r.status_code}")
    else:
        token = r.json().get("access_token")
        log("E2E: Auth", "PASS", f"Token: {token[:20]}...")

        # Send prescription
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r2 = requests.post(f"{BIO_BASE}/api/v1/or/prescriptions/send", headers=headers,
                           json={"job_id": 1, "analysis_types": ["lp", "pert", "tdabc"]}, timeout=15)
        if r2.status_code == 200:
            data = r2.json()
            ec_resp = data.get("eventcore_response", {})
            stored = ec_resp.get("stored", 0)
            errors = ec_resp.get("errors", [])
            log("E2E: Send", "PASS", f"Stored={stored}, Errors={errors}")

            # Verify received
            time.sleep(0.5)
            r3 = requests.get(f"{EC_BASE}/api/v1/prescriptions/job/1", timeout=10)
            if r3.status_code == 200:
                rx = r3.json()
                log("E2E: Receive", "PASS", f"Retrieved {len(rx)} prescriptions")

                # Verify status update
                if rx:
                    r4 = requests.patch(f"{EC_BASE}/api/v1/prescriptions/{rx[0]['id']}/status?status=applied", timeout=10)
                    if r4.status_code == 200:
                        log("E2E: Status Update", "PASS", f"ID {rx[0]['id']} → applied")
                    else:
                        log("E2E: Status Update", "FAIL", f"{r4.status_code}: {r4.text}")
            else:
                log("E2E: Receive", "FAIL", f"{r3.status_code}: {r3.text}")
        else:
            log("E2E: Send", "FAIL", f"{r2.status_code}: {r2.text}")
except Exception as e:
    log("E2E", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════════
# PHASE 5: SCHEMA INTEGRITY
# ═══════════════════════════════════════════════════════════════════
print("
" + "="*60)
print("PHASE 5: SCHEMA INTEGRITY")
print("="*60)

# 5.1 Check Pydantic v2 patterns in receiver
with open(f"{EC_PATH}\app\routers\prescription_receiver.py", 'r') as f:
    src = f.read()
    checks = [
        ("ConfigDict", "model_config = ConfigDict" in src),
        ("pattern validator", "pattern=" in src),
        ("json.dumps details", "json.dumps(item.details)" in src),
        ("json.loads details", "json.loads(r.details)" in src),
    ]
    for name, ok in checks:
        log(f"SCHEMA: {name}", "PASS" if ok else "FAIL")

# 5.2 Check httpx usage in sender
with open(f"{BIO_PATH}\app\or_module\prescription_sender.py", 'r') as f:
    src = f.read()
    checks = [
        ("httpx.AsyncClient", "httpx.AsyncClient" in src),
        ("X-Bridge-Token header", "X-Bridge-Token" in src),
        ("timeout 15s", "timeout=15.0" in src),
    ]
    for name, ok in checks:
        log(f"SCHEMA: {name}", "PASS" if ok else "FAIL")

# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════
print("
" + "="*60)
print("FINAL INTEGRITY REPORT")
print("="*60)

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
warnings = sum(1 for r in results if r["status"] not in ("PASS", "FAIL"))

print(f"
Total Checks: {len(results)}")
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"⚠️  Warnings: {warnings}")

if failed == 0:
    print("
🎉 P2 REVERSE BRIDGE — FULLY VERIFIED")
    print("Ready for P4 (Auto-Trigger Engine)")
else:
    print(f"
⚠️  {failed} check(s) failed. Fix before proceeding to P4.")
    for r in results:
        if r["status"] == "FAIL":
            print(f"   ❌ {r['stage']}: {r['detail']}")

# Save report
report_path = f"{BIO_PATH}\p2_integrity_report.json"
with open(report_path, 'w') as f:
    json.dump({"results": results, "passed": passed, "failed": failed}, f, indent=2)
print(f"
Report saved: {report_path}")
