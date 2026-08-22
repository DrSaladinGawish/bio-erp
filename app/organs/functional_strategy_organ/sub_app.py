"""
Functional-Level Strategy Sub-Application for BIO-ERP v5
=========================================================
Mount at: app.mount("/api/v1/functional-strategy", functional_strategy_app) in BIO-ERP's main.py

Techniques: Operations Strategy, Marketing Strategy, HR Strategy, Financial Strategy,
            IT Strategy, Supply Chain Strategy, R&D Strategy, Quality Management
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

functional_strategy_app = FastAPI(
    title="Functional-Level Strategy Microservice",
    description="Functional Strategy Analysis — Operations, Marketing, HR, Financial, IT, Supply Chain, R&D, Quality Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — Operations Strategy
# =============================================================================


class OperationsMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    target_value: float = Field(...)
    unit: str = Field(default="")
    priority: int = Field(default=3, ge=1, le=5)


class OperationsStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    focus_areas: List[str] = Field(default_factory=list)
    metrics: List[OperationsMetricSchema]
    capacity_utilization_pct: float = Field(default=50.0, ge=0, le=100)
    oee_pct: float = Field(default=50.0, ge=0, le=100, description="Overall Equipment Effectiveness")

# =============================================================================
# PYDANTIC SCHEMAS — Marketing Strategy
# =============================================================================


class MarketingChannelSchema(BaseModel):
    channel_name: str = Field(..., min_length=1)
    budget: float = Field(default=0.0, ge=0)
    expected_reach: int = Field(default=0, ge=0)
    conversion_rate_pct: float = Field(default=0.0, ge=0, le=100)
    roi_pct: float = Field(default=0.0)


class MarketingStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    target_segments: List[str] = Field(default_factory=list)
    channels: List[MarketingChannelSchema]
    total_marketing_budget: float = Field(..., gt=0)
    brand_awareness_score: float = Field(default=5.0, ge=1, le=10)

# =============================================================================
# PYDANTIC SCHEMAS — HR Strategy
# =============================================================================


class HRMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    target_value: float = Field(...)
    unit: str = Field(default="")


class HRStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    headcount: int = Field(default=0, ge=0)
    turnover_rate_pct: float = Field(default=0.0, ge=0, le=100)
    engagement_score: float = Field(default=5.0, ge=1, le=10)
    metrics: List[HRMetricSchema]
    key_initiatives: List[str] = Field(default_factory=list)

# =============================================================================
# PYDANTIC SCHEMAS — Financial Strategy
# =============================================================================


class FinancialMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    target_value: float = Field(...)
    benchmark_value: float = Field(default=0.0)


class FinancialStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    total_revenue: float = Field(default=0.0, ge=0)
    total_assets: float = Field(default=0.0, ge=0)
    debt_to_equity: float = Field(default=0.0, ge=0)
    metrics: List[FinancialMetricSchema]
    funding_sources: List[str] = Field(default_factory=list)

# =============================================================================
# PYDANTIC SCHEMAS — IT Strategy
# =============================================================================


class ITInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    category: str = Field(default="INFRASTRUCTURE", description="INFRASTRUCTURE, APPLICATION, SECURITY, DATA")
    budget: float = Field(default=0.0, ge=0)
    timeline_months: int = Field(default=6, ge=1, le=60)
    priority: int = Field(default=3, ge=1, le=5)
    expected_benefit: str = Field(default="")


class ITStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    total_it_budget: float = Field(..., gt=0)
    current_satisfaction: float = Field(default=5.0, ge=1, le=10)
    digital_maturity: float = Field(default=3.0, ge=1, le=5)
    initiatives: List[ITInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Supply Chain Strategy
# =============================================================================


class SCMMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    target_value: float = Field(...)
    unit: str = Field(default="")


class SupplyChainStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    supplier_count: int = Field(default=0, ge=0)
    on_time_delivery_pct: float = Field(default=0.0, ge=0, le=100)
    inventory_turns: float = Field(default=0.0, ge=0)
    lead_time_days: float = Field(default=0.0, ge=0)
    metrics: List[SCMMetricSchema]
    key_initiatives: List[str] = Field(default_factory=list)

# =============================================================================
# PYDANTIC SCHEMAS — R&D Strategy
# =============================================================================


class RDProjectSchema(BaseModel):
    project_name: str = Field(..., min_length=1)
    stage: str = Field(..., description="IDEATION, DEVELOPMENT, TESTING, LAUNCH")
    budget: float = Field(default=0.0, ge=0)
    expected_timeline_months: int = Field(default=12, ge=1, le=120)
    success_probability_pct: float = Field(default=50.0, ge=0, le=100)
    strategic_alignment: float = Field(default=5.0, ge=1, le=10)


class RDStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    rd_budget_pct_of_revenue: float = Field(default=5.0, ge=0, le=50)
    patents_filed: int = Field(default=0, ge=0)
    projects: List[RDProjectSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Quality Management
# =============================================================================


class QualityMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    target_value: float = Field(...)
    unit: str = Field(default="")
    category: str = Field(default="DEFECT_RATE", description="DEFECT_RATE, CUSTOMER_SATISFACTION, PROCESS_CAPABILITY, COMPLIANCE")


class QualityManagementSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    certifications: List[str] = Field(default_factory=list)
    metrics: List[QualityMetricSchema]
    six_sigma_level: float = Field(default=3.0, ge=1, le=6)
    cost_of_quality_pct: float = Field(default=5.0, ge=0, le=50, description="Percentage of revenue")

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@functional_strategy_app.get("/")
def root():
    return {
        "service": "Functional-Level Strategy Microservice",
        "version": "1.0.0",
        "techniques": [
            "Operations_Strategy", "Marketing_Strategy", "HR_Strategy",
            "Financial_Strategy", "IT_Strategy", "Supply_Chain_Strategy",
            "RD_Strategy", "Quality_Management",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@functional_strategy_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "functional-strategy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "operations", "marketing", "hr", "financial",
            "it", "supply_chain", "rd", "quality",
        ],
    }

# =============================================================================
# ENDPOINTS — Operations Strategy
# =============================================================================


@functional_strategy_app.post("/operations/analyze")
def operations_analyze(strategy: OperationsStrategySchema):
    try:
        metric_results = []
        for m in strategy.metrics:
            progress = (m.current_value / m.target_value * 100) if m.target_value != 0 else 0
            metric_results.append({
                "metric": m.metric_name,
                "progress_pct": round(progress, 1),
                "status": "ON_TRACK" if progress >= 90 else "AT_RISK" if progress >= 70 else "BEHIND",
            })
        return {
            "success": True,
            "organization": strategy.organization_name,
            "capacity_utilization": strategy.capacity_utilization_pct,
            "oee": strategy.oee_pct,
            "focus_areas": strategy.focus_areas,
            "metrics": metric_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Marketing Strategy
# =============================================================================


@functional_strategy_app.post("/marketing/analyze")
def marketing_analyze(strategy: MarketingStrategySchema):
    try:
        channel_results = []
        total_spend = 0
        total_reach = 0
        for ch in strategy.channels:
            efficiency = ch.expected_reach / ch.budget if ch.budget > 0 else 0
            total_spend += ch.budget
            total_reach += ch.expected_reach
            channel_results.append({
                "channel": ch.channel_name,
                "budget": ch.budget,
                "reach": ch.expected_reach,
                "roi": ch.roi_pct,
                "efficiency": round(efficiency, 2),
            })
        budget_utilization = (total_spend / strategy.total_marketing_budget * 100) if strategy.total_marketing_budget > 0 else 0
        return {
            "success": True,
            "organization": strategy.organization_name,
            "target_segments": strategy.target_segments,
            "total_budget": strategy.total_marketing_budget,
            "budget_utilization_pct": round(budget_utilization, 1),
            "total_reach": total_reach,
            "brand_awareness": strategy.brand_awareness_score,
            "channels": channel_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — HR Strategy
# =============================================================================


@functional_strategy_app.post("/hr/analyze")
def hr_analyze(strategy: HRStrategySchema):
    try:
        metric_results = []
        for m in strategy.metrics:
            progress = (m.current_value / m.target_value * 100) if m.target_value != 0 else 0
            metric_results.append({
                "metric": m.metric_name,
                "progress_pct": round(progress, 1),
            })
        health = "HEALTHY" if strategy.engagement_score >= 7 and strategy.turnover_rate_pct <= 15 else "AT_RISK"
        return {
            "success": True,
            "organization": strategy.organization_name,
            "headcount": strategy.headcount,
            "turnover_rate": strategy.turnover_rate_pct,
            "engagement_score": strategy.engagement_score,
            "health_status": health,
            "metrics": metric_results,
            "initiatives": strategy.key_initiatives,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Financial Strategy
# =============================================================================


@functional_strategy_app.post("/financial/analyze")
def financial_analyze(strategy: FinancialStrategySchema):
    try:
        metric_results = []
        for m in strategy.metrics:
            gap = m.target_value - m.current_value
            benchmark_gap = m.current_value - m.benchmark_value if m.benchmark_value else None
            metric_results.append({
                "metric": m.metric_name,
                "current": m.current_value,
                "target": m.target_value,
                "gap": round(gap, 2),
                "vs_benchmark": round(benchmark_gap, 2) if benchmark_gap is not None else None,
            })
        return {
            "success": True,
            "organization": strategy.organization_name,
            "total_revenue": strategy.total_revenue,
            "total_assets": strategy.total_assets,
            "debt_to_equity": strategy.debt_to_equity,
            "funding_sources": strategy.funding_sources,
            "metrics": metric_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — IT Strategy
# =============================================================================


@functional_strategy_app.post("/it/analyze")
def it_analyze(strategy: ITStrategySchema):
    try:
        budget_by_category = {}
        priority_items = []
        for init in strategy.initiatives:
            budget_by_category.setdefault(init.category, 0)
            budget_by_category[init.category] += init.budget
            if init.priority >= 4:
                priority_items.append(init.initiative_name)
        total_initiative_budget = sum(init.budget for init in strategy.initiatives)
        return {
            "success": True,
            "organization": strategy.organization_name,
            "total_it_budget": strategy.total_it_budget,
            "digital_maturity": strategy.digital_maturity,
            "satisfaction": strategy.current_satisfaction,
            "initiatives_count": len(strategy.initiatives),
            "budget_by_category": budget_by_category,
            "high_priority_initiatives": priority_items,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Supply Chain Strategy
# =============================================================================


@functional_strategy_app.post("/supply-chain/analyze")
def supply_chain_analyze(strategy: SupplyChainStrategySchema):
    try:
        metric_results = []
        for m in strategy.metrics:
            progress = (m.current_value / m.target_value * 100) if m.target_value != 0 else 0
            metric_results.append({
                "metric": m.metric_name,
                "current": m.current_value,
                "target": m.target_value,
                "progress_pct": round(progress, 1),
            })
        supply_chain_health = "STRONG" if strategy.on_time_delivery_pct >= 95 and strategy.inventory_turns >= 8 else \
                              "ADEQUATE" if strategy.on_time_delivery_pct >= 85 else "WEAK"
        return {
            "success": True,
            "organization": strategy.organization_name,
            "supplier_count": strategy.supplier_count,
            "on_time_delivery": strategy.on_time_delivery_pct,
            "inventory_turns": strategy.inventory_turns,
            "lead_time_days": strategy.lead_time_days,
            "health_status": supply_chain_health,
            "metrics": metric_results,
            "initiatives": strategy.key_initiatives,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — R&D Strategy
# =============================================================================


@functional_strategy_app.post("/rd/analyze")
def rd_analyze(strategy: RDStrategySchema):
    try:
        stage_summary = {}
        total_budget = 0
        for proj in strategy.projects:
            stage_summary.setdefault(proj.stage, []).append(proj.project_name)
            total_budget += proj.budget
        avg_probability = sum(p.success_probability_pct for p in strategy.projects) / len(strategy.projects) if strategy.projects else 0
        avg_alignment = sum(p.strategic_alignment for p in strategy.projects) / len(strategy.projects) if strategy.projects else 0
        return {
            "success": True,
            "organization": strategy.organization_name,
            "rd_budget_pct": strategy.rd_budget_pct_of_revenue,
            "patents_filed": strategy.patents_filed,
            "projects_count": len(strategy.projects),
            "total_project_budget": total_budget,
            "stage_distribution": {k: len(v) for k, v in stage_summary.items()},
            "average_success_probability": round(avg_probability, 1),
            "average_strategic_alignment": round(avg_alignment, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Quality Management
# =============================================================================


@functional_strategy_app.post("/quality/analyze")
def quality_analyze(strategy: QualityManagementSchema):
    try:
        metric_results = []
        total_gap = 0
        for m in strategy.metrics:
            gap = m.target_value - m.current_value
            total_gap += abs(gap)
            metric_results.append({
                "metric": m.metric_name,
                "current": m.current_value,
                "target": m.target_value,
                "gap": round(gap, 2),
                "category": m.category,
            })
        quality_maturity = "ADVANCED" if strategy.six_sigma_level >= 5 else \
                           "INTERMEDIATE" if strategy.six_sigma_level >= 3 else "BASIC"
        return {
            "success": True,
            "organization": strategy.organization_name,
            "certifications": strategy.certifications,
            "six_sigma_level": strategy.six_sigma_level,
            "cost_of_quality_pct": strategy.cost_of_quality_pct,
            "quality_maturity": quality_maturity,
            "total_gap": round(total_gap, 2),
            "metrics": metric_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/functional-strategy"):
    parent_app.mount(prefix, functional_strategy_app)
