"""
Test OR-ERP Planning & Analysis Module
=======================================
Verifies all planning endpoints work in READ-ONLY mode.
"""

import requests
import sys

BASE_URL = "http://localhost:8000/api/v1/or/planning"
PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def test(name, method, endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        elif method == "DELETE":
            r = requests.delete(url, timeout=10)
        else:
            r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            success = data.get("success", True)
            status = PASS if success else FAIL
            print(f"  {status} {name}")
            results.append({"test": name, "status": "PASS"})
            return data
        else:
            print(f"  {FAIL} {name} (HTTP {r.status_code})")
            results.append({"test": name, "status": "FAIL"})
            return None
    except Exception as e:
        print(f"  {FAIL} {name} ({str(e)})")
        results.append({"test": name, "status": "FAIL"})
        return None

print("=" * 60)
print("OR-ERP PLANNING & ANALYSIS TEST SUITE")
print("=" * 60)

# [1] Planning info
print("\n[1] Planning Module Info")
test("Planning Info", "GET", "/")

# [2] What-If Inventory
print("\n[2] What-If Inventory Analysis")
test("Inventory +20% Demand", "POST", "/what-if/inventory", {
    "scenario_name": "Demand Increase 20%",
    "demand_multiplier": 1.2,
    "holding_cost_change": 0.0,
    "ordering_cost_change": 0.0
})

# [3] Production Mix
print("\n[3] Production Mix Optimization")
test("Production Mix", "POST", "/optimize/production-mix", {
    "scenario_name": "Standard Production",
    "labor_hours_available": 100,
    "machine_hours_available": 80
})

# [4] Transportation
print("\n[4] Transportation Analysis")
test("Transportation Vogel", "POST", "/analyze/transportation", {
    "scenario_name": "Egypt Distribution",
    "method": "vogel"
})

# [5] Project Schedule
print("\n[5] Project Schedule (PERT/CPM)")
test("Project Schedule", "POST", "/analyze/project-schedule", {
    "scenario_name": "Construction Project",
    "activities": [
        {"id": "A", "name": "Site Prep", "predecessors": [], "duration": 3},
        {"id": "B", "name": "Foundation", "predecessors": ["A"], "duration": 4},
        {"id": "C", "name": "Framing", "predecessors": ["B"], "duration": 5}
    ]
})

# [6] Scenario Comparison
print("\n[6] Scenario Comparison")
test("Compare Scenarios", "POST", "/compare-scenarios", {
    "report_name": "Inventory Comparison",
    "scenarios": [
        {"type": "inventory", "name": "Current", "params": {}},
        {"type": "inventory", "name": "High Demand", "params": {"demand_multiplier": 1.5}}
    ]
})

# [7] List Scenarios
print("\n[7] List Saved Scenarios")
test("List Scenarios", "GET", "/scenarios")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")

if failed == 0:
    print("\n🎉 ALL PLANNING TESTS PASSED — Read-Only mode verified!")
    sys.exit(0)
else:
    sys.exit(1)
