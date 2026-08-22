"""
Digital & Innovation Strategy Sub-Application for BIO-ERP v5
=============================================================
Mount at: app.mount("/api/v1/digital-innovation", digital_innovation_app) in BIO-ERP's main.py

Techniques: Digital Twin, Blockchain Strategy, AI/ML Strategy, IoT Strategy, Cloud Strategy,
            Platform Strategy, Innovation Pipeline, Technology Roadmap, Digital Transformation
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

digital_innovation_app = FastAPI(
    title="Digital & Innovation Strategy Microservice",
    description="Digital & Innovation Strategy — Digital Twin, Blockchain, AI/ML, IoT, Cloud, Platform, Innovation Pipeline, Tech Roadmap",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — Digital Twin
# =============================================================================


class DigitalTwinSchema(BaseModel):
    asset_name: str = Field(..., min_length=1)
    asset_type: str = Field(..., description="PHYSICAL_ASSET, PROCESS, SYSTEM, ORGANIZATION")
    maturity_level: int = Field(default=2, ge=1, le=5)
    data_sources: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    investment: float = Field(default=0.0, ge=0)
    expected_roi_pct: float = Field(default=0.0)


class DigitalTwinStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    twins: List[DigitalTwinSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Blockchain Strategy
# =============================================================================


class BlockchainInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    use_case: str = Field(..., description="SUPPLY_CHAIN, SMART_CONTRACT, IDENTITY, TOKENIZATION, OTHER")
    maturity_level: int = Field(default=1, ge=1, le=5)
    stakeholders: List[str] = Field(default_factory=list)
    expected_benefits: List[str] = Field(default_factory=list)
    investment: float = Field(default=0.0, ge=0)
    timeline_months: int = Field(default=12, ge=1, le=60)


class BlockchainStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    initiatives: List[BlockchainInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — AI/ML Strategy
# =============================================================================


class AIMLInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    ai_type: str = Field(..., description="ML, DEEP_LEARNING, NLP, COMPUTER_VISION, GENAI, RULE_BASED")
    maturity_level: int = Field(default=2, ge=1, le=5)
    data_availability: float = Field(default=5.0, ge=1, le=10)
    expected_impact: str = Field(default="MEDIUM")
    investment: float = Field(default=0.0, ge=0)
    timeline_months: int = Field(default=6, ge=1, le=36)


class AIMLStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    ai_budget_pct_of_it: float = Field(default=5.0, ge=0, le=50)
    initiatives: List[AIMLInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — IoT Strategy
# =============================================================================


class IoTInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    domain: str = Field(..., description="SMART_BUILDING, PREDICTIVE_MAINTENANCE, ASSET_TRACKING, ENVIRONMENTAL, OTHER")
    devices_count: int = Field(default=0, ge=0)
    connectivity: str = Field(default="WIFI", description="WIFI, LORAWAN, NB_IOT, 5G, SATELLITE")
    data_volume_gb_daily: float = Field(default=0.0, ge=0)
    maturity_level: int = Field(default=2, ge=1, le=5)
    investment: float = Field(default=0.0, ge=0)


class IoTStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    initiatives: List[IoTInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Cloud Strategy
# =============================================================================


class CloudServiceSchema(BaseModel):
    service_name: str = Field(..., min_length=1)
    provider: str = Field(default="AWS", description="AWS, AZURE, GCP, PRIVATE, HYBRID")
    monthly_cost: float = Field(default=0.0, ge=0)
    utilization_pct: float = Field(default=50.0, ge=0, le=100)
    criticality: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")


class CloudStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    cloud_budget: float = Field(..., gt=0)
    current_migration_pct: float = Field(default=0.0, ge=0, le=100)
    services: List[CloudServiceSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Platform Strategy
# =============================================================================


class PlatformSchema(BaseModel):
    platform_name: str = Field(..., min_length=1)
    platform_type: str = Field(..., description="MARKETPLACE, ECOSYSTEM, API, DATA, SOCIAL")
    users_count: int = Field(default=0, ge=0)
    developers_count: int = Field(default=0, ge=0)
    revenue_model: str = Field(default="SUBSCRIPTION")
    network_effect_strength: float = Field(default=5.0, ge=1, le=10)
    maturity_level: int = Field(default=2, ge=1, le=5)


class PlatformStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    platforms: List[PlatformSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Innovation Pipeline
# =============================================================================


class InnovationProjectSchema(BaseModel):
    project_name: str = Field(..., min_length=1)
    stage: str = Field(..., description="IDEATION, SCREENING, DEVELOPMENT, TESTING, LAUNCH")
    innovation_type: str = Field(default="INCREMENTAL", description="INCREMENTAL, RADICAL, DISRUPTIVE")
    budget: float = Field(default=0.0, ge=0)
    success_probability_pct: float = Field(default=50.0, ge=0, le=100)
    expected_revenue: float = Field(default=0.0, ge=0)


class InnovationPipelineSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    annual_rd_budget: float = Field(..., gt=0)
    projects: List[InnovationProjectSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Technology Roadmap
# =============================================================================


class TechInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    technology_area: str = Field(...)
    timeline_quarter: str = Field(..., description="Q1-2026, Q2-2026, etc.")
    maturity_level: int = Field(default=2, ge=1, le=5)
    investment: float = Field(default=0.0, ge=0)
    dependencies: List[str] = Field(default_factory=list)
    status: str = Field(default="PLANNED", description="PLANNED, IN_PROGRESS, COMPLETED")


class TechRoadmapSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    roadmap_years: int = Field(default=3, ge=1, le=10)
    initiatives: List[TechInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Digital Transformation
# =============================================================================


class TransformationDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    current_score: float = Field(default=3.0, ge=1, le=10)
    target_score: float = Field(default=7.0, ge=1, le=10)
    weight: float = Field(default=1.0, gt=0, le=10)


class DigitalTransformationSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    dimensions: List[TransformationDimensionSchema]
    total_budget: float = Field(..., gt=0)
    timeline_years: int = Field(default=3, ge=1, le=10)

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@digital_innovation_app.get("/")
def root():
    return {
        "service": "Digital & Innovation Strategy Microservice",
        "version": "1.0.0",
        "techniques": [
            "Digital_Twin", "Blockchain_Strategy", "AI_ML_Strategy",
            "IoT_Strategy", "Cloud_Strategy", "Platform_Strategy",
            "Innovation_Pipeline", "Technology_Roadmap", "Digital_Transformation",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@digital_innovation_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "digital-innovation",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "digital_twin", "blockchain", "ai_ml", "iot",
            "cloud", "platform", "innovation_pipeline",
            "tech_roadmap", "digital_transformation",
        ],
    }

# =============================================================================
# ENDPOINTS — Digital Twin
# =============================================================================


@digital_innovation_app.post("/digital-twin/evaluate")
def digital_twin_evaluate(strategy: DigitalTwinStrategySchema):
    try:
        total_investment = sum(t.investment for t in strategy.twins)
        avg_maturity = sum(t.maturity_level for t in strategy.twins) / len(strategy.twins) if strategy.twins else 0
        by_type = {}
        for t in strategy.twins:
            by_type.setdefault(t.asset_type, []).append(t.asset_name)
        return {
            "success": True,
            "organization": strategy.organization_name,
            "twins_count": len(strategy.twins),
            "total_investment": total_investment,
            "average_maturity": round(avg_maturity, 2),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Blockchain Strategy
# =============================================================================


@digital_innovation_app.post("/blockchain/evaluate")
def blockchain_evaluate(strategy: BlockchainStrategySchema):
    try:
        total_investment = sum(i.investment for i in strategy.initiatives)
        by_use_case = {}
        for i in strategy.initiatives:
            by_use_case.setdefault(i.use_case, []).append(i.initiative_name)
        avg_maturity = sum(i.maturity_level for i in strategy.initiatives) / len(strategy.initiatives) if strategy.initiatives else 0
        return {
            "success": True,
            "organization": strategy.organization_name,
            "initiatives_count": len(strategy.initiatives),
            "total_investment": total_investment,
            "average_maturity": round(avg_maturity, 2),
            "by_use_case": {k: len(v) for k, v in by_use_case.items()},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — AI/ML Strategy
# =============================================================================


@digital_innovation_app.post("/ai-ml/evaluate")
def ai_ml_evaluate(strategy: AIMLStrategySchema):
    try:
        total_investment = sum(i.investment for i in strategy.initiatives)
        by_type = {}
        for i in strategy.initiatives:
            by_type.setdefault(i.ai_type, []).append(i.initiative_name)
        high_impact = [i.initiative_name for i in strategy.initiatives if i.expected_impact in ("HIGH", "CRITICAL")]
        return {
            "success": True,
            "organization": strategy.organization_name,
            "ai_budget_pct": strategy.ai_budget_pct_of_it,
            "initiatives_count": len(strategy.initiatives),
            "total_investment": total_investment,
            "by_type": {k: len(v) for k, v in by_type.items()},
            "high_impact_initiatives": high_impact,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — IoT Strategy
# =============================================================================


@digital_innovation_app.post("/iot/evaluate")
def iot_evaluate(strategy: IoTStrategySchema):
    try:
        total_devices = sum(i.devices_count for i in strategy.initiatives)
        total_data = sum(i.data_volume_gb_daily for i in strategy.initiatives)
        total_investment = sum(i.investment for i in strategy.initiatives)
        by_domain = {}
        for i in strategy.initiatives:
            by_domain.setdefault(i.domain, []).append(i.initiative_name)
        return {
            "success": True,
            "organization": strategy.organization_name,
            "initiatives_count": len(strategy.initiatives),
            "total_devices": total_devices,
            "total_data_daily_gb": round(total_data, 2),
            "total_investment": total_investment,
            "by_domain": {k: len(v) for k, v in by_domain.items()},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Cloud Strategy
# =============================================================================


@digital_innovation_app.post("/cloud/evaluate")
def cloud_evaluate(strategy: CloudStrategySchema):
    try:
        total_monthly = sum(s.monthly_cost for s in strategy.services)
        avg_utilization = sum(s.utilization_pct for s in strategy.services) / len(strategy.services) if strategy.services else 0
        critical_services = [s.service_name for s in strategy.services if s.criticality in ("HIGH", "CRITICAL")]
        by_provider = {}
        for s in strategy.services:
            by_provider.setdefault(s.provider, []).append(s.service_name)
        return {
            "success": True,
            "organization": strategy.organization_name,
            "cloud_budget": strategy.cloud_budget,
            "migration_pct": strategy.current_migration_pct,
            "monthly_cost": round(total_monthly, 2),
            "annual_cost": round(total_monthly * 12, 2),
            "average_utilization": round(avg_utilization, 1),
            "critical_services": critical_services,
            "by_provider": {k: len(v) for k, v in by_provider.items()},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Platform Strategy
# =============================================================================


@digital_innovation_app.post("/platform/evaluate")
def platform_evaluate(strategy: PlatformStrategySchema):
    try:
        results = []
        total_users = 0
        total_devs = 0
        for p in strategy.platforms:
            network_score = p.network_effect_strength * p.users_count / 1000 if p.users_count > 0 else 0
            total_users += p.users_count
            total_devs += p.developers_count
            results.append({
                "platform": p.platform_name,
                "type": p.platform_type,
                "users": p.users_count,
                "developers": p.developers_count,
                "network_score": round(network_score, 2),
                "revenue_model": p.revenue_model,
            })
        return {
            "success": True,
            "organization": strategy.organization_name,
            "platforms_count": len(strategy.platforms),
            "total_users": total_users,
            "total_developers": total_devs,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Innovation Pipeline
# =============================================================================


@digital_innovation_app.post("/pipeline/analyze")
def pipeline_analyze(pipeline: InnovationPipelineSchema):
    try:
        stage_summary = {}
        total_budget = 0
        total_expected_revenue = 0
        for p in pipeline.projects:
            stage_summary.setdefault(p.stage, []).append(p.project_name)
            total_budget += p.budget
            total_expected_revenue += p.expected_revenue
        innovation_mix = {}
        for p in pipeline.projects:
            innovation_mix.setdefault(p.innovation_type, 0)
            innovation_mix[p.innovation_type] += 1
        pipeline_health = "HEALTHY" if len(stage_summary) >= 3 else "UNBALANCED"
        return {
            "success": True,
            "organization": pipeline.organization_name,
            "rd_budget": pipeline.annual_rd_budget,
            "projects_count": len(pipeline.projects),
            "total_project_budget": total_budget,
            "total_expected_revenue": total_expected_revenue,
            "stage_distribution": {k: len(v) for k, v in stage_summary.items()},
            "innovation_mix": innovation_mix,
            "pipeline_health": pipeline_health,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Technology Roadmap
# =============================================================================


@digital_innovation_app.post("/roadmap/analyze")
def roadmap_analyze(roadmap: TechRoadmapSchema):
    try:
        timeline = {}
        total_investment = 0
        for init in roadmap.initiatives:
            timeline.setdefault(init.timeline_quarter, []).append(init.initiative_name)
            total_investment += init.investment
        status_counts = {}
        for init in roadmap.initiatives:
            status_counts[init.status] = status_counts.get(init.status, 0) + 1
        dependency_risks = [init.initiative_name for init in roadmap.initiatives if len(init.dependencies) > 2]
        return {
            "success": True,
            "organization": roadmap.organization_name,
            "roadmap_years": roadmap.roadmap_years,
            "initiatives_count": len(roadmap.initiatives),
            "total_investment": total_investment,
            "timeline": {k: len(v) for k, v in sorted(timeline.items())},
            "status_distribution": status_counts,
            "high_dependency_initiatives": dependency_risks,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Digital Transformation
# =============================================================================


@digital_innovation_app.post("/transformation/assess")
def transformation_assess(data: DigitalTransformationSchema):
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
            })
            weighted_score += d.current_score * d.weight
            total_weight += d.weight
        overall = weighted_score / total_weight if total_weight > 0 else 0
        maturity = "ADVANCED" if overall >= 8 else "DEVELOPING" if overall >= 5 else "EMERGING"
        return {
            "success": True,
            "organization": data.organization_name,
            "dimensions_count": len(data.dimensions),
            "overall_maturity": round(overall, 2),
            "maturity_level": maturity,
            "total_budget": data.total_budget,
            "timeline_years": data.timeline_years,
            "gaps": gaps,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/digital-innovation"):
    parent_app.mount(prefix, digital_innovation_app)
