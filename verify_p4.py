#!/usr/bin/env python3
"""
P4 — Auto-Trigger Engine Verification Script
Tests: webhook endpoint, OR engines, prescription push
"""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
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

print("=" * 60)
print("  P4 AUTO-TRIGGER — VERIFICATION REPORT")
print("=" * 60)

# 1. auto_trigger.py syntax
try:
    from app.organs.or_organ.auto_trigger import AutoTriggerEngine
    check("auto_trigger.py import", True, f"AutoTriggerEngine OK")
except Exception as e:
    check("auto_trigger.py import", False, str(e))

# 2. job_or_bridge.py import
try:
    from app.organs.or_organ.job_or_bridge import EventORBridge
    check("job_or_bridge.py import", True, f"EventORBridge OK")
except Exception as e:
    check("job_or_bridge.py import", False, str(e))

# 3. eventcore_webhook.py routes
try:
    from app.organs.or_organ.eventcore_webhook import router
    routes = [(r.path, list(r.methods)) for r in router.routes]
    check("eventcore_webhook.py routes", True, f"Routes: {routes}")
except Exception as e:
    check("eventcore_webhook.py routes", False, str(e))

# 4. Health endpoint
try:
    req = urllib.request.Request(f"{BASE}/api/v1/or/auto-trigger/health")
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    ok = data.get("status") == "active"
    check("GET /auto-trigger/health", ok, json.dumps(data))
except Exception as e:
    check("GET /auto-trigger/health", False, str(e))

# 5. POST /auto-trigger/job
try:
    body = json.dumps({"job_id": 999999, "title": "Verify Test", "client_id": 1}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/or/auto-trigger/job",
        data=body,
        headers={"X-Bridge-Token": TOKEN, "Content-Type": "application/json"},
        method="POST"
    )
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=30)
    elapsed = time.time() - t0
    data = json.loads(resp.read())
    ok = data.get("status") == "completed"
    check("POST /auto-trigger/job", ok, f"status={data.get('status')}, elapsed={elapsed:.2f}s")
    check("Prescriptions pushed count", data.get("prescriptions_pushed", -1) >= 0,
          f"pushed={data.get('prescriptions_pushed')}")
except Exception as e:
    check("POST /auto-trigger/job", False, str(e))

# 6. 403 for bad token
try:
    body = json.dumps({"job_id": 1, "title": "x"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/or/auto-trigger/job",
        data=body,
        headers={"X-Bridge-Token": "wrong-token", "Content-Type": "application/json"},
        method="POST"
    )
    urllib.request.urlopen(req, timeout=5)
    check("Auth: bad token rejected", False, "Should have been 403")
except urllib.error.HTTPError as e:
    check("Auth: bad token rejected", e.code == 403, f"Got {e.code} as expected")
except Exception as e:
    check("Auth: bad token rejected", False, str(e))

print("-" * 60)
print(f"  TOTAL: {PASS} passed, {FAIL} failed")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
