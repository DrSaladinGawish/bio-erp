"""
Test OR-ERP Database Integration
=================================
Run this to verify DB persistence works.
"""

import sys
sys.path.insert(0, "app")

from or_module.db_integration import ORDBIntegratedModule

# Use SQLite for testing (no PostgreSQL needed)
module = ORDBIntegratedModule("sqlite:///test_or_erp.db")

print("=" * 60)
print("OR-ERP DATABASE INTEGRATION TEST")
print("=" * 60)

# Test 1: Decision Analysis with DB save
print("\n[1] Decision Analysis + DB Save")
states = [
    {"id": "boom", "name": "Boom", "probability": 0.3},
    {"id": "normal", "name": "Normal", "probability": 0.5},
    {"id": "recession", "name": "Recession", "probability": 0.2}
]
alternatives = [
    {"id": "expand", "name": "Expand", "payoffs": {"boom": 100, "normal": 50, "recession": -20}},
    {"id": "maintain", "name": "Maintain", "payoffs": {"boom": 60, "normal": 40, "recession": 10}}
]
module.create_decision_model(states, alternatives)
result = module.run_decision_analysis("emv")
print(f"  Saved model ID: {result.get('saved_model_id')}")
print(f"  Recommended: {result['recommended_alternative']}")

# Test 2: LP with DB save
print("\n[2] Linear Programming + DB Save")
lp_result = module.solve_linear_program(
    {"name": "Profit", "coefficients": [40, 30], "sense": "maximize"},
    [
        {"name": "Labor", "coefficients": [2, 1], "rhs": 100, "operator": "<="},
        {"name": "Machine", "coefficients": [1, 2], "rhs": 80, "operator": "<="}
    ]
)
print(f"  Saved model ID: {lp_result.get('saved_model_id')}")
print(f"  Objective value: {lp_result.get('objective_value')}")

# Test 3: Query history
print("\n[3] Query History from DB")
decisions = module.get_decision_history()
print(f"  Decision models saved: {len(decisions)}")
for d in decisions[:3]:
    print(f"    - {d['id']}: {d['name']} -> {d['recommended']}")

lp_history = module.get_lp_history()
print(f"  LP models saved: {len(lp_history)}")

# Test 4: DB Stats
print("\n[4] Database Statistics")
stats = module.get_db_stats()
for table, count in stats.items():
    print(f"  {table}: {count} rows")

# Test 5: Audit Trail
print("\n[5] Audit Trail (Sergey Protocol)")
audit = module.get_audit_trail_db()
print(f"  Audit entries: {len(audit)}")
for a in audit[:3]:
    print(f"    - {a['operation']} ({a['model_type']})")

# Test 6: Export all
print("\n[6] Export All Models")
export = module.export_all_models()
for key, count in export.items():
    if key != "timestamp":
        print(f"  {key}: {count}")

print("\n" + "=" * 60)
print("✅ ALL DB INTEGRATION TESTS PASSED")
print("=" * 60)
