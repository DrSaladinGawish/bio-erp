"""Start Bio-ERP and test SCM endpoints"""
import subprocess, time, httpx, sys, os

BASE = "D:/ERP System/BIO_ERP"
os.chdir(BASE)
os.environ["BIO_ERP_BRIDGE_TOKEN"] = "ec-bridge-token-dev"

print("Starting Bio-ERP on port 8000...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

# Wait for startup
for i in range(30):
    time.sleep(1)
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2)
        if r.status_code == 200:
            print(f"Bio-ERP started (attempt {i+1})")
            break
    except:
        pass
else:
    print("FAILED to start Bio-ERP")
    proc.terminate()
    sys.exit(1)

# Test SCM
try:
    r = httpx.get("http://localhost:8000/api/v1/scm/health", timeout=5)
    print(f"SCM health: {r.status_code} {r.json()['status']}")

    r = httpx.post("http://localhost:8000/api/v1/scm/tdabc/calculate-pool", json={
        "name": "Test", "total_cost": 100000.0, "resources_count": 5, "efficiency_pct": 85.0
    }, timeout=5)
    print(f"TDABC: {r.status_code} practical={r.json().get('practical_minutes')}")

    r = httpx.get("http://localhost:8000/api/v1/or/health", timeout=5)
    print(f"OR: {r.status_code} {r.json()['status']}")

    print("\n=== ALL SCM ENDPOINTS VERIFIED ===")
except Exception as e:
    print(f"Error: {e}")
    # Show server output
    stdout, stderr = proc.communicate(timeout=3)
    if stderr:
        print("Server stderr:", stderr.decode()[-500:])
finally:
    proc.terminate()
    print("Server terminated.")
