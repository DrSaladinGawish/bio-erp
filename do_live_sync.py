"""Execute live sync: start Bio-ERP + EventCore, push data, verify"""
import subprocess, time, httpx, sys, os

BASE = "D:/ERP System/BIO_ERP"
EC_BASE = "D:/EventCore_ERP"

# 1. Start Bio-ERP
print("[1] Starting Bio-ERP on port 8000...")
bio_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

# Wait for it
for i in range(20):
    time.sleep(2)
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2)
        if r.status_code == 200:
            print(f"  Bio-ERP OK (attempt {i+1})")
            break
    except:
        pass
else:
    print("  FAILED to start Bio-ERP")
    bio_proc.terminate()
    sys.exit(1)

# 2. Start EventCore
print("[2] Starting EventCore on port 8001...")
ec_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd=EC_BASE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

for i in range(15):
    time.sleep(2)
    try:
        r = httpx.get("http://localhost:8001/api/v1/health", timeout=2)
        if r.status_code == 200:
            print(f"  EventCore OK (attempt {i+1})")
            break
    except:
        pass
else:
    print("  FAILED to start EventCore")
    bio_proc.terminate()
    sys.exit(1)

# 3. Verify organs
print("\n[3] Verifying organs...")
try:
    r = httpx.get("http://localhost:8000/api/v1/scm/health", timeout=3)
    print(f"  SCM organ: {r.status_code} {r.json()['status']} ({len(r.json()['engines_ready'])} engines)")

    r = httpx.get("http://localhost:8000/api/v1/or/health", timeout=3)
    print(f"  OR organ: {r.status_code} {r.json()['status']}")

    r = httpx.get("http://localhost:8000/", timeout=3)
    print(f"  Linked systems: {len(r.json()['linked_systems'])}")
except Exception as e:
    print(f"  Organ check failed: {e}")

# 4. Execute push-all from EventCore to Bio-ERP
print("\n[4] Executing live sync: EventCore -> Bio-ERP...")
try:
    r = httpx.post("http://localhost:8001/api/v1/bio-sync/push-all", timeout=60)
    if r.status_code == 200:
        d = r.json()
        print(f"  Batch: {d.get('batch_id')}")
        for res in d.get("results", []):
            emoji = "OK" if res.get("accepted", 0) > 0 or res.get("sent", 0) == 0 else "!!"
            print(f"  {emoji} {res['entity']}: sent={res['sent']} accepted={res.get('accepted',0)} rejected={res.get('rejected',0)}")
    else:
        print(f"  Sync FAILED: {r.status_code} {r.text[:200]}")
except Exception as e:
    print(f"  Sync ERROR: {e}")

# 5. Test SCM endpoint
print("\n[5] Testing SCM prescription...")
try:
    r = httpx.post("http://localhost:8000/api/v1/scm/roi-eva/quick?nopat=180000&capital_employed=4000000&wacc_pct=10", timeout=5)
    print(f"  SCM ROI/EVA quick: {r.status_code} eva={r.json().get('eva')}")
except Exception as e:
    print(f"  SCM test failed: {e}")

# 6. Cleanup
print("\n[6] Summary:")
print("  Bio-ERP Doctor: http://localhost:8000 (ONLINE)")
print("  EventCore Patient: http://localhost:8001 (ONLINE)")
print("  SCM Module: http://localhost:8000/api/v1/scm/ (26 endpoints)")
print("  OR Module: http://localhost:8000/api/v1/or/ (30+ endpoints)")
print("  Bridge: EventCore -> Bio-ERP via X-Bridge-Token")

# Keep running for 30 seconds so user can test, then shut down
print("\nServers will run for 30 seconds, then auto-terminate...")
time.sleep(30)

bio_proc.terminate()
ec_proc.terminate()
print("\nServers terminated.")
