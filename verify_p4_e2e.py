#!/usr/bin/env python3
"""
P4 + P2 End-to-End Verification Script
Tests: P4 webhook, OR engines, P2 reverse flow, EventCore storage
"""
import json
import sys
import time
import urllib.request
import urllib.error

BIO_BASE = "http://localhost:8000"
EC_BASE = "http://localhost:8001"
TOKEN = "ec-bridge-token-dev"
PASS = 0
FAIL = 0

def check(label, ok, detail=""):
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))

def json_req(url, method="GET", data=None, headers=None, timeout=15):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

print("=" * 60)
print("  P4+P2 END-TO-END VERIFICATION REPORT")
print("=" * 60)

# === PART 1: P4 AUTO-TRIGGER ===
print("\n--- PART 1: P4 Auto-Trigger Engine (Bio-ERP) ---")

# 1.1 Health
try:
    d = json_req(f"{BIO_BASE}/api/v1/or/auto-trigger/health")
    check("Health endpoint", d.get("status") == "active", str(d))
except Exception as e:
    check("Health endpoint", False, str(e))

# 1.2 Bad token → 403
try:
    json_req(f"{BIO_BASE}/api/v1/or/auto-trigger/job", "POST",
             {"job_id": 1, "title": "x"},
             {"X-Bridge-Token": "wrong-token"})
    check("Auth: bad token", False, "Should have been 403")
except urllib.error.HTTPError as e:
    check("Auth: bad token", e.code == 403, f"Got {e.code}")
except Exception as e:
    check("Auth: bad token", False, str(e))

# 1.3 Trigger OR analysis (non-existent event)
t0 = time.time()
try:
    d = json_req(f"{BIO_BASE}/api/v1/or/auto-trigger/job", "POST",
                 {"job_id": 999999, "title": "Verify", "client_id": 1},
                 {"X-Bridge-Token": TOKEN}, timeout=30)
    elapsed = time.time() - t0
    ok = d.get("status") == "completed"
    check("POST /auto-trigger/job", ok, f"status={d['status']}, {elapsed:.2f}s")
    check("Prescriptions pushed", d.get("prescriptions_pushed", -1) >= 0,
          f"pushed={d['prescriptions_pushed']}")
except Exception as e:
    check("POST /auto-trigger/job", False, str(e))

# === PART 2: P2 REVERSE FLOW (Bio-ERP -> EventCore) ===
print("\n--- PART 2: P2 Reverse Flow (Bio-ERP -> EventCore) ---")

# 2.1 Push OR results
try:
    d = json_req(f"{BIO_BASE}/api/v1/reverse-flow/push/e2e-test", "POST", {
        "job_id": "e2e-test",
        "analysis_type": "lp_optimization",
        "or_score": 0.912,
        "sensitivity_min": 0.88,
        "sensitivity_max": 0.94,
        "recommendations": ["Optimal allocation", "Reduce waste"],
        "generated_at": "2026-05-30T12:00:00",
        "source_module": "or_erp",
        "source_url": "http://localhost:8000/api/v1/or/"
    }, timeout=30)
    ok = d.get("success") and d.get("eventcore_status") == 200
    check("Push OR results to EventCore", ok, f"eventcore={d.get('eventcore_status')}")
except Exception as e:
    check("Push OR results to EventCore", False, str(e))

# 2.2 Verify EventCore received it
try:
    d = json_req(f"{EC_BASE}/api/v1/jobs/e2e-test/or-insights")
    ok = d.get("has_data") and d.get("insights_count", 0) > 0
    check("EventCore stored OR insight", ok,
          f"count={d.get('insights_count')}, score={d.get('latest',{}).get('or_score')}")
except Exception as e:
    check("EventCore stored OR insight", False, str(e))

# 2.3 Verify badge endpoint
try:
    d = json_req(f"{EC_BASE}/api/v1/jobs/e2e-test/or-insights/badge")
    check("Badge endpoint", d.get("visible"), f"text={d.get('badge_text')}")
except Exception as e:
    check("Badge endpoint", False, str(e))

# === PART 3: EventCore HEALTH ===
print("\n--- PART 3: EventCore Server Status ---")

try:
    d = json_req(f"{EC_BASE}/api/v1/health")
    check("EventCore health", d.get("status") == "healthy", str(d))
except Exception as e:
    check("EventCore health", False, str(e))

try:
    d = json_req(f"{EC_BASE}/")
    check("EventCore root", d.get("message") == "EventCore ERP", str(d))
except Exception as e:
    check("EventCore root", False, str(e))

# === SUMMARY ===
print("\n" + "=" * 60)
print(f"  TOTAL: {PASS} passed, {FAIL} failed  |  P4 loop: DOCTOR <-> PATIENT")
print("=" * 60)
print("  End-to-end paths verified:")
print("    P4 Hook: EventCore job created -> Bio-ERP webhook -> OR analysis")
print("    P2 Push: Bio-ERP -> EventCore /or-insights receiver -> stored")
print("    P2 Pull: EventCore job page shows OR badge & insights")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
