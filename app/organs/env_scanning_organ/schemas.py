"""
Environmental Scanning Organ — Pydantic v2 Schemas
BIO-ERP v5.3.0 — env_scanning_organ

10 Techniques: PESTEL, SWOT, Scenario Planning, Competitor Intelligence,
Customer Analysis, Trend Analysis, Benchmarking, Market Research,
Stakeholder Mapping, Environmental Assessment
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# =============================================================================
# SHARED ENUMS
# =============================================================================

class PESTELCategory(str, Enum):
    POLITICAL = "Political"
    ECONOMIC = "Economic"
    SOCIAL = "Social"
    TECHNOLOGICAL = "Technological"
    ENVIRONMENTAL = "Environmental"
    LEGAL = "Legal"


class SWOTQuadrant(str, Enum):
    STRENGTHS = "Strengths"
    WEAKNESSES = "Weaknesses"
    OPPORTUNITIES = "Opportunities"
    THREATS = "Threats"


class AttitudeType(str, Enum):
    SUPPORTER = "supporter"
    NEUTRAL = "neutral"
    OPPONENT = "opponent"


# =============================================================================
# 1. PESTEL ANALYSIS
# =============================================================================

class PESTELFactorSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    factor_name: str = Field(..., min_length=1)
    description: str = Field(default="")
    impact_score: float = Field(..., ge=1, le=10, description="1-10 impact rating")
    probability: float = Field(..., ge=0, le=1, description="0-1 probability")


class PESTELAnalysisRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    political: List[PESTELFactorSchema] = Field(default_factory=list)
    economic: List[PESTELFactorSchema] = Field(default_factory=list)
    social: List[PESTELFactorSchema] = Field(default_factory=list)
    technological: List[PESTELFactorSchema] = Field(default_factory=list)
    environmental: List[PESTELFactorSchema] = Field(default_factory=list)
    legal: List[PESTELFactorSchema] = Field(default_factory=list)


# =============================================================================
# 2. SWOT ANALYSIS
# =============================================================================

class SWOTItemSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    item_name: str = Field(..., min_length=1)
    category: str = Field(default="")
    description: str = Field(default="")
    impact_score: float = Field(..., ge=1, le=10)
    urgency: int = Field(..., ge=1, le=5)


class SWOTAnalysisRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    strengths: List[SWOTItemSchema] = Field(default_factory=list)
    weaknesses: List[SWOTItemSchema] = Field(default_factory=list)
    opportunities: List[SWOTItemSchema] = Field(default_factory=list)
    threats: List[SWOTItemSchema] = Field(default_factory=list)


# =============================================================================
# 3. SCENARIO PLANNING
# =============================================================================

class ScenarioVariableSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    low_value: float = Field(default=0.0)
    high_value: float = Field(default=1.0)


class ScenarioSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    probability: float = Field(default=0.25, ge=0, le=1)
    description: str = Field(default="")
    variables: dict = Field(default_factory=dict, description="variable_name -> value")
    strategic_implications: List[str] = Field(default_factory=list)


class ScenarioPlanningRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    uncertainty_x: str = Field(..., min_length=1, description="High-impact uncertainty X axis")
    uncertainty_y: str = Field(..., min_length=1, description="High-impact uncertainty Y axis")
    planning_horizon_years: int = Field(default=5, ge=1, le=30)
    scenarios: List[ScenarioSchema] = Field(
        default_factory=list,
        description="2-4 scenarios for the quadrant matrix",
    )


# =============================================================================
# 4. COMPETITOR INTELLIGENCE
# =============================================================================

class CompetitorSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    market_share: float = Field(default=0.0, ge=0, le=100)
    price_score: float = Field(default=5.0, ge=1, le=10, description="1=low price, 10=premium")
    quality_score: float = Field(default=5.0, ge=1, le=10)
    innovation_score: float = Field(default=5.0, ge=1, le=10)
    market_presence_score: float = Field(default=5.0, ge=1, le=10)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recent_moves: List[str] = Field(default_factory=list)


class CompetitorIntelligenceRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    industry: str = Field(default="")
    our_price_score: float = Field(default=5.0, ge=1, le=10)
    our_quality_score: float = Field(default=5.0, ge=1, le=10)
    our_innovation_score: float = Field(default=5.0, ge=1, le=10)
    our_market_presence_score: float = Field(default=5.0, ge=1, le=10)
    competitors: List[CompetitorSchema] = Field(default_factory=list)


# =============================================================================
# 5. CUSTOMER ANALYSIS
# =============================================================================

class CustomerSegmentSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    size: int = Field(..., ge=0, description="Number of customers or market size")
    growth_rate: float = Field(default=0.0, description="Annual growth rate %")
    satisfaction_score: float = Field(default=5.0, ge=1, le=10)
    willingness_to_pay: float = Field(default=5.0, ge=1, le=10)
    retention_rate: float = Field(default=80.0, ge=0, le=100, description="Annual retention %")
    average_revenue: float = Field(default=0.0, ge=0)


class CustomerAnalysisRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    segments: List[CustomerSegmentSchema] = Field(default_factory=list)
    discount_rate_pct: float = Field(default=10.0, ge=0, le=50)


# =============================================================================
# 6. TREND ANALYSIS
# =============================================================================

class TimeSeriesPointSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    period: str = Field(..., min_length=1, description="e.g. 2024-Q1, 2024-01")
    metric_name: str = Field(..., min_length=1)
    value: float = Field(default=0.0)


class TrendAnalysisRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    data_points: List[TimeSeriesPointSchema] = Field(default_factory=list)
    forecast_periods: int = Field(default=3, ge=1, le=12)


# =============================================================================
# 7. BENCHMARKING
# =============================================================================

class BenchmarkMetricSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    metric_name: str = Field(..., min_length=1)
    your_value: float = Field(default=0.0)
    industry_benchmark: float = Field(default=0.0)
    best_in_class: float = Field(default=0.0)
    unit: str = Field(default="")
    higher_is_better: bool = Field(default=True)


class BenchmarkingRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    metrics: List[BenchmarkMetricSchema] = Field(default_factory=list)


# =============================================================================
# 8. MARKET RESEARCH
# =============================================================================

class MarketResearchRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    market_name: str = Field(..., min_length=1)
    tam: float = Field(..., ge=0, description="Total Addressable Market")
    sam: float = Field(..., ge=0, description="Serviceable Addressable Market")
    som: float = Field(..., ge=0, description="Serviceable Obtainable Market")
    growth_rate_pct: float = Field(default=0.0)
    competitive_intensity: float = Field(default=5.0, ge=1, le=10, description="1=low, 10=hyper")
    barriers_to_entry: float = Field(default=5.0, ge=1, le=10, description="1=low, 10=high")
    regulatory_risk: float = Field(default=5.0, ge=1, le=10)
    technology_risk: float = Field(default=5.0, ge=1, le=10)


# =============================================================================
# 9. STAKEHOLDER MAPPING
# =============================================================================

class StakeholderSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    power_score: int = Field(..., ge=1, le=10)
    interest_score: int = Field(..., ge=1, le=10)
    attitude: AttitudeType = Field(default=AttitudeType.NEUTRAL)
    influence_notes: str = Field(default="")


class StakeholderMappingRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    stakeholders: List[StakeholderSchema] = Field(default_factory=list)


# =============================================================================
# 10. ENVIRONMENTAL ASSESSMENT (COMPREHENSIVE)
# =============================================================================

class EnvironmentalAssessmentRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    assessment_name: str = Field(default="Comprehensive Environmental Assessment")
    pestel_score: Optional[float] = Field(default=None, ge=0, le=100)
    swot_score: Optional[float] = Field(default=None, ge=-100, le=100)
    competitor_score: Optional[float] = Field(default=None, ge=0, le=100)
    trend_score: Optional[float] = Field(default=None, ge=0, le=100)
    market_score: Optional[float] = Field(default=None, ge=0, le=100)
    top_issues: List[str] = Field(default_factory=list)
    custom_weights: Optional[dict] = Field(
        default=None,
        description="Override default weights: pestel, swot, competitor, trend, market",
    )
