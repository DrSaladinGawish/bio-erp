"""Full integration test: Bio-ERP + EventCore + SCM + live sync"""
import subprocess, time, sys, json as _json, urllib.request, urllib.error

def http(url, method="GET", data=None, timeout=10):
    body = _json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    r = urllib.request.urlopen(req, timeout=timeout)
    return r.status, _json.loads(r.read().decode())

# Start Bio-ERP
p1 = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd="D:/ERP System/BIO_ERP", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(4)

# Start EventCore (from its own directory to avoid env conflicts)
p2 = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd="D:/EventCore_ERP", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(4)

results = []

try:
    # 1. Bio-ERP health
    s, j = http("http://localhost:8000/health")
    results.append(("Bio-ERP health", f"{s} {j['status']} v{j['version']} db={j['database']}"))

    # 2. Linked systems
    s, j = http("http://localhost:8000/")
    results.append(("Linked systems", f"{len(j['linked_systems'])}"))

    # 3. SCM health
    s, j = http("http://localhost:8000/api/v1/scm/health")
    results.append(("SCM health", f"{j['status']} engines={len(j['engines_ready'])}"))

    # 4. SCM TDABC
    s, j = http("http://localhost:8000/api/v1/scm/tdabc/calculate-pool", "POST",
                {"name":"Test","total_cost":500000,"resources_count":10,"efficiency_pct":85})
    results.append(("SCM TDABC", f"practical={j['practical_minutes']}"))

    # 5. SCM ROI/EVA
    s, j = http("http://localhost:8000/api/v1/scm/roi-eva/analyze", "POST", {
        "baseline": {"investment_name":"E","initial_investment":1000000,"operating_profit":200000,
                     "total_assets":5000000,"current_liabilities":1000000},
        "calculation": {"nopat":180000,"wacc_pct":10}
    })
    results.append(("SCM ROI/EVA", f"eva={j['eva']} roi={j['roi_pct']}%"))

    # 6. OR health
    s, j = http("http://localhost:8000/api/v1/or/health")
    results.append(("OR health", f"{s} {j['status']}"))

    # 7. OR Decision Analysis
    s, j = http("http://localhost:8000/api/v1/or/decision-analysis", "POST", {
        "model_name":"Test","states":[{"id":"s1","name":"Good","probability":0.6}],
        "alternatives":[{"id":"a1","name":"A","payoffs":{"s1":100}}],"criterion":"emv"
    })
    results.append(("OR Decision", f"success={j.get('success')}"))

    # 8. EventCore health
    s, j = http("http://localhost:8001/api/v1/health")
    results.append(("EventCore", f"{s} {j['status']}"))

    # 9. EventCore exclusions
    try:
        s, j = http("http://localhost:8001/api/v1/bio-sync/exclusions")
        results.append(("Exclusions", f"OK gaps={len(j.get('permanent_gaps',[]))}"))
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        results.append(("Exclusions", f"HTTP {e.code}: {body}"))

    # 10. LIVE SYNC
    print("\n--- LIVE SYNC ---")
    try:
        req = urllib.request.Request(
            "http://localhost:8001/api/v1/bio-sync/push-all",
            data=_json.dumps({}).encode(), method="POST"
        )
        req.add_header("Content-Type", "application/json")
        r = urllib.request.urlopen(req, timeout=30)
        j = _json.loads(r.read().decode())
        for res in j.get("results", []):
            print(f"  {res['entity']}: sent={res['sent']} acc={res['accepted']} rej={res['rejected']}")
        results.append(("LIVE SYNC", f"batch={j.get('batch_id')} online={j.get('bio_erp_online')}"))
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        results.append(("LIVE SYNC", f"HTTP {e.code}: {body}"))

    # Summary
    print("\n=== INTEGRATION TEST RESULTS ===")
    for name, val in results:
        is_ok = not val.startswith("HTTP 4") and "ERROR" not in str(val).upper()
        print(f"  [{'OK' if is_ok else 'FAIL'}] {name}: {val}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
finally:
    p1.terminate()
    p2.terminate()
    print("\nServers terminated.")
