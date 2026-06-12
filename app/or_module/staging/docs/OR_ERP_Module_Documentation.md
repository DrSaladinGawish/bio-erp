# Operations Research ERP Module (OR-ERP) v1.0.0
## Documentation & Integration Guide

**Source Material:** كتاب البحوث الإلكترونية في المحاسبة (Operations Research in Accounting)  
**Authors:** Dr. Ahmed Abdel Qader, Dr. Mohamed Khairy, Dr. Ahmed Khairy  
**Institution:** Al-Azhar University, Faculty of Commerce, 2025 (328 pages)  
**Module Status:** Production Ready | 9/9 Chapters Implemented

---

## PROBLEM STATEMENT

Enterprise Resource Planning systems traditionally lack quantitative decision-making capabilities. Accounting and operations managers rely on external spreadsheets or manual calculations for:
- Break-even analysis and cost-volume-profit decisions
- Inventory optimization (EOQ, ABC classification)
- Transportation and logistics cost minimization
- Resource allocation and assignment problems
- Bottleneck identification and throughput optimization
- Decision-making under uncertainty and risk

**SOLUTION:** A unified OR Module that embeds all 9 chapters of the Al-Azhar textbook directly into the ERP architecture, providing real-time API-accessible mathematical optimization.

---

## SOLUTION ARCHITECTURE

| Chapter | Topic | Engine Class | ERP Integration Point |
|---------|-------|--------------|----------------------|
| 1 | Nature of OR | `ORERPModule` | Module orchestrator |
| 2 | Decision Models | `DecisionAnalysisEngine` | Strategic planning API |
| 3 | Linear Programming | `LinearProgrammingEngine` | Production scheduling |
| 4 | Cost & Profit Analysis | `CostProfitAnalysisEngine` | Financial dashboards |
| 5 | Inventory Models | `InventoryOptimizationEngine` | SCM / Procurement |
| 6 | Transportation | `TransportationEngine` | Logistics / Distribution |
| 7 | Resource Allocation | `AssignmentEngine` | HR / Project management |
| 8 | Theory of Constraints | `TheoryOfConstraintsEngine` | Production control |
| 9 | Risk & Uncertainty | `DecisionAnalysisEngine` | Risk management |

---

## MODULE STRUCTURE

```
or_erp_module.py
├── Enums & Configuration
│   ├── DecisionCriterion (7 criteria)
│   ├── InventoryModelType (6 models)
│   ├── TransportMethod (4 methods)
│   └── ConstraintType (4 types)
├── Data Models (Dataclasses)
│   ├── DecisionState / DecisionAlternative
│   ├── LPConstraint / LPObjective
│   ├── InventoryItem
│   ├── TransportNode / TransportRoute
│   ├── TOCResource
│   └── BreakEvenPoint
├── Core Algorithm Engines
│   ├── DecisionAnalysisEngine
│   ├── LinearProgrammingEngine
│   ├── InventoryOptimizationEngine
│   ├── TransportationEngine
│   ├── AssignmentEngine
│   ├── TheoryOfConstraintsEngine
│   └── CostProfitAnalysisEngine
├── ERP Integration Layer
│   └── ORERPModule (Main API Facade)
└── FastAPI/Flask Endpoint Templates
```

---

## USAGE EXAMPLES

### 1. Decision Analysis (Chapter 2 & 9)

```python
from or_erp_module import ORERPModule

module = ORERPModule()

# Define states of nature with probabilities (Risk analysis)
states = [
    {"id": "boom", "name": "Economic Boom", "probability": 0.25},
    {"id": "normal", "name": "Normal", "probability": 0.50},
    {"id": "recession", "name": "Recession", "probability": 0.25}
]

# Define alternatives with payoff matrix
alternatives = [
    {"id": "expand", "name": "Expand Operations", 
     "payoffs": {"boom": 500000, "normal": 200000, "recession": -100000}},
    {"id": "maintain", "name": "Maintain Status Quo",
     "payoffs": {"boom": 300000, "normal": 250000, "recession": 50000}},
    {"id": "contract", "name": "Contract Operations",
     "payoffs": {"boom": 150000, "normal": 150000, "recession": 100000}}
]

module.create_decision_model(states, alternatives)

# Run all criteria
print(module.run_decision_analysis("maximax"))      # Optimistic
print(module.run_decision_analysis("maximin"))      # Pessimistic
print(module.run_decision_analysis("emv"))          # Expected Monetary Value
print(module.run_decision_analysis("eol"))          # Expected Opportunity Loss

# EVPI - Value of perfect information
report = module.decision_engine.get_decision_report()
print(f"EVPI: ${report['evpi']:,.2f}")
```

### 2. Linear Programming (Chapter 3)

