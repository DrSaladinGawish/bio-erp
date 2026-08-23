"""
Ethics & Social Responsibility Sub-Application for BIO-ERP v5
===============================================================
Mount at: app.mount("/api/v1/ethics-social", ethics_social_app) in BIO-ERP's main.py

Techniques: ESG Framework, CSR Strategy, Triple Bottom Line, Ethical Leadership,
            Stakeholder Engagement, Sustainability Reporting
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

ethics_social_app = FastAPI(
    title="Ethics & Social Responsibility Microservice",
    description="Ethics & Social Responsibility -- ESG, CSR, Triple Bottom Line, Ethical Leadership, Stakeholder Engagement, Sustainability",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS -- ESG Framework
# =============================================================================


class ESGPillarSchema(BaseModel):
    pillar_name: str = Field(..., description="ENVIRONMENTAL, SOCIAL, GOVERNANCE")
    score: float = Field(default=5.0, ge=1, le=10)
    weight: float = Field(default=33.3, ge=0, le=100)
    metrics: List[dict] = Field(default_factory=list, description="List of {name, value, unit}")


class ESGFrameworkSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    industry: str = Field(default="")
    pillars: List[ESGPillarSchema]

# =============================================================================
# PYDANTIC SCHEMAS -- CSR Strategy
# =============================================================================


class CSRInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    category: str = Field(..., description="COMMUNITY, ENVIRONMENT, EMPLOYEES, ETHICAL_OPERATIONS, PHILANTHROPY")
    budget: float = Field(default=0.0, ge=0)
    beneficiaries_count: int = Field(default=0, ge=0)
    impact_score: float = Field(default=5.0, ge=1, le=10)
    alignment_with_values: float = Field(default=5.0, ge=1, le=10)


class CSRStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    total_csr_budget: float = Field(..., gt=0)
    revenue: float = Field(default=0.0, ge=0)
    initiatives: List[CSRInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS -- Triple Bottom Line
# =============================================================================


class TBLSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    economic_score: float = Field(default=5.0, ge=1, le=10, description="Profit dimension")
    social_score: float = Field(default=5.0, ge=1, le=10, description="People dimension")
    environmental_score: float = Field(default=5.0, ge=1, le=10, description="Planet dimension")
    revenue: float = Field(default=0.0, ge=0)
    carbon_footprint_tons: float = Field(default=0.0, ge=0)
    employees_satisfied_pct: float = Field(default=50.0, ge=0, le=100)
    community_investment: float = Field(default=0.0, ge=0)

# =============================================================================
# PYDANTIC SCHEMAS -- Ethical Leadership
# =============================================================================


class EthicalDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    score: float = Field(default=5.0, ge=1, le=10)
    weight: float = Field(default=1.0, gt=0, le=10)
    evidence: List[str] = Field(default_factory=list)


class EthicalLeadershipSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    leader_name: str = Field(default="")
    dimensions: List[EthicalDimensionSchema]

# =============================================================================
# PYDANTIC SCHEMAS -- Stakeholder Engagement
# =============================================================================


class StakeholderSchema(BaseModel):
    stakeholder_name: str = Field(..., min_length=1)
    stakeholder_type: str = Field(..., description="INTERNAL, EXTERNAL, REGULATORY, COMMUNITY, INVESTOR")
    interest_level: float = Field(default=5.0, ge=1, le=10)
    influence_level: float = Field(default=5.0, ge=1, le=10)
    satisfaction_level: float = Field(default=5.0, ge=1, le=10)
    engagement_frequency: str = Field(default="QUARTERLY", description="WEEKLY, MONTHLY, QUARTERLY, ANNUAL")


class StakeholderEngagementSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    stakeholders: List[StakeholderSchema]

# =============================================================================
# PYDANTIC SCHEMAS -- Sustainability Reporting
# =============================================================================


class SustainabilityMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    category: str = Field(..., description="ENVIRONMENTAL, SOCIAL, GOVERNANCE")
    current_value: float = Field(...)
    target_value: float = Field(...)
    unit: str = Field(default="")
    year_over_year_change_pct: float = Field(default=0.0)


class SustainabilityReportSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    reporting_period: str = Field(default="2025")
    framework: str = Field(default="GRI", description="GRI, SASB, TCFD, UN_SDGS")
    metrics: List[SustainabilityMetricSchema]

# =============================================================================
# ENDPOINTS -- Root & Health
# =============================================================================


@ethics_social_app.get("/")
def root():
    return {
        "service": "Ethics & Social Responsibility Microservice",
        "version": "1.0.0",
        "techniques": [
            "ESG_Framework", "CSR_Strategy", "Triple_Bottom_Line",
            "Ethical_Leadership", "Stakeholder_Engagement",
            "Sustainability_Reporting",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@ethics_social_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "ethics-social",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "esg", "csr", "triple_bottom_line",
            "ethical_leadership", "stakeholder_engagement",
            "sustainability_reporting",
        ],
    }

# =============================================================================
# ENDPOINTS -- ESG Framework
# =============================================================================


@ethics_social_app.post("/esg/analyze")
def esg_analyze(data: ESGFrameworkSchema):
    try:
        pillar_results = []
        weighted_total = 0
        total_weight = 0
        for p in data.pillars:
            weighted_total += p.score * p.weight
            total_weight += p.weight
            pillar_results.append({
                "pillar": p.pillar_name,
                "score": p.score,
                "weight": p.weight,
                "weighted_score": round(p.score * p.weight / 100, 2),
                "metrics_count": len(p.metrics),
            })
        overall_esg = weighted_total / total_weight if total_weight > 0 else 0
        rating = "AAA" if overall_esg >= 9 else "AA" if overall_esg >= 8 else "A" if overall_esg >= 7 else \
                 "BBB" if overall_esg >= 6 else "BB" if overall_esg >= 5 else "B" if overall_esg >= 4 else "CCC"
        return {
            "success": True,
            "organization": data.organization_name,
            "industry": data.industry,
            "overall_esg_score": round(overall_esg, 2),
            "esg_rating": rating,
            "pillars": pillar_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- CSR Strategy
# =============================================================================


@ethics_social_app.post("/csr/analyze")
def csr_analyze(data: CSRStrategySchema):
    try:
        by_category = {}
        total_beneficiaries = 0
        for init in data.initiatives:
            by_category.setdefault(init.category, []).append(init.initiative_name)
            total_beneficiaries += init.beneficiaries_count
        total_investment = sum(i.budget for i in data.initiatives)
        csr_pct = (total_investment / data.revenue * 100) if data.revenue > 0 else 0
        avg_impact = sum(i.impact_score for i in data.initiatives) / len(data.initiatives) if data.initiatives else 0
        return {
            "success": True,
            "organization": data.organization_name,
            "total_csr_budget": data.total_csr_budget,
            "total_investment": total_investment,
            "csr_pct_of_revenue": round(csr_pct, 2),
            "initiatives_count": len(data.initiatives),
            "total_beneficiaries": total_beneficiaries,
            "average_impact_score": round(avg_impact, 2),
            "by_category": {k: len(v) for k, v in by_category.items()},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Triple Bottom Line
# =============================================================================


@ethics_social_app.post("/tbl/analyze")
def tbl_analyze(data: TBLSchema):
    try:
        overall = (data.economic_score + data.social_score + data.environmental_score) / 3
        balance = max(data.economic_score, data.social_score, data.environmental_score) - \
                  min(data.economic_score, data.social_score, data.environmental_score)
        strongest = "ECONOMIC" if data.economic_score >= data.social_score and data.economic_score >= data.environmental_score else \
                    "SOCIAL" if data.social_score >= data.environmental_score else "ENVIRONMENTAL"
        sustainability = "HIGH" if overall >= 7 and balance <= 2 else "MODERATE" if overall >= 5 else "LOW"
        return {
            "success": True,
            "organization": data.organization_name,
            "economic_score": data.economic_score,
            "social_score": data.social_score,
            "environmental_score": data.environmental_score,
            "overall_tbl_score": round(overall, 2),
            "balance_gap": round(balance, 2),
            "strongest_dimension": strongest,
            "sustainability_level": sustainability,
            "revenue": data.revenue,
            "carbon_footprint_tons": data.carbon_footprint_tons,
            "community_investment": data.community_investment,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Ethical Leadership
# =============================================================================


@ethics_social_app.post("/ethical-leadership/assess")
def ethical_leadership_assess(data: EthicalLeadershipSchema):
    try:
        weighted_score = 0
        total_weight = 0
        dimension_results = []
        for d in data.dimensions:
            weighted_score += d.score * d.weight
            total_weight += d.weight
            dimension_results.append({
                "dimension": d.dimension_name,
                "score": d.score,
                "weight": d.weight,
                "evidence_count": len(d.evidence),
            })
        overall = weighted_score / total_weight if total_weight > 0 else 0
        maturity = "EXEMPLARY" if overall >= 8 else "STRONG" if overall >= 6 else \
                   "DEVELOPING" if overall >= 4 else "WEAK"
        return {
            "success": True,
            "organization": data.organization_name,
            "leader": data.leader_name,
            "overall_score": round(overall, 2),
            "maturity_level": maturity,
            "dimensions_count": len(data.dimensions),
            "results": dimension_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Stakeholder Engagement
# =============================================================================


@ethics_social_app.post("/stakeholder/analyze")
def stakeholder_analyze(data: StakeholderEngagementSchema):
    try:
        results = []
        by_type = {}
        total_satisfaction = 0
        for s in data.stakeholders:
            power_interest = s.interest_level * s.influence_level
            category = "MANAGE_CLOSELY" if s.interest_level >= 7 and s.influence_level >= 7 else \
                       "KEEP_SATISFIED" if s.influence_level >= 7 else \
                       "KEEP_INFORMED" if s.interest_level >= 7 else "MONITOR"
            total_satisfaction += s.satisfaction_level
            by_type.setdefault(s.stakeholder_type, []).append(s.stakeholder_name)
            results.append({
                "stakeholder": s.stakeholder_name,
                "type": s.stakeholder_type,
                "power_interest": round(power_interest, 2),
                "engagement_strategy": category,
                "satisfaction": s.satisfaction_level,
                "frequency": s.engagement_frequency,
            })
        avg_satisfaction = total_satisfaction / len(data.stakeholders) if data.stakeholders else 0
        return {
            "success": True,
            "organization": data.organization_name,
            "stakeholders_count": len(data.stakeholders),
            "average_satisfaction": round(avg_satisfaction, 2),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS -- Sustainability Reporting
# =============================================================================


@ethics_social_app.post("/sustainability/analyze")
def sustainability_analyze(report: SustainabilityReportSchema):
    try:
        by_category = {}
        on_track = 0
        total_metrics = len(report.metrics)
        for m in report.metrics:
            progress = (m.current_value / m.target_value * 100) if m.target_value != 0 else 0
            if m.category not in by_category:
                by_category[m.category] = {"count": 0, "total_progress": 0}
            by_category[m.category]["count"] += 1
            by_category[m.category]["total_progress"] += progress
            if progress >= 90:
                on_track += 1
        category_breakdown = {k: round(v["total_progress"] / v["count"], 1) for k, v in by_category.items()}
        return {
            "success": True,
            "organization": report.organization_name,
            "period": report.reporting_period,
            "framework": report.framework,
            "metrics_count": total_metrics,
            "on_track_count": on_track,
            "on_track_pct": round(on_track / total_metrics * 100, 1) if total_metrics > 0 else 0,
            "category_progress": category_breakdown,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/ethics-social"):
    parent_app.mount(prefix, ethics_social_app)
