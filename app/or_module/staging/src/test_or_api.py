"""
OR-ERP Microservice Test Suite
==============================
Tests all 9 chapters with real API calls.
Run the server first: uvicorn main:app --port 8010
Then run: python test_or_api.py
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8010"
PASS = "✅ PASS"
FAIL = "❌ FAIL"

results = []

def test(name, method, endpoint, payload=None):
    """Run a single test and report"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=payload, timeout=10)

        if r.status_code == 200:
            data = r.json()
            success = data.get("success", True)
            status = PASS if success else FAIL
            print(f"  {status} {name}")
            results.append({"test": name, "status": "PASS", "data": data})
            return data
        else:
            print(f"  {FAIL} {name} (HTTP {r.status_code})")
            results.append({"test": name, "status": "FAIL", "error": r.text})
            return None
    except Exception as e:
        print(f"  {FAIL} {name} ({str(e)})")
        results.append({"test": name, "status": "FAIL", "error": str(e)})
        return None

print("=" * 60)
print("OR-ERP MICROSERVICE TEST SUITE")
print(f"Target: {BASE_URL}")
print(f"Time: {datetime.now().isoformat()}")
print("=" * 60)

# 0. Health Check
print("\n[0] Health Check")
test("Health", "GET", "/health")

# 1. Chapter 2 & 9: Decision Analysis
print("\n[1] Decision Analysis (Chapters 2 & 9)")
decision_payload = {
    "model_name": "Factory Expansion Decision",
    "states": [
        {"id": "boom", "name": "Economic Boom", "probability": 0.25},
        {"id": "normal", "name": "Normal", "probability": 0.50},
        {"id": "recession", "name": "Recession", "probability": 0.25}
    ],
    "alternatives": [
        {"id": "expand", "name": "Expand", "payoffs": {"boom": 500000, "normal": 200000, "recession": -100000}},
        {"id": "maintain", "name": "Maintain", "payoffs": {"boom": 300000, "normal": 250000, "recession": 50000}},
        {"id": "contract", "name": "Contract", "payoffs": {"boom": 150000, "normal": 150000, "recession": 100000}}
    ],
    "criterion": "emv",
    "alpha": 0.5
}
test("EMV Decision", "POST", "/api/v1/or/decision-analysis", decision_payload)

# 2. Chapter 3: Linear Programming
print("\n[2] Linear Programming (Chapter 3)")
lp_payload = {
    "model_name": "Production Mix Optimization",
    "objective": {
        "name": "Maximize Profit",
        "coefficients": [40, 30],
        "sense": "maximize"
    },
    "constraints": [
        {"name": "Labor", "coefficients": [2, 1], "rhs": 100, "operator": "<="},
        {"name": "Machine", "coefficients": [1, 2], "rhs": 80, "operator": "<="},
        {"name": "Material A", "coefficients": [3, 0], "rhs": 90, "operator": "<="}
    ],
    "run_sensitivity": True
}
test("LP Production Mix", "POST", "/api/v1/or/linear-programming", lp_payload)

# 3. Chapter 5: Inventory Optimization
print("\n[3] Inventory Optimization (Chapter 5)")
inventory_payload = {
    "items": [
        {
            "sku": "RAW-STEEL-001",
            "name": "Steel Sheet",
            "annual_demand": 2400,
            "ordering_cost": 150,
            "holding_cost_per_unit": 12,
            "unit_cost": 80,
            "lead_time_days": 7,
            "daily_demand": 6.5753,
            "stockout_cost": 25,
            "production_rate": 3000
        }
    ],
    "model_type": "all"
}
test("Inventory EOQ/EPQ", "POST", "/api/v1/or/inventory/optimize", inventory_payload)

# 4. ABC Classification
print("\n[4] ABC Classification (Chapter 5)")
abc_payload = [
    {"sku": "A001", "annual_demand": 1000, "unit_cost": 500},
    {"sku": "A002", "annual_demand": 5000, "unit_cost": 20},
    {"sku": "A003", "annual_demand": 200, "unit_cost": 2000},
    {"sku": "A004", "annual_demand": 800, "unit_cost": 150},
    {"sku": "A005", "annual_demand": 3000, "unit_cost": 10}
]
test("ABC Classification", "POST", "/api/v1/or/inventory/abc-analysis", abc_payload)

