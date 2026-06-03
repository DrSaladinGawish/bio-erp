"""Full smoke test for IncentiveHouse ERP"""
import urllib.request, json, sys

BASE = "http://127.0.0.1:8003"
PASS = "pemCzLvBpBHYEYoRCpIq"
errors = []
ok_count = 0

def test(label, method, path, expect, data=None, headers=None, expect_json=True):
    global ok_count
    url = BASE + path
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        status = r.status
        body = r.read()
        resp = json.loads(body) if expect_json else body.decode()
    except urllib.error.HTTPError as e:
        status = e.code
        resp = json.loads(e.read()) if expect_json else e.read().decode()
    except Exception as e:
        errors.append(f"[FAIL] {label}: {e}")
        return None
    ok = status == expect
    if ok:
        ok_count += 1
        print(f"  [OK] {label} ({status})")
    else:
        errors.append(f"[FAIL] {label}: expected {expect}, got {status} — {str(resp)[:100]}")
    return resp

# ── 1. Health ──
test("Health", "GET", "/health", 200)

# ── 2. Auth ──
r = test("Login (correct)", "POST", "/api/v1/incentivehouse/auth/login", 200,
         {"username": "admin", "password": PASS})
token = r.get("access_token") if r else None
if token:
    print(f"  Token: {token[:30]}...")
else:
    errors.append("[FAIL] No access_token")

auth = {"Authorization": f"Bearer {token}"} if token else {}

test("Login (wrong pass)", "POST", "/api/v1/incentivehouse/auth/login", 401,
     {"username": "admin", "password": "wrong"})
test("Login (wrong user)", "POST", "/api/v1/incentivehouse/auth/login", 401,
     {"username": "nobody", "password": PASS})
test("Me (valid)", "GET", "/api/v1/incentivehouse/auth/me", 200, headers=auth)
test("Me (no token)", "GET", "/api/v1/incentivehouse/auth/me", 401)
test("Me (bad token)", "GET", "/api/v1/incentivehouse/auth/me", 401,
     headers={"Authorization": "Bearer invalid"})

# ── 3. IncentiveHouse endpoints ──
test("IH root", "GET", "/api/v1/incentivehouse/", 200, headers=auth, expect_json=False)
test("Dashboard", "GET", "/api/v1/incentivehouse/dashboard", 200, headers=auth)
test("Dashboard (no auth)", "GET", "/api/v1/incentivehouse/dashboard", 401)

# ── 4. Module routers (now available via top-level app) ──
test("BNK transactions", "GET", "/api/v1/bnk/transactions?limit=3", 200, headers=auth)
test("BNK accounts", "GET", "/api/v1/bnk/accounts", 200, headers=auth)
test("BNK summary", "GET", "/api/v1/bnk/summary", 200, headers=auth)
test("SAL root", "GET", "/api/v1/sal/", 200, headers=auth)
test("PUR root", "GET", "/api/v1/pur/", 200, headers=auth)
test("ENV clients", "GET", "/api/v1/env/clients?limit=3", 200, headers=auth)
test("ENV vendors", "GET", "/api/v1/env/vendors?limit=3", 200, headers=auth)
test("ENV cost-centers", "GET", "/api/v1/env/cost-centers?limit=3", 200, headers=auth)
test("ENV staff", "GET", "/api/v1/env/staff?limit=3", 200, headers=auth)
test("EVN events", "GET", "/api/v1/evn/events?limit=3", 200, headers=auth)

# ── 5. Login page HTML ──
test("Login page", "GET", "/api/v1/incentivehouse/login", 200, expect_json=False)

print(f"\n=== RESULTS: {ok_count} OK, {len(errors)} FAILURES ===")
for e in errors:
    print(f"  {e}")
print(f"\nLogin URL:  {BASE}/api/v1/incentivehouse/login")
print(f"Credentials: admin / {PASS}")

sys.exit(1 if errors else 0)