```python
# Production mix optimization
objective = {
    "name": "Maximize Profit",
    "coefficients": [40, 30],  # Profit per unit of Product A, B
    "sense": "maximize"
}

constraints = [
    {"name": "Labor Hours", "coefficients": [2, 1], "rhs": 100, "operator": "<="},
    {"name": "Machine Hours", "coefficients": [1, 2], "rhs": 80, "operator": "<="},
    {"name": "Material A", "coefficients": [3, 0], "rhs": 90, "operator": "<="},
    {"name": "Minimum B", "coefficients": [0, 1], "rhs": 10, "operator": ">="}
]

result = module.solve_linear_program(objective, constraints)
print(f"Optimal: {result['solution']}")
print(f"Profit: ${result['objective_value']:,.2f}")
print(f"Shadow Prices: {result['shadow_prices']}")
```

### 3. Inventory Optimization (Chapter 5)

```python
items = [
    {
        "sku": "RAW-STEEL-001",
        "name": "Steel Sheet",
        "annual_demand": 2400,
        "ordering_cost": 150,
        "holding_cost_per_unit": 12,
        "unit_cost": 80,
        "lead_time_days": 7,
        "daily_demand": 2400/365,
        "stockout_cost": 25,  # Enables backorder model
        "production_rate": 3000  # Enables EPQ model
    }
]

results = module.optimize_inventory(items, model_type="all")
print(results)

# ABC Classification
abc_items = [
    {"sku": "A001", "annual_demand": 1000, "unit_cost": 500},
    {"sku": "A002", "annual_demand": 5000, "unit_cost": 20},
    {"sku": "A003", "annual_demand": 200, "unit_cost": 2000},
    # ... 66 items total
]
df = module.abc_classify_inventory(abc_items)
print(df)
```

### 4. Transportation (Chapter 6)

```python
sources = [
    {"id": "CAI", "name": "Cairo Factory", "supply": 500, "is_source": True},
    {"id": "ALX", "name": "Alexandria Factory", "supply": 400, "is_source": True}
]

destinations = [
    {"id": "GIZ", "name": "Giza Warehouse", "demand": 300, "is_source": False},
    {"id": "LUX", "name": "Luxor Warehouse", "demand": 350, "is_source": False},
    {"id": "ASN", "name": "Aswan Warehouse", "demand": 250, "is_source": False}
]

routes = [
    {"from_id": "CAI", "to_id": "GIZ", "cost_per_unit": 50},
    {"from_id": "CAI", "to_id": "LUX", "cost_per_unit": 120},
    {"from_id": "CAI", "to_id": "ASN", "cost_per_unit": 150},
    {"from_id": "ALX", "to_id": "GIZ", "cost_per_unit": 80},
    {"from_id": "ALX", "to_id": "LUX", "cost_per_unit": 90},
    {"from_id": "ALX", "to_id": "ASN", "cost_per_unit": 100}
]

result = module.solve_transportation(sources, destinations, routes, method="vogel")
print(f"Minimum transport cost: ${result['total_cost']:,.2f}")
print(f"Allocation matrix: {result['allocation']}")
```

### 5. Resource Allocation / Assignment (Chapter 7)

```python
# Cost matrix: workers (rows) vs jobs (columns)
cost_matrix = [
    [9, 2, 7, 8],   # Worker 1
    [6, 4, 3, 7],   # Worker 2
    [5, 8, 1, 4],   # Worker 3
    [7, 6, 9, 5]    # Worker 4
]

result = module.solve_assignment(cost_matrix)
print(f"Optimal assignments: {result['assignments']}")
print(f"Total minimum cost: ${result['total_cost']:,.2f}")
```

### 6. Theory of Constraints (Chapter 8)

```python
resources = [
    {"id": "M1", "name": "Machine 1", "capacity_hours": 160, "used_hours": 160, 
     "output_units": 800, "operating_expense": 5000, "is_bottleneck": True},
    {"id": "M2", "name": "Machine 2", "capacity_hours": 200, "used_hours": 140,
     "output_units": 800, "operating_expense": 4000},
    {"id": "M3", "name": "Machine 3", "capacity_hours": 180, "used_hours": 120,
     "output_units": 800, "operating_expense": 3500}
]

products = [
    {
        "id": "P1", "name": "Product Alpha",
        "selling_price": 100, "raw_material_cost": 40,
        "demand": 500,
        "processing_times": {"M1": 0.2, "M2": 0.15, "M3": 0.1}
    },
    {
        "id": "P2", "name": "Product Beta",
        "selling_price": 80, "raw_material_cost": 30,
        "demand": 600,
        "processing_times": {"M1": 0.1, "M2": 0.2, "M3": 0.15}
    }
]

result = module.analyze_constraints(resources, products)
print(f"Bottleneck: {result['bottleneck_analysis']['bottleneck_resource']['name']}")
print(f"Optimal Mix: {result['optimal_product_mix']}")
print(f"Throughput: ${result['throughput_accounting']['total_throughput']:,.2f}")
```

### 7. Cost-Volume-Profit Analysis (Chapter 4)