# 5. Chapter 6: Transportation
print("\n[5] Transportation (Chapter 6)")
transport_payload = {
    "model_name": "Egypt Distribution Network",
    "sources": [
        {"id": "CAI", "name": "Cairo Factory", "supply": 500, "is_source": True},
        {"id": "ALX", "name": "Alexandria Factory", "supply": 400, "is_source": True}
    ],
    "destinations": [
        {"id": "GIZ", "name": "Giza Warehouse", "demand": 300, "is_source": False},
        {"id": "LUX", "name": "Luxor Warehouse", "demand": 350, "is_source": False},
        {"id": "ASN", "name": "Aswan Warehouse", "demand": 250, "is_source": False}
    ],
    "routes": [
        {"from_id": "CAI", "to_id": "GIZ", "cost_per_unit": 50},
        {"from_id": "CAI", "to_id": "LUX", "cost_per_unit": 120},
        {"from_id": "CAI", "to_id": "ASN", "cost_per_unit": 150},
        {"from_id": "ALX", "to_id": "GIZ", "cost_per_unit": 80},
        {"from_id": "ALX", "to_id": "LUX", "cost_per_unit": 90},
        {"from_id": "ALX", "to_id": "ASN", "cost_per_unit": 100}
    ],
    "method": "vogel"
}
test("Transportation Vogel", "POST", "/api/v1/or/transportation", transport_payload)

# 6. Chapter 7: Assignment
print("\n[6] Assignment Problem (Chapter 7)")
assignment_payload = {
    "model_name": "Worker Job Assignment",
    "cost_matrix": [
        [9, 2, 7, 8],
        [6, 4, 3, 7],
        [5, 8, 1, 4],
        [7, 6, 9, 5]
    ]
}
test("Hungarian Algorithm", "POST", "/api/v1/or/assignment", assignment_payload)

# 7. Chapter 8: Theory of Constraints
print("\n[7] Theory of Constraints (Chapter 8)")
toc_payload = {
    "model_name": "Production Line TOC Analysis",
    "resources": [
        {"id": "M1", "name": "Machine 1", "capacity_hours": 160, "used_hours": 160, "output_units": 800, "operating_expense": 5000, "is_bottleneck": True},
        {"id": "M2", "name": "Machine 2", "capacity_hours": 200, "used_hours": 140, "output_units": 800, "operating_expense": 4000},
        {"id": "M3", "name": "Machine 3", "capacity_hours": 180, "used_hours": 120, "output_units": 800, "operating_expense": 3500}
    ],
    "products": [
        {
            "id": "P1", "name": "Product Alpha",
            "selling_price": 100, "raw_material_cost": 40, "demand": 500,
            "processing_times": {"M1": 0.2, "M2": 0.15, "M3": 0.1}
        },
        {
            "id": "P2", "name": "Product Beta",
            "selling_price": 80, "raw_material_cost": 30, "demand": 600,
            "processing_times": {"M1": 0.1, "M2": 0.2, "M3": 0.15}
        }
    ]
}
test("TOC Analysis", "POST", "/api/v1/or/theory-of-constraints", toc_payload)

# 8. Chapter 4: CVP Analysis
print("\n[8] Cost-Volume-Profit (Chapter 4)")
cvp_payload = {
    "model_name": "Product Line CVP",
    "fixed_costs": 50000,
    "variable_cost": 25,
    "selling_price": 60,
    "target_profit": 20000,
    "scenarios": [
        {"name": "Pessimistic", "volume": 1000, "sp": 55, "vc": 28},
        {"name": "Expected", "volume": 1500, "sp": 60, "vc": 25},
        {"name": "Optimistic", "volume": 2000, "sp": 65, "vc": 22}
    ]
}
test("CVP Analysis", "POST", "/api/v1/or/cvp-analysis", cvp_payload)


# ---- Chapter 3: Graphical LP ----
print("\n[3] Graphical LP (Chapter 3)")
graphical_payload = {
    "model_name": "Product Mix Graphical",
    "objective": {"name": "Profit", "coefficients": [3, 2], "sense": "maximize"},
    "constraints": [
        {"name": "Labor", "coefficients": [2, 1], "rhs": 100, "operator": "<="},
        {"name": "Material", "coefficients": [1, 1], "rhs": 80, "operator": "<="},
        {"name": "Non-negativity X", "coefficients": [1, 0], "rhs": 0, "operator": ">="},
        {"name": "Non-negativity Y", "coefficients": [0, 1], "rhs": 0, "operator": ">="}
    ]
}
test("Graphical LP", "POST", "/api/v1/or/graphical-lp", graphical_payload)

