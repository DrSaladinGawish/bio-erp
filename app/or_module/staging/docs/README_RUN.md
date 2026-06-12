# OR-ERP Microservice - Run Guide
## Operations Research Module for ERP Systems

**Source:** كتاب البحوث الإلكترونية في المحاسبة (Al-Azhar University, 2025)  
**Version:** 1.1.0 (Realigned) | **Port:** 8010

---

## Quick Start (3 Steps)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
# Option A: Direct Python
python main.py

# Option B: Uvicorn (recommended)
uvicorn main:app --host 0.0.0.0 --port 8010 --reload

# Option C: Docker
docker-compose up --build
```

### Step 3: Run Tests
```bash
# In a new terminal
python test_or_api.py
```

---

## API Endpoints

| Method | Endpoint | Book Chapter | Description |
|--------|----------|--------------|-------------|
| GET | `/` | - | Service info |
| GET | `/health` | - | Health check |
| POST | `/api/v1/or/decision-analysis` | Bonus | Decision under uncertainty |
| POST | `/api/v1/or/linear-programming` | Ch 2, 4, 5 | LP Simplex + sensitivity |
| **POST** | **`/api/v1/or/graphical-lp`** | **Ch 3** | **Graphical method** |
| POST | `/api/v1/or/inventory/optimize` | Bonus | EOQ, EPQ, backorders |
| POST | `/api/v1/or/inventory/abc-analysis` | Bonus | ABC classification |
| POST | `/api/v1/or/inventory/quantity-discount` | Bonus | Quantity discount |
| POST | `/api/v1/or/transportation` | Ch 6 | Transport optimization |
| POST | `/api/v1/or/assignment` | Bonus | Hungarian algorithm |
| **POST** | **`/api/v1/or/game-theory`** | **Ch 7** | **Game theory** |
| **POST** | **`/api/v1/or/pert-cpm`** | **Ch 8** | **PERT/CPM networks** |
| **POST** | **`/api/v1/or/knapsack`** | **Ch 9, 11** | **Dynamic programming** |
| **POST** | **`/api/v1/or/goal-programming`** | **Ch 10** | **Goal programming** |
| POST | `/api/v1/or/theory-of-constraints` | Bonus | Bottleneck & throughput |
| POST | `/api/v1/or/cvp-analysis` | Bonus | Break-even & scenarios |
| POST | `/api/v1/or/batch` | - | Multi-model batch |
| GET | `/api/v1/or/audit-trail` | - | Audit log |
| GET | `/api/v1/or/report` | Ch 1 | Module status |

**20 endpoints covering all 11 book chapters + 6 bonus utilities**

---

## Interactive Documentation

Once running, open your browser:
- **Swagger UI:** http://localhost:8010/docs
- **ReDoc:** http://localhost:8010/redoc

---

## Sample cURL Commands

### Decision Analysis (EMV)
```bash
curl -X POST http://localhost:8010/api/v1/or/decision-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "Investment Decision",
    "states": [
      {"id": "boom", "name": "Boom", "probability": 0.3},
      {"id": "normal", "name": "Normal", "probability": 0.5},
      {"id": "recession", "name": "Recession", "probability": 0.2}
    ],
    "alternatives": [
      {"id": "stocks", "name": "Stocks", "payoffs": {"boom": 100000, "normal": 40000, "recession": -20000}},
      {"id": "bonds", "name": "Bonds", "payoffs": {"boom": 50000, "normal": 50000, "recession": 30000}}
    ],
    "criterion": "emv"
  }'
```

### Linear Programming
```bash
curl -X POST http://localhost:8010/api/v1/or/linear-programming \
  -H "Content-Type: application/json" \
  -d '{
    "objective": {"name": "Profit", "coefficients": [40, 30], "sense": "maximize"},
    "constraints": [
      {"name": "Labor", "coefficients": [2, 1], "rhs": 100, "operator": "<="},
      {"name": "Machine", "coefficients": [1, 2], "rhs": 80, "operator": "<="}
    ]
  }'
