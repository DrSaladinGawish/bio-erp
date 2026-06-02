"""Verify v2.2 server: UI pages + full protocol with real data."""
import subprocess, sys, time, json, urllib.request, urllib.error, os

SERVER_DIR = r"D:\ERP System\BIO_ERP\app\organs\incentivehouse_organ"
os.chdir(SERVER_DIR)

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "incentivehouse_server:app",
     "--host", "127.0.0.1", "--port", "9001", "--log-level", "warning"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(5)

def req(method, path, body=None, token=None):
    url = "http://127.0.0.1:9001" + path
    if token:
        url += "?token=" + token
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def req_text(method, path, body=None):
    url = "http://127.0.0.1:9001" + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r)
        return resp.read().decode()
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:200]}"

results = []

# === UI PAGES ===
ui_tests = [
    ("Dashboard", "GET", "/"),
    ("Event Form", "GET", "/api/v1/incentivehouse/events/new"),
    ("Recon Form", "GET", "/api/v1/incentivehouse/recon/form"),
    ("Swagger", "GET", "/docs"),
]
for name, method, path in ui_tests:
    try:
        resp_text = req_text(method, path)
        ok = "HTTP" not in resp_text[:6] and len(resp_text) > 100
        results.append((name, f"{method} {path}", "200" if ok else "FAIL", f"{len(resp_text)} bytes"))
        print(f"{name}: {'OK' if ok else 'FAIL'} ({len(resp_text)} bytes)")
    except Exception as e:
        results.append((name, f"{method} {path}", "FAIL", str(e)))
        print(f"{name}: FAIL - {e}")

# === API ENDPOINTS ===
h = req("GET", "/health")
ok = h.get("status") == "HEALTHY"
results.append(("Health", "GET /health", "200" if ok else "FAIL", h.get("status")))
print(f"HEALTH: {h.get('status')}")

a = req("POST", "/v2/auth/login", {"username": "admin", "password": "admin123"})
token = a.get("access_token", "")
ok = bool(token)
results.append(("0 Auth", "POST /v2/auth/login", "200" if ok else "FAIL", "token+" + a.get("role","?")))
print(f"AUTH: token={token[:25]}... role={a.get('role')}")

m = req("POST", "/v2/extract/master", {"source_file": "Data_Base_Mtbls.xlsx"}, token=token)
m_ok = m.get("status") in ("SUCCESS", "PARTIAL")
m_recs = m.get("records_inserted", 0)
results.append(("1b Master", "POST /v2/extract/master", "200" if m_ok else "FAIL", f"{m_recs} records"))
print(f"MASTER: status={m.get('status')} tables={m.get('tables_processed')} records={m_recs}")
for e in (m.get("errors") or [])[:3]:
    print(f"  ERR: {e}")

e1 = req("POST", "/v2/extract", {"module":"BNK","source_file":"Bnk_TRNX SOURCE.xlsx","dry_run":False}, token=token)
e1_ok = e1.get("status") in ("SUCCESS", "PARTIAL")
e1_recs = e1.get("records_extracted") or e1.get("records_inserted") or e1.get("records_read") or 0
results.append(("1 Extract", "POST /v2/extract BNK", "200" if e1_ok else "FAIL", f"{e1_recs} records"))
print(f"EXTRACT BNK: status={e1.get('status')} response={json.dumps(e1, indent=2)[:300]}")
eid = e1.get("extract_id", 1)

v = req("POST", "/v2/validate", {"extract_id": eid}, token=token)
v_ok = v.get("status") == "SUCCESS"
vs = v.get("quality_score") or v.get("passed_records")
results.append(("2 Validate", "POST /v2/validate", "200" if v_ok else "FAIL", f"qscore={v.get('quality_score')}"))
print(f"VALIDATE: status={v.get('status')} response={json.dumps(v, indent=2)[:200]}")
vid = v.get("validate_id", 1)

s = req("POST", "/v2/stage", {"validate_id": vid, "target_table": "bnk_staging"}, token=token)
s_ok = s.get("status") == "SUCCESS"
results.append(("3 Stage", "POST /v2/stage", "200" if s_ok else "FAIL", f"snap={s.get('snapshot_id','')[:20]}"))
print(f"STAGE: status={s.get('status')}")
sid = s.get("stage_id", 1)

rc = req("POST", "/v2/reconcile", {"stage_id": sid, "module": "BNK"}, token=token)
rc_ok = rc.get("status") == "SUCCESS"
rc_id = rc.get("recon_id") or rc.get("reconcile_id") or 1
results.append(("4 Reconcile", "POST /v2/reconcile", "200" if rc_ok else "FAIL", f"rid={rc_id}"))
print(f"RECONCILE: status={rc.get('status')} response={json.dumps(rc, indent=2)[:200]}")
rid = rc_id

ap = req("POST", "/v2/approve", {"recon_id": rid, "approval_level": "auto"}, token=token)
ap_ok = ap.get("status") == "SUCCESS"
results.append(("5 Approve", "POST /v2/approve", "200" if ap_ok else "FAIL", f"auto={ap.get('auto_approved')}"))
print(f"APPROVE: status={ap.get('status')}")
aid = ap.get("approve_id", 1)

pr = req("POST", "/v2/promote", {"approve_id": aid}, token=token)
pr_ok = pr.get("status") == "SUCCESS"
results.append(("6 Promote", "POST /v2/promote", "200" if pr_ok else "FAIL", f"rb={pr.get('rollback_token','')[:25]}"))
print(f"PROMOTE: status={pr.get('status')}")
pid = pr.get("promote_id", 1)

ob = req("POST", "/v2/observe", {"promote_id": pid}, token=token)
ob_ok = ob.get("status") == "SUCCESS"
results.append(("7 Observe", "POST /v2/observe", "200" if ob_ok else "FAIL", f"alerts={ob.get('alert_count')}"))
print(f"OBSERVE: status={ob.get('status')}")

st = req("GET", "/v2/status", token=token)
counts = st.get("records") or st.get("table_counts") or {}
st_ok = bool(counts)
total_recs = sum(v for v in counts.values() if isinstance(v, (int, float)))
results.append(("Status", "GET /v2/status", "200" if st_ok else "FAIL", f"{total_recs} total"))
print(f"\nSTATUS: {len(counts)} tables, {total_recs} total records")
for t, c in sorted(counts.items()):
    if isinstance(c, (int, float)) and c > 0:
        print(f"  {t}: {c}")

# Recon API
rcs = req("GET", "/recon/status", token=token)
rcs_ok = bool(rcs)
results.append(("Recon Status", "GET /recon/status", "200" if rcs_ok else "FAIL", f"{len(rcs)} keys"))
print(f"RECON STATUS: {list(rcs.keys())[:5] if isinstance(rcs,dict) else 'ok'}")

print("\n=== RESULTS ===")
print(f"{'Component':<20} {'Endpoint':<40} {'Status':<8} Details")
print("-" * 75)
for name, endpoint, status, details in results:
    print(f"{name:<20} {endpoint:<40} {status:<8} {details}")

server.terminate()
server.wait(timeout=5)
print("\n=== v2.2 VERIFICATION COMPLETE ===")
