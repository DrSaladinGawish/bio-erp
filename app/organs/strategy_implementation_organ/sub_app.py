"""
Strategy Implementation Sub-Application for BIO-ERP v5
=======================================================
Mount at: app.mount("/api/v1/strategy-implementation", strategy_implementation_app) in BIO-ERP's main.py

Techniques: OKR, MBO, Balanced Scorecard, Strategy Map, Change Management,
            Project Portfolio Management, Resource Allocation, Action Planning,
            Performance Contracts, Strategy Execution Framework
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

strategy_implementation_app = FastAPI(
    title="Strategy Implementation Microservice",
    description="Strategy Implementation Tools — OKR, MBO, BSC, Strategy Map, Change Management, and more",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — OKR
# =============================================================================


class KeyResultSchema(BaseModel):
    kr_name: str = Field(..., min_length=1)
    target_value: float = Field(..., ge=0)
    current_value: float = Field(default=0.0, ge=0)
    unit: str = Field(default="")


class ObjectiveSchema(BaseModel):
    objective_name: str = Field(..., min_length=1)
    owner: str = Field(default="")
    key_results: List[KeyResultSchema]


class OKRSpecSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    period: str = Field(default="Q1-2026")
    objectives: List[ObjectiveSchema]

# =============================================================================
# PYDANTIC SCHEMAS — MBO
# =============================================================================


class MBOGoalSchema(BaseModel):
    goal_name: str = Field(..., min_length=1)
    manager: str = Field(default="")
    weight_pct: float = Field(default=25.0, ge=0, le=100)
    target: str = Field(default="")
    actual: str = Field(default="")
    completion_pct: float = Field(default=0.0, ge=0, le=100)


class MBOSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    period: str = Field(default="Annual-2026")
    goals: List[MBOGoalSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Balanced Scorecard
# =============================================================================


class BSCPerspectiveSchema(BaseModel):
    perspective: str = Field(..., description="FINANCIAL, CUSTOMER, INTERNAL_PROCESS, LEARNING_GROWTH")
    weight_pct: float = Field(default=25.0, ge=0, le=100)


class BSCMeasureSchema(BaseModel):
    measure_name: str = Field(..., min_length=1)
    perspective: str
    target_value: float = Field(...)
    current_value: float = Field(default=0.0)
    unit: str = Field(default="")
    initiative: str = Field(default="")


class BSCScorecardSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    perspectives: List[BSCPerspectiveSchema] = Field(default_factory=list)
    measures: List[BSCMeasureSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Strategy Map
# =============================================================================


class StrategyMapLinkSchema(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    relationship: str = Field(default="ENABLES")


class StrategyMapObjectiveSchema(BaseModel):
    name: str = Field(..., min_length=1)
    perspective: str
    description: str = Field(default="")
    priority: int = Field(default=3, ge=1, le=5)


class StrategyMapSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    objectives: List[StrategyMapObjectiveSchema]
    links: List[StrategyMapLinkSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Change Management
# =============================================================================


class ChangeInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    change_type: str = Field(default="ADAPTIVE", description="ADAPTIVE, INNOVATIVE, RADICAL")
    impact_level: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    readiness_score: float = Field(default=5.0, ge=1, le=10)
    stakeholder_support: float = Field(default=5.0, ge=1, le=10)
    estimated_duration_months: int = Field(default=6, ge=1, le=60)


class ChangeManagementSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    initiatives: List[ChangeInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Resource Allocation
# =============================================================================


class ResourceAllocationSchema(BaseModel):
    resource_name: str = Field(..., min_length=1)
    allocated_pct: float = Field(default=50.0, ge=0, le=100)
    strategic_priority: int = Field(default=3, ge=1, le=5)
    efficiency: float = Field(default=5.0, ge=1, le=10)
    cost: float = Field(default=0.0, ge=0)


class ResourceAllocationPlanSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    total_budget: float = Field(..., gt=0)
    allocations: List[ResourceAllocationSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Action Planning
# =============================================================================


class ActionItemSchema(BaseModel):
    action_name: str = Field(..., min_length=1)
    responsible: str = Field(default="")
    deadline: str = Field(default="")
    status: str = Field(default="NOT_STARTED", description="NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED")
    priority: int = Field(default=3, ge=1, le=5)
    estimated_hours: float = Field(default=0.0, ge=0)


class ActionPlanSchema(BaseModel):
    plan_name: str = Field(..., min_length=1)
    organization_name: str = Field(..., min_length=1)
    actions: List[ActionItemSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Performance Contracts
# =============================================================================


class PerformanceContractSchema(BaseModel):
    contract_name: str = Field(..., min_length=1)
    contractee: str = Field(..., min_length=1)
    kpi_name: str = Field(..., min_length=1)
    target: float = Field(...)
    actual: float = Field(default=0.0)
    weight_pct: float = Field(default=25.0, ge=0, le=100)
    incentive_amount: float = Field(default=0.0, ge=0)

# =============================================================================
# PYDANTIC SCHEMAS — Strategy Execution Framework
# =============================================================================


class ExecutionDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    score: float = Field(default=5.0, ge=1, le=10)
    weight: float = Field(default=1.0, gt=0, le=10)
    description: str = Field(default="")


class StrategyExecutionSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    dimensions: List[ExecutionDimensionSchema]

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@strategy_implementation_app.get("/")
def root():
    return {
        "service": "Strategy Implementation Microservice",
        "version": "1.0.0",
        "techniques": [
            "OKR", "MBO", "Balanced_Scorecard", "Strategy_Map",
            "Change_Management", "Project_Portfolio_Management",
            "Resource_Allocation", "Action_Planning",
            "Performance_Contracts", "Strategy_Execution_Framework",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@strategy_implementation_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "strategy-implementation",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "okr", "mbo", "balanced_scorecard", "strategy_map",
            "change_management", "project_portfolio", "resource_allocation",
            "action_planning", "performance_contracts", "strategy_execution",
        ],
    }

# =============================================================================
# ENDPOINTS — OKR
# =============================================================================


@strategy_implementation_app.post("/okr/evaluate")
def okr_evaluate(okr: OKRSpecSchema):
    try:
        results = []
        for obj in okr.objectives:
            total_progress = 0
            for kr in obj.key_results:
                progress = (kr.current_value / kr.target_value * 100) if kr.target_value > 0 else 0
                total_progress += min(progress, 100)
            obj_progress = total_progress / len(obj.key_results) if obj.key_results else 0
            results.append({
                "objective": obj.objective_name,
                "owner": obj.owner,
                "progress_pct": round(obj_progress, 1),
                "key_results_count": len(obj.key_results),
                "status": "ON_TRACK" if obj_progress >= 70 else "AT_RISK" if obj_progress >= 40 else "OFF_TRACK",
            })
        total_objectives = len(okr.objectives)
        on_track = len([r for r in results if r["status"] == "ON_TRACK"])
        return {
            "success": True,
            "organization": okr.organization_name,
            "period": okr.period,
            "objectives_count": total_objectives,
            "on_track_count": on_track,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — MBO
# =============================================================================


@strategy_implementation_app.post("/mbo/evaluate")
def mbo_evaluate(mbo: MBOSchema):
    try:
        weighted_completion = sum(g.completion_pct * g.weight_pct / 100 for g in mbo.goals)
        results = [{
            "goal": g.goal_name,
            "manager": g.manager,
            "completion": g.completion_pct,
            "weight": g.weight_pct,
        } for g in mbo.goals]
        return {
            "success": True,
            "organization": mbo.organization_name,
            "period": mbo.period,
            "overall_completion_pct": round(weighted_completion, 1),
            "goals_count": len(mbo.goals),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Balanced Scorecard
# =============================================================================


@strategy_implementation_app.post("/bsc/score")
def bsc_score(scorecard: BSCScorecardSchema):
    try:
        if not scorecard.perspectives:
            scorecard.perspectives = [
                BSCPerspectiveSchema(perspective=p, weight_pct=25.0)
                for p in ["FINANCIAL", "CUSTOMER", "INTERNAL_PROCESS", "LEARNING_GROWTH"]
            ]
        perspective_weights = {p.perspective: p.weight_pct for p in scorecard.perspectives}
        perspective_scores = {}
        for m in scorecard.measures:
            progress = (m.current_value / m.target_value * 100) if m.target_value > 0 else 0
            perspective_scores.setdefault(m.perspective, []).append(min(progress, 100))
        weighted_total = 0
        for pers, scores in perspective_scores.items():
            avg = sum(scores) / len(scores)
            weight = perspective_weights.get(pers, 25)
            weighted_total += avg * weight / 100
        return {
            "success": True,
            "organization": scorecard.organization_name,
            "measures_count": len(scorecard.measures),
            "perspective_breakdown": {k: round(sum(v) / len(v), 1) for k, v in perspective_scores.items()},
            "overall_score": round(weighted_total, 1),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategy Map
# =============================================================================


@strategy_implementation_app.post("/strategy-map/analyze")
def strategy_map_analyze(sm: StrategyMapSchema):
    try:
        perspectives = {}
        for obj in sm.objectives:
            perspectives.setdefault(obj.perspective, []).append(obj.name)
        inbound = {}
        outbound = {}
        for link in sm.links:
            outbound.setdefault(link.source, []).append(link.target)
            inbound.setdefault(link.target, []).append(link.source)
        orphan_objectives = [obj.name for obj in sm.objectives if obj.name not in inbound]
        return {
            "success": True,
            "organization": sm.organization_name,
            "objectives_count": len(sm.objectives),
            "links_count": len(sm.links),
            "perspectives": {k: len(v) for k, v in perspectives.items()},
            "orphan_objectives": orphan_objectives,
            "connectivity_score": round(len(sm.links) / max(len(sm.objectives), 1), 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Change Management
# =============================================================================


@strategy_implementation_app.post("/change/assess")
def change_assess(cm: ChangeManagementSchema):
    try:
        results = []
        for init in cm.initiatives:
            readiness = init.readiness_score
            support = init.stakeholder_support
            composite = (readiness + support) / 2
            success_probability = composite * 10
            results.append({
                "initiative": init.initiative_name,
                "type": init.change_type,
                "impact": init.impact_level,
                "success_probability_pct": round(min(success_probability, 100), 1),
                "duration_months": init.estimated_duration_months,
            })
        avg_probability = sum(r["success_probability_pct"] for r in results) / len(results) if results else 0
        return {
            "success": True,
            "organization": cm.organization_name,
            "initiatives_count": len(cm.initiatives),
            "average_success_probability": round(avg_probability, 1),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Resource Allocation
# =============================================================================


@strategy_implementation_app.post("/allocation/analyze")
def allocation_analyze(plan: ResourceAllocationPlanSchema):
    try:
        total_allocated = sum(a.allocated_pct for a in plan.allocations)
        total_cost = sum(a.cost for a in plan.allocations)
        prioritized = sorted(plan.allocations, key=lambda a: a.strategic_priority)
        return {
            "success": True,
            "organization": plan.organization_name,
            "total_budget": plan.total_budget,
            "total_allocated_pct": round(total_allocated, 1),
            "remaining_pct": round(100 - total_allocated, 1),
            "total_cost": total_cost,
            "top_priorities": [{"name": a.resource_name, "priority": a.strategic_priority} for a in prioritized[:5]],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Action Planning
# =============================================================================


@strategy_implementation_app.post("/action-plan/analyze")
def action_plan_analyze(plan: ActionPlanSchema):
    try:
        status_counts = {}
        total_hours = 0
        for a in plan.actions:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
            total_hours += a.estimated_hours
        completed = status_counts.get("COMPLETED", 0)
        total = len(plan.actions)
        completion_rate = (completed / total * 100) if total else 0
        return {
            "success": True,
            "organization": plan.organization_name,
            "plan_name": plan.plan_name,
            "total_actions": total,
            "completion_rate_pct": round(completion_rate, 1),
            "status_breakdown": status_counts,
            "total_estimated_hours": total_hours,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Performance Contracts
# =============================================================================


@strategy_implementation_app.post("/contract/evaluate")
def contract_evaluate(contracts: List[PerformanceContractSchema]):
    try:
        results = []
        total_incentive = 0
        total_earned = 0
        for c in contracts:
            achievement = (c.actual / c.target * 100) if c.target > 0 else 0
            earned = c.incentive_amount * min(achievement / 100, 1.5)
            total_incentive += c.incentive_amount
            total_earned += earned
            results.append({
                "contract": c.contract_name,
                "contractee": c.contractee,
                "kpi": c.kpi_name,
                "achievement_pct": round(achievement, 1),
                "incentive_earned": round(earned, 2),
            })
        return {
            "success": True,
            "contracts_count": len(contracts),
            "total_incentive_pool": total_incentive,
            "total_incentive_earned": round(total_earned, 2),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategy Execution Framework
# =============================================================================


@strategy_implementation_app.post("/execution/assess")
def execution_assess(framework: StrategyExecutionSchema):
    try:
        weighted_score = sum(d.score * d.weight for d in framework.dimensions)
        total_weight = sum(d.weight for d in framework.dimensions)
        overall = weighted_score / total_weight if total_weight > 0 else 0
        maturity = "ADVANCED" if overall >= 8 else "DEVELOPING" if overall >= 5 else "EMERGING"
        weakest = min(framework.dimensions, key=lambda d: d.score)
        strongest = max(framework.dimensions, key=lambda d: d.score)
        return {
            "success": True,
            "organization": framework.organization_name,
            "dimensions_count": len(framework.dimensions),
            "overall_execution_score": round(overall, 2),
            "maturity_level": maturity,
            "strongest_dimension": strongest.dimension_name,
            "weakest_dimension": weakest.dimension_name,
            "results": [{"name": d.dimension_name, "score": d.score, "weight": d.weight} for d in framework.dimensions],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/strategy-implementation"):
    parent_app.mount(prefix, strategy_implementation_app)
