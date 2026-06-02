"""Live sync test: start servers, test endpoints, verify SCM + bridge"""
import subprocess, time, httpx, sys, os
from pathlib import Path

BASE = Path("D:/ERP System/BIO_ERP")
EC_BASE = Path("D:/EventCore_ERP")

# Start Bio-ERP
print("Starting Bio-ERP...")
bio_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=str(BASE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(10)

try:
    # 1. Bio-ERP health
    r = httpx.get("http://localhost:8000/health", timeout=5)
    print(f"[1] Bio-ERP health: {r.status_code} {r.json()['status']}")

    # 2. SCM health
    r = httpx.get("http://localhost:8000/api/v1/scm/health", timeout=5)
    print(f"[2] SCM health: {r.status_code} {r.json()['status']} engines={len(r.json()['engines_ready'])}")

    # 3. OR health
    r = httpx.get("http://localhost:8000/api/v1/or/health", timeout=5)
    print(f"[3] OR health: {r.status_code} {r.json()['status']}")

    # 4. SCM TDABC via mount
    r = httpx.post("http://localhost:8000/api/v1/scm/tdabc/calculate-pool", json={
        "name": "Live Test Pool", "total_cost": 500000.0,
        "resources_count": 10, "efficiency_pct": 85.0
    }, timeout=5)
    print(f"[4] SCM TDABC: {r.status_code} practical={r.json().get('practical_minutes')}")

    # 5. SCM ROI/EVA via mount
    r = httpx.post("http://localhost:8000/api/v1/scm/roi-eva/analyze", json={
        "baseline": {"investment_name": "Test", "initial_investment": 1000000.0,
                     "operating_profit": 200000.0, "total_assets": 5000000.0,
                     "current_liabilities": 1000000.0},
        "calculation": {"nopat": 180000.0, "wacc_pct": 10.0}
    }, timeout=5)
    print(f"[5] SCM ROI/EVA: {r.status_code} eva={r.json().get('eva')} roi={r.json().get('roi_pct')}%")

    # 6. Root endpoint shows linked systems
    r = httpx.get("http://localhost:8000/", timeout=5)
    print(f"[6] Root: {r.status_code} systems={len(r.json()['linked_systems'])}")

    # 7. Start EventCore
    print("\nStarting EventCore...")
    ec_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=str(EC_BASE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(8)

    r = httpx.get("http://localhost:8001/api/v1/health", timeout=5)
    print(f"[7] EventCore health: {r.status_code} {r.json()['status']}")

    # 8. EventCore exclusions
    r = httpx.get("http://localhost:8001/api/v1/bio-sync/exclusions", timeout=5)
    if r.status_code == 200:
        d = r.json()
        print(f"[8] Exclusions: {d.get('permanent_gaps')} gap={d.get('sync_ready_rows')}")
    else:
        print(f"[8] Exclusions failed: {r.status_code}")

    # 9. EventCore push-all to Bio-ERP
    print("\n--- Attempting live sync: EventCore -> Bio-ERP ---")
    r = httpx.post("http://localhost:8001/api/v1/bio-sync/push-all", timeout=30)
    if r.status_code == 200:
        d = r.json()
        print(f"[9] Sync OK: batch={d.get('batch_id')}")
        for res in d.get("results", []):
            print(f"    {res['entity']}: sent={res['sent']} accepted={res['accepted']} rejected={res['rejected']}")
    else:
        print(f"[9] Sync failed: {r.status_code} {r.text[:200]}")

    print("\n=== ALL TESTS COMPLETE ===")

finally:
    bio_proc.terminate()
    try:
        ec_proc.terminate()
    except:
        pass
    print("Servers terminated.")