# ---- Chapter 7: Game Theory ----
print("\n[7] Game Theory (Chapter 7)")
game_payload = {
    "model_name": "Market Share Game",
    "payoff_matrix": [[3, -2, 4], [1, 5, -1], [0, 3, 2]],
    "player_a_strategies": ["A1", "A2", "A3"],
    "player_b_strategies": ["B1", "B2", "B3"]
}
test("Game Theory Saddle", "POST", "/api/v1/or/game-theory", game_payload)

# ---- Chapter 8: PERT/CPM ----
print("\n[8] PERT/CPM (Chapter 8)")
pert_payload = {
    "model_name": "Construction Project",
    "activities": [
        {"id": "A", "name": "Site Prep", "predecessors": [], "duration": 3},
        {"id": "B", "name": "Foundation", "predecessors": ["A"], "duration": 4},
        {"id": "C", "name": "Framing", "predecessors": ["B"], "duration": 5},
        {"id": "D", "name": "Electrical", "predecessors": ["C"], "duration": 2},
        {"id": "E", "name": "Plumbing", "predecessors": ["C"], "duration": 3},
        {"id": "F", "name": "Finishing", "predecessors": ["D", "E"], "duration": 4}
    ]
}
test("PERT/CPM Network", "POST", "/api/v1/or/pert-cpm", pert_payload)

# ---- Chapter 9 & 11: Dynamic Programming ----
print("\n[9] Dynamic Programming - Knapsack (Chapters 9 & 11)")
knapsack_payload = {
    "model_name": "Investment Portfolio",
    "capacity": 50,
    "items": [
        {"id": "Project_A", "weight": 10, "value": 60},
        {"id": "Project_B", "weight": 20, "value": 100},
        {"id": "Project_C", "weight": 30, "value": 120}
    ]
}
test("Knapsack DP", "POST", "/api/v1/or/knapsack", knapsack_payload)

# ---- Chapter 10: Goal Programming ----
print("\n[10] Goal Programming (Chapter 10)")
goal_payload = {
    "model_name": "Multi-Objective Production",
    "goals": [
        {"name": "Profit Target", "coefficients": [40, 30], "target": 1000, "priority": 1},
        {"name": "Labor Limit", "coefficients": [2, 1], "target": 100, "priority": 2}
    ],
    "constraints": [
        {"name": "Capacity", "coefficients": [1, 1], "rhs": 80, "operator": "<="}
    ],
    "variables": ["x1", "x2"],
    "method": "preemptive"
}
test("Goal Programming", "POST", "/api/v1/or/goal-programming", goal_payload)

# 14. Quantity Discount
print("\n[9] Quantity Discount Analysis")
discount_payload = {
    "item": {
        "sku": "BULK-001", "name": "Bulk Material",
        "annual_demand": 10000, "ordering_cost": 200,
        "holding_cost_per_unit": 5, "unit_cost": 50,
        "lead_time_days": 3, "daily_demand": 27.4
    },
    "tiers": [
        {"min_qty": 0, "max_qty": 500, "unit_cost": 50},
        {"min_qty": 501, "max_qty": 2000, "unit_cost": 48},
        {"min_qty": 2001, "unit_cost": 45}
    ]
}
test("Quantity Discount", "POST", "/api/v1/or/inventory/quantity-discount", discount_payload)

# 15. Batch Processing
print("\n[10] Batch Processing")
batch_payload = [
    {"type": "cvp", "data": {
        "model_name": "Batch CVP",
        "fixed_costs": 30000,
        "variable_cost": 20,
        "selling_price": 50,
        "target_profit": 10000
    }},
    {"type": "inventory", "data": {
        "items": [{
            "sku": "BATCH-001", "name": "Batch Item",
            "annual_demand": 1200, "ordering_cost": 100,
            "holding_cost_per_unit": 6, "unit_cost": 30,
            "lead_time_days": 5, "daily_demand": 3.29
        }],
        "model_type": "eoq"
    }}
]
test("Batch Multi-Model", "POST", "/api/v1/or/batch", batch_payload)

# 16. Audit Trail
print("\n[11] Audit Trail")
test("Audit Trail", "GET", "/api/v1/or/audit-trail")

# 17. Module Report
print("\n[12] Module Report")
test("Module Report", "GET", "/api/v1/or/report")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Target: 18 tests for 11 chapters")

if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  - {r['test']}: {r.get('error', 'Unknown error')}")
    sys.exit(1)
else:
    print("\n🎉 ALL TESTS PASSED - OR-ERP Module is fully operational!")
    sys.exit(0)