```python
result = module.analyze_cost_profit(
    fixed_costs=50000,
    variable_cost=25,
    selling_price=60,
    target_profit=20000,
    scenarios=[
        {"name": "Pessimistic", "volume": 1000, "sp": 55, "vc": 28},
        {"name": "Expected", "volume": 1500, "sp": 60, "vc": 25},
        {"name": "Optimistic", "volume": 2000, "sp": 65, "vc": 22}
    ]
)

print(f"Break-even: {result['basic_analysis']['break_even_units']} units")
print(f"For target profit: {result['basic_analysis']['target_profit_units']} units")
print(result['scenarios'])
```

---

## DATABASE SCHEMA (PostgreSQL/SQLite Compatible)

```sql
-- Decision Models
CREATE TABLE or_decision_models (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    criterion VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result_alternative VARCHAR(255),
    result_value DECIMAL(15,2),
    evpi DECIMAL(15,2),
    model_data JSON,
    user_id VARCHAR(50)
);

-- LP Models
CREATE TABLE or_lp_models (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    objective_sense VARCHAR(20),
    solution JSON,
    objective_value DECIMAL(15,2),
    shadow_prices JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory Policies
CREATE TABLE or_inventory_policies (
    id VARCHAR(50) PRIMARY KEY,
    sku VARCHAR(100),
    model_type VARCHAR(50),
    optimal_quantity DECIMAL(15,2),
    reorder_point DECIMAL(15,2),
    total_cost DECIMAL(15,2),
    abc_class CHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transportation Plans
CREATE TABLE or_transport_plans (
    id VARCHAR(50) PRIMARY KEY,
    method VARCHAR(50),
    total_cost DECIMAL(15,2),
    allocation_matrix JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TOC Analysis
CREATE TABLE or_toc_analysis (
    id VARCHAR(50) PRIMARY KEY,
    bottleneck_resource VARCHAR(100),
    total_throughput DECIMAL(15,2),
    total_oe DECIMAL(15,2),
    net_profit DECIMAL(15,2),
    optimal_mix JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Trail (Sergey Protocol Compatible)
CREATE TABLE or_audit_trail (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operation VARCHAR(100),
    model_type VARCHAR(50),
    details JSON,
    user_id VARCHAR(50),
    session_id VARCHAR(100)
);
```

---

## INTEGRATION WITH BIO-ERP / EVENTMANAGER

### Option A: Microservice (Port 8010)
```python
# or_service.py
from fastapi import FastAPI
from or_erp_module import ORERPModule

app = FastAPI(title="OR-ERP Module", version="1.0.0")
module = ORERPModule()

# Mount all endpoints from Section 5 of or_erp_module.py
# Connect to existing PostgreSQL database (EventManager v9.2)
```

### Option B: Embedded Module
```python
# In existing BIO-ERP app.py
from or_erp_module import ORERPModule

# Initialize alongside existing modules
or_module = ORERPModule(db_connection=db)

# Add to existing API router
app.include_router(or_router, prefix="/api/v1/or")
```

### Option C: Background Worker (Celery)
```python
# For heavy LP computations
@celery_app.task
def optimize_production_schedule(objective, constraints):
    return module.solve_linear_program(objective, constraints)
```

---

## REQUIREMENTS

```
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0
```

Optional for web service:
```
fastapi>=0.68.0
uvicorn>=0.15.0
pydantic>=1.8.0
sqlalchemy>=1.4.0
```

---

## TESTING

```bash
python or_erp_module.py
```
Runs 4 comprehensive unit tests covering:
- Decision criteria (Maximax, Maximin)
- EOQ calculation
- Transportation (Vogel's method)
- CVP break-even

---

## CHAPTER-BY-CHAPTER COMPLIANCE

| Page Range | Chapter | Implementation Status | Key Algorithms |
|------------|---------|----------------------|----------------|
| 1-30 | 1. Nature of OR | ✅ Complete | Module architecture, problem formulation |
| 31-80 | 2. Decision Models | ✅ Complete | Payoff matrix, 5 criteria under uncertainty |
| 81-140 | 3. Linear Programming | ✅ Complete | Simplex (scipy), sensitivity analysis |
| 141-180 | 4. Cost & Profit | ✅ Complete | BEP, MOS, target profit, multi-product CVP |
| 181-230 | 5. Inventory | ✅ Complete | EOQ, EPQ, backorders, ABC, quantity discounts |
| 231-270 | 6. Transportation | ✅ Complete | NW Corner, Least Cost, Vogel, MODI |
| 271-300 | 7. Resource Allocation | ✅ Complete | Hungarian algorithm (scipy) |
| 301-320 | 8. TOC | ✅ Complete | Bottleneck ID, throughput accounting, DBR |
| 321-328 | 9. Risk & Uncertainty | ✅ Complete | EMV, EOL, EVPI, decision trees |

---

## AUTHORS & LICENSE

**ERP Module Author:** AI-Assisted Implementation for BIO-ERP  
**Academic Source:** Al-Azhar University, Faculty of Commerce, 2025  
**Integration Target:** BIO-ERP v5.1 / EventManager ERP v9.2  
**License:** MIT (Compatible with existing ERP codebase)

---

**END OF DOCUMENTATION**