```

### Inventory EOQ
```bash
curl -X POST http://localhost:8010/api/v1/or/inventory/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{
      "sku": "TEST-001", "name": "Test Item",
      "annual_demand": 1000, "ordering_cost": 50,
      "holding_cost_per_unit": 2.5, "unit_cost": 10,
      "lead_time_days": 5, "daily_demand": 2.74
    }],
    "model_type": "eoq"
  }'
```

---

## File Structure

```
.
├── main.py                 # FastAPI application (all endpoints wired)
├── or_erp_module.py        # Core algorithm engines
├── or_erp_router.py        # Standalone router (alternative to main.py)
├── or_erp_schema.sql       # Database schema (PostgreSQL/SQLite)
├── test_or_api.py          # Comprehensive test suite
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # Multi-service orchestration
└── OR_ERP_Module_Documentation.md  # Full docs
```


### Graphical LP (Chapter 3)
```bash
curl -X POST http://localhost:8010/api/v1/or/graphical-lp \
  -H "Content-Type: application/json" \
  -d '{
    "objective": {"name": "Profit", "coefficients": [3, 2], "sense": "maximize"},
    "constraints": [
      {"name": "Labor", "coefficients": [2, 1], "rhs": 100, "operator": "<="},
      {"name": "Material", "coefficients": [1, 1], "rhs": 80, "operator": "<="}
    ]
  }'
```

### Game Theory (Chapter 7)
```bash
curl -X POST http://localhost:8010/api/v1/or/game-theory \
  -H "Content-Type: application/json" \
  -d '{
    "payoff_matrix": [[3, -2, 4], [1, 5, -1], [0, 3, 2]],
    "player_a_strategies": ["A1", "A2", "A3"],
    "player_b_strategies": ["B1", "B2", "B3"]
  }'
```

### PERT/CPM (Chapter 8)
```bash
curl -X POST http://localhost:8010/api/v1/or/pert-cpm \
  -H "Content-Type: application/json" \
  -d '{
    "activities": [
      {"id": "A", "name": "Site Prep", "predecessors": [], "duration": 3},
      {"id": "B", "name": "Foundation", "predecessors": ["A"], "duration": 4},
      {"id": "C", "name": "Framing", "predecessors": ["B"], "duration": 5}
    ]
  }'
```

### Knapsack DP (Chapters 9 & 11)
```bash
curl -X POST http://localhost:8010/api/v1/or/knapsack \
  -H "Content-Type: application/json" \
  -d '{
    "capacity": 50,
    "items": [
      {"id": "Project_A", "weight": 10, "value": 60},
      {"id": "Project_B", "weight": 20, "value": 100},
      {"id": "Project_C", "weight": 30, "value": 120}
    ]
  }'
```

### Goal Programming (Chapter 10)
```bash
curl -X POST http://localhost:8010/api/v1/or/goal-programming \
  -H "Content-Type: application/json" \
  -d '{
    "goals": [
      {"name": "Profit", "coefficients": [40, 30], "target": 1000, "priority": 1},
      {"name": "Labor", "coefficients": [2, 1], "target": 100, "priority": 2}
    ],
    "constraints": [
      {"name": "Capacity", "coefficients": [1, 1], "rhs": 80, "operator": "<="}
    ],
    "variables": ["x1", "x2"],
    "method": "preemptive"
  }'
```

---

## Integration with Existing ERP

### BIO-ERP v5.1
```python
# In your existing app.py
from main import app as or_app
from fastapi import FastAPI

main_app = FastAPI()
main_app.mount("/api/v1/or", or_app)
```

### EventManager ERP v9.2
```python
# Add to existing router
from or_erp_router import router as or_router
app.include_router(or_router, prefix="/api/v1/or")
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8010 in use | `uvicorn main:app --port 8020` |
| scipy not found | `pip install scipy` |
| Module import error | Ensure all files are in the same directory |
| Docker build fails | Check Docker daemon is running |

---

**Ready to optimize your ERP with Operations Research! 🚀**
