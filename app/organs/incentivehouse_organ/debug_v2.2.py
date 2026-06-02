"""Debug v2.2 500 errors."""
import sys, os, json
sys.path.insert(0, r"D:\ERP System\BIO_ERP\app\organs\incentivehouse_organ")
os.chdir(r"D:\ERP System\BIO_ERP\app\organs\incentivehouse_organ")

from fastapi.testclient import TestClient
from incentivehouse_server import app

client = TestClient(app)

# Auth first
ar = client.post("/v2/auth/login", json={"username": "admin", "password": "admin123"})
token = ar.json()["access_token"]
print(f"Auth: token={token[:20]}...")

# Test master extract
mr = client.post(f"/v2/extract/master?token={token}", json={"source_file": "Data_Base_Mtbls.xlsx"})
print(f"Master: {mr.status_code}")
if mr.status_code != 200:
    print(f"  Body: {mr.text[:500]}")

# Test BNK extract
er = client.post(f"/v2/extract?token={token}", json={"module":"BNK","source_file":"Bnk_TRNX SOURCE.xlsx","dry_run":False})
print(f"Extract BNK: {er.status_code}")
if er.status_code != 200:
    print(f"  Body: {er.text[:500]}")
else:
    print(f"  Result: {json.dumps(er.json(), indent=2)[:300]}")
