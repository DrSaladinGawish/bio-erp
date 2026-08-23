"""
Knowledge & Learning Strategy Sub-Application for BIO-ERP v5
==============================================================
Mount at: app.mount("/api/v1/knowledge-learning", knowledge_learning_app) in BIO-ERP's main.py

Techniques: SECI Model, Intellectual Capital, Knowledge Management, Organizational Learning
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

knowledge_learning_app = FastAPI(
    title="Knowledge & Learning Strategy Microservice",
    description="Knowledge & Learning Strategy -- SECI Model, Intellectual Capital, Knowledge Management, Organizational Learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS -- SECI Model
# =============================================================================


class SECIPhaseSchema(BaseModel):
    phase_name: str = Field(..., description="SOCIALIZATION, EXTERNALIZATION, COMBINATION, INTERNALIZATION")
    activities: List[str] = Field(default_factory=list)
    maturity_level: float = Field(default=3.0, ge=1, le=10)
    current_knowledge_volume: int = Field(default=0, ge=0)


class SECISchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    phases: List[SECIPhaseSchema]

# =============================================================================
# PYDANTIC SCHEMAS -- Intellectual Capital
# =============================================================================


class IntellectualCapitalSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    human_capital_score: float = Field(default=5.0, ge=1, le=10, description="Employee skills, knowledge, experience")
    structural_capital_score: float = Field(default=5.0, ge=1, le=10, description="Processes, databases, patents")
    relational_capital_score: float = Field(default=5.0, ge=1, le=10, description="Customer relationships, brand, networks")
    employee_count: int = Field(default=0, ge=0)
    training_hours_per_employee: float = Field(default=0.0, ge=0)
    patents_count: int = Field(default=0, ge=0)
    employee_retention_pct: float = Field(default=80.0, ge=0, le=100)

# =============================================================================
# PYDANTIC SCHEMAS -- Knowledge Management
# =============================================================================


class KMInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    km_process: str = Field(..., description="CAPTURE, STORE, SHARE, APPLY, MEASURE")
    maturity_level: int = Field(default=2, ge=1, le=5)
    adoption_rate_pct: float = Field(default=30.0, ge=0, le=100)
    investment: float = Field(default=0.0, ge=0)
    expected_benefits: List[str] = Field(default_factory=list)


class KnowledgeManagementSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    total_km_budget: float = Field(default=0.0, ge=0)
    knowledge_domains: List[str] = Field(default_factory=list)
    initiatives: List[KMInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS -- Organizational Learning
# =============================================================================


class LearningDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    current_score: float = Field(default=5.0, ge=1, le=10)
    target_score: float = Field(default=7.0, ge=1, le=10)
    weight: float = Field(default=1.0, gt=0, le=10)
    description: str = Field(default="")


class OrgLearningSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    dimensions: List[LearningDimensionSchema]
    learning_budget_pct_of_revenue: float = Field(default=2.0, ge=0, le=20)
    annual_training_hours: float = Field(default=40.0, ge=0)

# =============================================================================
# ENDPOINTS -- Root & Health
# =============================================================================


@knowledge_learning_app.get("/")
def root():
    return {
        "service": "Knowledge & Learning Strategy Microservice",
        "version": "1.0.0",
        "techniques": [
            "SECI_Model", "Intellectual_Capital",
            "Knowledge_Management", "Organizational_Learning",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@knowledge_learning_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "knowledge-learning",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "seci_model", "intellectual_capital",
            "knowledge_management", "organizational_learning",
        ],
    }

# =============================================================================
# ENDPOINTS -- SECI Model
# =============================================================================


@knowledge_learning_app.post("/seci/analyze")
def seci_analyze(data: SECISchema):
    try:
        total_knowledge = sum(p.current_knowledge_volume for p in data.phases)
        avg_maturity = sum(p.maturity_level for p in data.phases) / len(data.phases) if data.phases else 0
        phase_results = []
        for p in data.phases:
            share = (p.current_knowledge_volume / total_knowledge * 100) if total_knowledge > 0 else 0
            phase_results.append({
                "phase": p.phase_name,
                "maturity": p.maturity_level,
                "knowledge_volume": p.current_knowledge_volume,
                "share_pct": round(share, 1),
                "activities_count": len(p.activities),
            })
        weakest = min(data.phases, key=lambda p: p.maturity_level) if data.phases else None
        return {
            "success": True,
            "organization": data.organization_name,
            "phases_count": len(data.phases),
            "total_knowledge_volume": total_knowledge,
            "average_maturity": round(avg_maturity, 2),
            "weakest_phase": weakest.phase_name if weakest else None,
            "results": phase_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Intellectual Capital
# =============================================================================


@knowledge_learning_app.post("/intellectual-capital/analyze")
def intellectual_capital_analyze(data: IntellectualCapitalSchema):
    try:
        ic_value = (data.human_capital_score + data.structural_capital_score + data.relational_capital_score) / 3
        leverage_ratio = (data.structural_capital_score / data.human_capital_score) if data.human_capital_score > 0 else 0
        maturity = "ADVANCED" if ic_value >= 8 else "DEVELOPING" if ic_value >= 5 else "EMERGING"
        return {
            "success": True,
            "organization": data.organization_name,
            "human_capital": data.human_capital_score,
            "structural_capital": data.structural_capital_score,
            "relational_capital": data.relational_capital_score,
            "ic_value_index": round(ic_value, 2),
            "leverage_ratio": round(leverage_ratio, 2),
            "maturity_level": maturity,
            "employee_count": data.employee_count,
            "training_hours_per_employee": data.training_hours_per_employee,
            "patents_count": data.patents_count,
            "retention_pct": data.employee_retention_pct,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Knowledge Management
# =============================================================================


@knowledge_learning_app.post("/km/evaluate")
def km_evaluate(data: KnowledgeManagementSchema):
    try:
        results = []
        by_process = {}
        total_adoption = 0
        for init in data.initiatives:
            by_process.setdefault(init.km_process, []).append(init.initiative_name)
            total_adoption += init.adoption_rate_pct
            results.append({
                "initiative": init.initiative_name,
                "process": init.km_process,
                "maturity": init.maturity_level,
                "adoption_rate": init.adoption_rate_pct,
                "investment": init.investment,
            })
        avg_adoption = total_adoption / len(data.initiatives) if data.initiatives else 0
        avg_maturity = sum(i.maturity_level for i in data.initiatives) / len(data.initiatives) if data.initiatives else 0
        return {
            "success": True,
            "organization": data.organization_name,
            "initiatives_count": len(data.initiatives),
            "total_budget": data.total_km_budget,
            "knowledge_domains": data.knowledge_domains,
            "average_maturity": round(avg_maturity, 2),
            "average_adoption": round(avg_adoption, 1),
            "by_process": {k: len(v) for k, v in by_process.items()},
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Organizational Learning
# =============================================================================


@knowledge_learning_app.post("/learning/assess")
def org_learning_assess(data: OrgLearningSchema):
    try:
        weighted_score = 0
        total_weight = 0
        gaps = []
        for d in data.dimensions:
            gap = d.target_score - d.current_score
            gaps.append({
                "dimension": d.dimension_name,
                "current": d.current_score,
                "target": d.target_score,
                "gap": round(gap, 2),
                "weight": d.weight,
            })
            weighted_score += d.current_score * d.weight
            total_weight += d.weight
        overall = weighted_score / total_weight if total_weight > 0 else 0
        maturity = "LEARNING_ORG" if overall >= 8 else "DEVELOPING" if overall >= 5 else "TRADITIONAL"
        return {
            "success": True,
            "organization": data.organization_name,
            "dimensions_count": len(data.dimensions),
            "overall_learning_score": round(overall, 2),
            "maturity_level": maturity,
            "learning_budget_pct": data.learning_budget_pct_of_revenue,
            "annual_training_hours": data.annual_training_hours,
            "gaps": gaps,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/knowledge-learning"):
    parent_app.mount(prefix, knowledge_learning_app)
