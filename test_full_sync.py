"""Live sync test: start Bio-ERP + EventCore, test all endpoints + sync"""
import subprocess, time, httpx, sys, os

BASE = "D:/ERP System/BIO_ERP"
EC = "D:/EventCore_ERP"
os.chdir(BASE)
os.environ["BIO_ERP_BRIDGE_TOKEN"] = "ec-bridge-token-dev"

procs = []

def start_server(cwd, mod, port, label):
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", mod, "--host", "0.0.0.0", "--port", str(port)],
        cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    procs.append(p)
    for i in range(20):
        time.sleep(1)
        try:
            r = httpx.get(f"http://localhost:{port}/api/v1/health", timeout=2)
            if r.status_code == 200:
                print(f"[{label}] Started on port {port}")
                return
        except:
            pass
    print(f"[{label}] FAILED to start")

print("Starting Bio-ERP...")
start_server(BASE, "app.main:app", 8000, "Bio-ERP")

print("Starting EventCore...")
start_server(EC, "backend.app.main:app", 8001, "EventCore")

try:
    # 1. Bio-ERP health
    r = httpx.get("http://localhost:8000/health", timeout=5)
    print(f"\n[1] Bio-ERP: {r.status_code} {r.json()['status']} v{r.json()['version']}")

    # 2. Bio-ERP root (linked systems)
    r = httpx.get("http://localhost:8000/", timeout=5)
    print(f"[2] Systems: {len(r.json()['linked_systems'])} linked")

    # 3. SCM health
    r = httpx.get("http://localhost:8000/api/v1/scm/health", timeout=5)
    j = r.json()
    print(f"[3] SCM: {j['status']} engines={len(j['engines_ready'])}")

    # 4. SCM TDABC via mount
    r = httpx.post("http://localhost:8000/api/v1/scm/tdabc/calculate-pool", json={
        "name": "Live Test", "total_cost": 500000.0, "resources_count": 10, "efficiency_pct": 85.0
    }, timeout=5)
    print(f"[4] SCM TDABC: practical={r.json().get('practical_minutes')}")

    # 5. SCM ROI/EVA via mount
    r = httpx.post("http://localhost:8000/api/v1/scm/roi-eva/analyze", json={
        "baseline": {"investment_name": "Expansion", "initial_investment": 1000000.0,
                     "operating_profit": 200000.0, "total_assets": 5000000.0,
                     "current_liabilities": 1000000.0},
        "calculation": {"nopat": 180000.0, "wacc_pct": 10.0}
    }, timeout=5)
    print(f"[5] SCM ROI/EVA: eva={r.json()['eva']} roi={r.json()['roi_pct']}%")

    # 6. OR health
    r = httpx.get("http://localhost:8000/api/v1/or/health", timeout=5)
    print(f"[6] OR: {r.status_code} {r.json()['status']}")

    # 7. OR Decision Analysis via mount
    r = httpx.post("http://localhost:8000/api/v1/or/decision-analysis", json={
        "model_name": "Test", "states": [{"id": "s1", "name": "Good", "probability": 0.6}],
        "alternatives": [{"id": "a1", "name": "A", "payoffs": {"s1": 100}}],
        "criterion": "emv"
    }, timeout=5)
    print(f"[7] OR Decision: {r.status_code} success={r.json().get('success')}")

    # 8. EventCore health
    r = httpx.get("http://localhost:8001/api/v1/health", timeout=5)
    print(f"[8] EventCore: {r.status_code} {r.json()['status']}")

    # 9. EventCore exclusions
    r = httpx.get("http://localhost:8001/api/v1/bio-sync/exclusions", timeout=5)
    j = r.json() if r.status_code == 200 else {"sync_ready_rows": "ERROR", "permanent_gaps": []}
    print(f"[9] Exclusions: ready={j.get('sync_ready_rows')} gaps={len(j.get('permanent_gaps', []))}")

    # 10. LIVE SYNC: EventCore -> Bio-ERP
    print("\n--- LIVE SYNC: EventCore -> Bio-ERP ---")
    r = httpx.post("http://localhost:8001/api/v1/bio-sync/push-all", timeout=30)
    if r.status_code == 200:
        j = r.json()
        print(f"[10] Sync OK: batch={j.get('batch_id')}")
        for res in j.get("results", []):
            icon = "✓" if res.get("accepted", 0) > 0 else "○"
            print(f"     {icon} {res['entity']}: sent={res['sent']} accepted={res['accepted']} rejected={res['rejected']}")
    else:
        print(f"[10] Sync: {r.status_code} {r.text[:300]}")

    print("\n=== FULL INTEGRATION TEST COMPLETE ===")

finally:
    for p in procs:
        p.terminate()
    print("Servers terminated.")
