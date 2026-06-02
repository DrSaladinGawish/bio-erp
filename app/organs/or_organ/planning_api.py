"""
OR-ERP Planning API — Read-Only Analysis Endpoints
===================================================
These endpoints provide planning insights WITHOUT modifying production data.
All results are saved to disposable files, not the database.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.organs.or_organ.analysis_engine import ORAnalysisEngine

router = APIRouter(prefix="/api/v1/or/planning", tags=["Planning & Analysis"])

# Initialize analysis engine (read-only from production DB)
analyzer = ORAnalysisEngine(
    production_db_url="sqlite:///bio_erp.db",  # Will be overridden by env var
    analysis_dir="./analysis_sandbox"
)

# =============================================================================
# SCHEMAS
# =============================================================================

class WhatIfInventoryRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    scenario_name: Optional[str] = "Inventory Analysis"
    demand_multiplier: float = Field(default=1.0, ge=0.1, le=5.0)
    holding_cost_change: float = Field(default=0.0, ge=-0.5, le=0.5)
    ordering_cost_change: float = Field(default=0.0, ge=-0.5, le=0.5)

class ProductionMixRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    scenario_name: Optional[str] = "Production Mix"
    labor_hours_available: Optional[float] = None
    machine_hours_available: Optional[float] = None
    material_a_available: Optional[float] = None

class TransportationRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    scenario_name: Optional[str] = "Transportation Analysis"
    method: str = Field(default="vogel", pattern="^(nw_corner|least_cost|vogel)$")

class ProjectScheduleRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    scenario_name: Optional[str] = "Project Schedule"
    activities: Optional[List[Dict[str, Any]]] = None

class ScenarioComparisonRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    report_name: str = "Scenario Comparison Report"
    scenarios: List[Dict[str, Any]]

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/")
def planning_info():
    """Planning module info"""
    return {
        "module": "OR-ERP Planning & Analysis",
        "mode": "READ-ONLY",
        "warning": "This module does NOT modify production data",
        "capabilities": [
            "what_if_inventory",
            "optimize_production_mix", 
            "analyze_transportation",
            "analyze_project_schedule",
            "compare_scenarios"
        ],
        "storage": "Disposable files in ./analysis_sandbox",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/what-if/inventory")
def what_if_inventory(req: WhatIfInventoryRequest):
    """
    What-If Inventory Analysis

    Analyze impact of demand/cost changes on inventory policy.
    Does NOT modify production data.
    """
    try:
        scenario = analyzer.what_if_inventory(
            scenario_name=req.scenario_name,
            demand_multiplier=req.demand_multiplier,
            holding_cost_change=req.holding_cost_change,
            ordering_cost_change=req.ordering_cost_change
        )
        return {
            "success": True,
            "mode": "READ-ONLY",
            "scenario": {
                "id": scenario.id,
                "name": scenario.name,
                "parameters": scenario.parameters,
                "results": scenario.results
            },
            "saved_to": f"{analyzer.analysis_dir}/scenario_{scenario.id}.json",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/optimize/production-mix")
def optimize_production_mix(req: ProductionMixRequest):
    """
    Production Mix Optimization

    Find optimal product mix given resource constraints.
    Does NOT modify production data.
    """
    try:
        scenario = analyzer.optimize_production_mix(
            scenario_name=req.scenario_name,
            labor_hours_available=req.labor_hours_available,
            machine_hours_available=req.machine_hours_available,
            material_a_available=req.material_a_available
        )
        return {
            "success": True,
            "mode": "READ-ONLY",
            "scenario": {
                "id": scenario.id,
                "name": scenario.name,
                "parameters": scenario.parameters,
                "results": scenario.results
            },
            "recommendation": f"Optimal profit: ${scenario.results.get('objective_value', 0):,.2f}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze/transportation")
def analyze_transportation(req: TransportationRequest):
    """
    Transportation Cost Analysis

    Compare transportation methods and costs.
    Does NOT modify production data.
    """
    try:
        scenario = analyzer.analyze_transportation(
            scenario_name=req.scenario_name,
            method=req.method
        )
        return {
            "success": True,
            "mode": "READ-ONLY",
            "scenario": {
                "id": scenario.id,
                "name": scenario.name,
                "method": req.method,
                "results": scenario.results
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze/project-schedule")
def analyze_project_schedule(req: ProjectScheduleRequest):
    """
    Project Schedule Analysis (PERT/CPM)

    Analyze project timeline and critical path.
    Does NOT modify production data.
    """
    try:
        scenario = analyzer.analyze_project_schedule(
            scenario_name=req.scenario_name,
            activities=req.activities
        )
        return {
            "success": True,
            "mode": "READ-ONLY",
            "scenario": {
                "id": scenario.id,
                "name": scenario.name,
                "results": scenario.results
            },
            "critical_path": scenario.results.get("critical_path", []),
            "project_duration": scenario.results.get("project_duration"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/compare-scenarios")
def compare_scenarios(req: ScenarioComparisonRequest):
    """
    Compare Multiple Scenarios

    Run and compare multiple what-if scenarios.
    Does NOT modify production data.
    """
    try:
        report = analyzer.compare_scenarios(req.scenarios)
        return {
            "success": True,
            "mode": "READ-ONLY",
            "report": {
                "id": report.report_id,
                "type": report.report_type,
                "scenarios_count": len(report.scenarios),
                "recommendations": report.recommendations
            },
            "saved_to": f"{analyzer.analysis_dir}/{report.report_id}_scenario_comparison.json",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/scenarios")
def list_scenarios():
    """List all saved analysis scenarios"""
    try:
        scenarios = analyzer.list_scenarios()
        return {
            "success": True,
            "scenarios_count": len(scenarios),
            "scenarios": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "type": s.get("description", "").split()[0] if s.get("description") else "unknown",
                    "created_at": s.get("created_at")
                }
                for s in scenarios
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/scenarios/clear")
def clear_scenarios():
    """Clear all analysis scenarios (disposable)"""
    try:
        count = analyzer.clear_analysis_files()
        return {
            "success": True,
            "message": f"Cleared {count} analysis files",
            "warning": "This only deletes analysis files, NOT production data",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
