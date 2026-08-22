"""
Operations Research ERP Microservice
=====================================
A runnable FastAPI application implementing all 9 chapters of 
"البحوث الإلكترونية في المحاسبة" (Al-Azhar University, 2025)

Run: uvicorn main:app --host 0.0.0.0 --port 8010 --reload
Test: python test_or_api.py
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import uvicorn
import warnings
warnings.filterwarnings("ignore", message=".*protected namespace.*")

# Import our OR engines
from or_erp_module import (
    ORERPModule,
    DecisionState, DecisionAlternative, DecisionAnalysisEngine,
    LPObjective, LPConstraint,
    InventoryItem,
    TransportNode, TransportRoute,
    TOCResource,
    BreakEvenPoint,
    TransportationEngine
)

app = FastAPI(
    title="OR-ERP Microservice",
    description="Operations Research Module for ERP Systems - Al-Azhar University Textbook Implementation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for frontend integration
# WARNING: Restrict allow_origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global module instance (singleton for demo; use dependency injection in production)
or_module = ORERPModule()





# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class DecisionStateSchema(BaseModel):
    id: str
    name: str
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    description: Optional[str] = ""

class DecisionAlternativeSchema(BaseModel):
    id: str
    name: str
    payoffs: Dict[str, float]
    costs: Optional[Dict[str, float]] = None

class DecisionAnalysisRequest(BaseModel):
    model_name: str = "Decision Analysis Model"
    states: List[DecisionStateSchema]
    alternatives: List[DecisionAlternativeSchema]
    criterion: str = Field(default="emv", pattern="^(maximax|maximin|hurwicz|laplace|minimax_regret|emv|eol)$")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)

class LPObjectiveSchema(BaseModel):
    name: str
    coefficients: List[float]
    sense: str = Field(default="maximize", pattern="^(maximize|minimize)$")

class LPConstraintSchema(BaseModel):
    name: str
    coefficients: List[float]
    rhs: float
    operator: str = Field(default="<=", pattern="^(<=|>=|==)$")

class LPRequest(BaseModel):
    model_name: str = "LP Model"
    objective: LPObjectiveSchema
    constraints: List[LPConstraintSchema]
    run_sensitivity: bool = False

# ---- Chapter 7: Game Theory Schemas ----
class GameTheoryRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str = "Game Theory Analysis"
    payoff_matrix: List[List[float]]
    player_a_strategies: Optional[List[str]] = None
    player_b_strategies: Optional[List[str]] = None

# ---- Chapter 8: PERT/CPM Schemas ----
class ActivitySchema(BaseModel):
    id: str
    name: Optional[str] = None
    predecessors: List[str] = Field(default_factory=list)
    duration: Optional[float] = None
    optimistic: Optional[float] = None
    most_likely: Optional[float] = None
    pessimistic: Optional[float] = None

class PERTCPMRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str = "PERT/CPM Network"
    activities: List[ActivitySchema]

# ---- Chapter 9 & 11: Dynamic Programming Schemas ----
class KnapsackItemSchema(BaseModel):
    id: str
    weight: float = Field(..., gt=0)
    value: float = Field(..., gt=0)

class KnapsackRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str = "0/1 Knapsack"
    capacity: float = Field(..., gt=0)
    items: List[KnapsackItemSchema]

# ---- Chapter 10: Goal Programming Schemas ----
class GoalSchema(BaseModel):
    name: str
    coefficients: List[float]
    target: float
    priority: int = Field(..., ge=1)
    type: str = Field(default="minimize_deviation")

class GoalProgrammingRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str = "Goal Programming"
    goals: List[GoalSchema]
    constraints: List[LPConstraintSchema]
    variables: List[str]
    method: str = Field(default="preemptive", pattern="^(preemptive|weighted)$")

# ---- Chapter 3: Graphical LP Schemas ----
class GraphicalLPRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str = "Graphical LP"
    objective: LPObjectiveSchema
    constraints: List[LPConstraintSchema]

class GraphicalLPResponse(BaseModel):
    method: str
    objective: str
    sense: str
    corner_points: List[List[float]]
    optimal_point: Optional[List[float]]
    optimal_value: float
    plot_data: Optional[Dict[str, Any]] = None

class InventoryItemSchema(BaseModel):
    sku: str
    name: str
    annual_demand: float = Field(..., gt=0)
    ordering_cost: float = Field(..., gt=0)
    holding_cost_per_unit: float = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0)
    lead_time_days: int = Field(default=0, ge=0)
    daily_demand: Optional[float] = None
    stockout_cost: Optional[float] = None
    production_rate: Optional[float] = None

class InventoryOptimizeRequest(BaseModel):
    items: List[InventoryItemSchema]
    model_type: str = Field(default="all", pattern="^(all|eoq|epq|abc|quantity_discount|probabilistic)$")

class ABCItemSchema(BaseModel):
    sku: str
    annual_demand: float
    unit_cost: float

class TransportNodeSchema(BaseModel):
    id: str
    name: str
    supply: float = Field(default=0.0, ge=0.0)
    demand: float = Field(default=0.0, ge=0.0)
    is_source: bool = True

class TransportRouteSchema(BaseModel):
    from_id: str
    to_id: str
    cost_per_unit: float = Field(..., gt=0)

class TransportRequest(BaseModel):
    model_name: str = "Transport Model"
    sources: List[TransportNodeSchema]
    destinations: List[TransportNodeSchema]
    routes: List[TransportRouteSchema]
    method: str = Field(default="vogel", pattern="^(nw_corner|least_cost|vogel|modi)$")

class AssignmentRequest(BaseModel):
    model_name: str = "Assignment Model"
    cost_matrix: List[List[float]]

class TOCResourceSchema(BaseModel):
    id: str
    name: str
    capacity_hours: float = Field(..., gt=0)
    used_hours: float = Field(default=0.0, ge=0.0)
    output_units: float = Field(default=0.0)
    operating_expense: float = Field(default=0.0)
    is_bottleneck: bool = False

class TOCProductSchema(BaseModel):
    id: str
    name: str
    selling_price: float = Field(..., gt=0)
    raw_material_cost: float = Field(..., ge=0)
    demand: float = Field(..., gt=0)
    processing_times: Dict[str, float]

class TOCRequest(BaseModel):
    model_name: str = "TOC Analysis"
    resources: List[TOCResourceSchema]
    products: List[TOCProductSchema]

class CVPRequest(BaseModel):
    model_name: str = "CVP Analysis"
    fixed_costs: float = Field(..., ge=0)
    variable_cost: float = Field(..., ge=0)
    selling_price: float = Field(..., gt=0)
    target_profit: float = Field(default=0.0)
    scenarios: Optional[List[Dict[str, Any]]] = None

class QuantityDiscountTierSchema(BaseModel):
    min_qty: float
    max_qty: Optional[float] = None
    unit_cost: float

class QuantityDiscountRequest(BaseModel):
    item: InventoryItemSchema
    tiers: List[QuantityDiscountTierSchema]

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
def root():
    return {
        "service": "OR-ERP Microservice",
        "version": "1.0.0",
        "source": "البحوث الإلكترونية في المحاسبة - Al-Azhar University 2025",
        "chapters": 11,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "or-erp",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready_11_chapters": [
            "decision_analysis", "linear_programming", "graphical_lp",
            "inventory_optimization", "transportation", "assignment",
            "game_theory", "pert_cpm", "dynamic_programming", "goal_programming",
            "theory_of_constraints", "cvp_analysis"
        ]
    }

# ---- Chapter 2 & 9: Decision Analysis ----
@app.post("/api/v1/or/decision-analysis")
def decision_analysis(req: DecisionAnalysisRequest):
    """
    Decision-making under uncertainty and risk.
    Criteria: Maximax, Maximin, Hurwicz, Laplace, Minimax Regret, EMV, EOL
    """
    try:
        states = [DecisionState(**s.model_dump()) for s in req.states]
        alternatives = [
            DecisionAlternative(
                id=a.id, name=a.name,
                payoffs=a.payoffs,
                costs=a.costs or {}
            ) for a in req.alternatives
        ]

        or_module.decision_engine = DecisionAnalysisEngine(states, alternatives)

        result = or_module.run_decision_analysis(req.criterion, req.alpha)

        return {
            "success": True,
            "model_name": req.model_name,
            "criterion": req.criterion,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 3: Linear Programming ----
@app.post("/api/v1/or/linear-programming")
def linear_programming(req: LPRequest):
    """
    Solve LP using Simplex method. Returns optimal solution and shadow prices.
    """
    try:
        objective = LPObjective(**req.objective.model_dump())
        constraints = [LPConstraint(**c.model_dump()) for c in req.constraints]

        result = or_module.solve_linear_program(req.objective.model_dump(), [c.model_dump() for c in req.constraints])

        response = {
            "success": result.get("success", False),
            "model_name": req.model_name,
            "objective_value": result.get("objective_value"),
            "solution": result.get("solution"),
            "shadow_prices": result.get("shadow_prices"),
            "status": result.get("status"),
            "timestamp": datetime.now().isoformat()
        }

        if req.run_sensitivity and result.get("success"):
            sens = or_module.lp_engine.sensitivity_analysis()
            response["sensitivity"] = sens.get("sensitivities", [])

        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 5: Inventory Optimization ----
@app.post("/api/v1/or/inventory/optimize")
def inventory_optimize(req: InventoryOptimizeRequest):
    """
    Run EOQ, EPQ, backorder, or all inventory models.
    """
    try:
        items = [InventoryItem(**i.model_dump()) for i in req.items]
        results = or_module.optimize_inventory([i.model_dump() for i in req.items], req.model_type)

        return {
            "success": True,
            "model_name": "Inventory Optimization",
            "model_type": req.model_type,
            "items_analyzed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/or/inventory/abc-analysis")
def abc_analysis(items: List[ABCItemSchema]):
    """
    ABC Classification based on annual consumption value.
    """
    try:
        items_data = [i.model_dump() for i in items]
        df = or_module.abc_classify_inventory(items_data)

        return {
            "success": True,
            "items_count": len(items),
            "classification": df.to_dict('records'),
            "summary": {
                "class_a_count": int((df['class'] == 'A').sum()),
                "class_b_count": int((df['class'] == 'B').sum()),
                "class_c_count": int((df['class'] == 'C').sum()),
                "total_value": float(df['annual_consumption_value'].sum())
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/or/inventory/quantity-discount")
def quantity_discount(req: QuantityDiscountRequest):
    """
    Analyze quantity discount tiers and find optimal order quantity.
    """
    try:
        item = InventoryItem(**req.item.model_dump())
        tiers = [t.model_dump() for t in req.tiers]

        or_module.inventory_engine = or_module.inventory_engine.__class__([item])
        result = or_module.inventory_engine.quantity_discount_analysis(item, tiers)

        return {
            "success": True,
            "sku": item.sku,
            "optimal_tier": result["optimal_tier"],
            "all_tiers": result["all_tiers"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 6: Transportation ----
@app.post("/api/v1/or/transportation")
def transportation(req: TransportRequest):
    """
    Solve transportation problem: NW Corner, Least Cost, Vogel's method.
    """
    try:
        sources = [TransportNode(**s.model_dump()) for s in req.sources]
        destinations = [TransportNode(**d.model_dump()) for d in req.destinations]
        routes = [TransportRoute(**r.model_dump()) for r in req.routes]

        or_module.transport_engine = TransportationEngine(sources, destinations, routes)

        if req.method == "nw_corner":
            result = or_module.transport_engine.northwest_corner()
        elif req.method == "least_cost":
            result = or_module.transport_engine.least_cost_method()
        elif req.method == "vogel":
            result = or_module.transport_engine.vogel_approximation()
        else:
            raise HTTPException(status_code=400, detail="MODI not yet implemented in this version")

        return {
            "success": True,
            "model_name": req.model_name,
            "method": req.method,
            "total_cost": result["total_cost"],
            "allocation": result["allocation"],
            "sources": [s.id for s in sources],
            "destinations": [d.id for d in destinations],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 7: Assignment ----
@app.post("/api/v1/or/assignment")
def assignment(req: AssignmentRequest):
    """
    Solve assignment problem using Hungarian Algorithm.
    """
    try:
        import numpy as np
        from or_erp_module import AssignmentEngine

        matrix = np.array(req.cost_matrix)
        engine = AssignmentEngine(matrix)
        result = engine.hungarian_algorithm()

        return {
            "success": True,
            "model_name": req.model_name,
            "matrix_size": matrix.shape,
            "assignments": result["assignments"],
            "total_cost": result["total_cost"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 8: Theory of Constraints ----
@app.post("/api/v1/or/theory-of-constraints")
def theory_of_constraints(req: TOCRequest):
    """
    TOC analysis: bottleneck identification, throughput accounting, optimal product mix.
    """
    try:
        resources = [TOCResource(**r.model_dump()) for r in req.resources]
        products = [p.model_dump() for p in req.products]

        result = or_module.analyze_constraints([r.model_dump() for r in req.resources], products)

        return {
            "success": True,
            "model_name": req.model_name,
            "bottleneck": result["bottleneck_analysis"],
            "throughput_accounting": result["throughput_accounting"],
            "optimal_product_mix": result["optimal_product_mix"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 4: CVP Analysis ----
@app.post("/api/v1/or/cvp-analysis")
def cvp_analysis(req: CVPRequest):
    """
    Cost-Volume-Profit analysis: break-even, target profit, scenarios.
    """
    try:
        result = or_module.analyze_cost_profit(
            req.fixed_costs, req.variable_cost, req.selling_price,
            req.target_profit, req.scenarios
        )

        return {
            "success": True,
            "model_name": req.model_name,
            "basic_analysis": result["basic_analysis"],
            "scenarios": result["scenarios"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Chapter 3: Graphical LP ----
@app.post("/api/v1/or/graphical-lp")
def graphical_lp(req: GraphicalLPRequest):
    """
    Chapter 3: البرمجة الخطية: الحل البياني
    Solve 2-variable LP graphically. Returns corner points and plot data.
    """
    try:
        result = or_module.solve_graphical_lp(req.objective.model_dump(), [c.model_dump() for c in req.constraints])
        return {
            "success": True,
            "model_name": req.model_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 7: Game Theory ----
@app.post("/api/v1/or/game-theory")
def game_theory(req: GameTheoryRequest):
    """
    Chapter 7: نظرية المباريات
    Two-person zero-sum game analysis: saddle point, dominance, mixed strategies.
    """
    try:
        result = or_module.analyze_game(
            req.payoff_matrix,
            req.player_a_strategies,
            req.player_b_strategies
        )
        return {
            "success": True,
            "model_name": req.model_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 8: PERT/CPM ----
@app.post("/api/v1/or/pert-cpm")
def pert_cpm(req: PERTCPMRequest):
    """
    Chapter 8: شبكات الأعمال
    PERT/CPM network analysis: critical path, slack, project duration.
    """
    try:
        activities = [a.model_dump() for a in req.activities]
        result = or_module.analyze_network(activities)
        return {
            "success": True,
            "model_name": req.model_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 9 & 11: Dynamic Programming ----
@app.post("/api/v1/or/knapsack")
def knapsack(req: KnapsackRequest):
    """
    Chapter 9 & 11: البرمجة الديناميكية
    0/1 Knapsack problem solved via Dynamic Programming.
    """
    try:
        items = [i.model_dump() for i in req.items]
        result = or_module.solve_knapsack(req.capacity, items)
        return {
            "success": True,
            "model_name": req.model_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Chapter 10: Goal Programming ----
@app.post("/api/v1/or/goal-programming")
def goal_programming(req: GoalProgrammingRequest):
    """
    Chapter 10: برمجة الأهداف
    Multi-objective optimization with priority levels.
    """
    try:
        result = or_module.solve_goal_programming(
            [g.model_dump() for g in req.goals],
            [c.model_dump() for c in req.constraints],
            req.variables,
            req.method
        )
        return {
            "success": True,
            "model_name": req.model_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---- Audit & Reporting ----
@app.get("/api/v1/or/audit-trail")
def audit_trail(limit: int = 100):
    """Full audit trail of all OR operations."""
    trail = or_module.get_audit_trail()
    return {
        "operations_count": len(trail),
        "operations": trail[-limit:] if limit else trail,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/or/report")
def module_report():
    """Comprehensive module status report."""
    return or_module.export_report()

# ---- Batch Processing ----
@app.post("/api/v1/or/batch")
def batch_process(requests: List[Dict[str, Any]]):
    """
    Process multiple OR models in one request.
    Each request must have: {"type": "lp|inventory|transport|...", "data": {...}}
    """
    results = []
    for req in requests:
        req_type = req.get("type")
        data = req.get("data", {})

        try:
            if req_type == "lp":
                r = linear_programming(LPRequest(**data))
            elif req_type == "inventory":
                r = inventory_optimize(InventoryOptimizeRequest(**data))
            elif req_type == "cvp":
                r = cvp_analysis(CVPRequest(**data))
            else:
                r = {"error": f"Unknown type: {req_type}"}
            results.append({"type": req_type, "status": "success", "result": r})
        except Exception as e:
            results.append({"type": req_type, "status": "error", "error": str(e)})

    return {"batch_results": results, "timestamp": datetime.now().isoformat()}

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
