"""
Strategy Formulation Organ — Pydantic v2 Schemas
BIO-ERP v5.3.0 — strategy_formulation_organ
"""

from pydantic import BaseModel, Field
from typing import List


# =============================================================================
# 1. BCG Matrix
# =============================================================================


class BusinessUnitSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    relative_market_share: float = Field(
        ...,
        description="Share relative to largest competitor (1.0 = parity, >1.0 = leader)",
    )
    market_growth_rate_pct: float = Field(..., description="Annual market growth %")
    revenue: float = Field(default=0.0, ge=0)


class BCGMatrixRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    business_units: List[BusinessUnitSchema] = Field(..., min_length=1)


# =============================================================================
# 2. Ansoff Matrix
# =============================================================================


class ProductSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    maturity: float = Field(
        default=5.0, ge=1, le=10,
        description="Product maturity 1=introductory, 10=declining",
    )
    is_new_to_company: bool = Field(default=False)


class MarketSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    growth_rate_pct: float = Field(default=0.0)
    is_new_to_company: bool = Field(default=False)


class CurrentStateSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    market_share_pct: float = Field(default=10.0, ge=0, le=100)
    product_maturity: float = Field(default=5.0, ge=1, le=10)


class AnsoffRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    products: List[ProductSchema] = Field(..., min_length=1)
    markets: List[MarketSchema] = Field(..., min_length=1)
    current_state: CurrentStateSchema


# =============================================================================
# 3. Blue Ocean Strategy
# =============================================================================


class CompetitorFactorSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    level: float = Field(default=5.0, ge=0, le=10)


class BlueOceanFactorSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    current_level: float = Field(default=5.0, ge=0, le=10)
    importance_to_customer: float = Field(default=5.0, ge=1, le=10)


class BlueOceanRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    factors: List[BlueOceanFactorSchema] = Field(..., min_length=1)
    competitor_factors: List[CompetitorFactorSchema] = Field(default_factory=list)


# =============================================================================
# 4. Porter's Generic Strategies
# =============================================================================


class DifferentiationStrengthSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    strength: float = Field(default=5.0, ge=1, le=10)


class PorterGenericRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    cost_position: float = Field(
        default=5.0, ge=1, le=10,
        description="Cost advantage strength (10 = industry-lowest cost)",
    )
    differentiation_strengths: List[DifferentiationStrengthSchema] = Field(
        ..., min_length=1
    )
    market_scope: str = Field(default="BROAD", description="BROAD or NARROW")
    competitive_scope: str = Field(default="BROAD", description="BROAD or NARROW")


# =============================================================================
# 5. TOWS Strategy
# =============================================================================


class SWOTItemSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    item_name: str = Field(..., min_length=1)
    score: float = Field(default=5.0, ge=1, le=10)


class TOWSRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    strengths: List[SWOTItemSchema] = Field(default_factory=list)
    weaknesses: List[SWOTItemSchema] = Field(default_factory=list)
    opportunities: List[SWOTItemSchema] = Field(default_factory=list)
    threats: List[SWOTItemSchema] = Field(default_factory=list)


# =============================================================================
# 6. Competitive Advantage
# =============================================================================


class AdvantageSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    type: str = Field(
        default="DIFFERENTIATION",
        description="COST, DIFFERENTIATION, NETWORK_EFFECTS, SWITCHING_COSTS, BRAND, REGULATORY, TALENT",
    )
    rarity: float = Field(default=5.0, ge=1, le=10)
    durability: float = Field(default=5.0, ge=1, le=10)
    imitability_score: float = Field(
        default=5.0, ge=1, le=10,
        description="Ease of imitation (10 = trivially easy to copy)",
    )


class CompetitiveAdvantageRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    advantages: List[AdvantageSchema] = Field(..., min_length=1)


# =============================================================================
# 7. Core Competency
# =============================================================================


class CompetencySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    market_relevance: float = Field(
        default=5.0, ge=1, le=10,
        description="Access to a wide variety of markets",
    )
    competitor_rarity: float = Field(default=5.0, ge=1, le=10)
    customer_value: float = Field(
        default=5.0, ge=1, le=10,
        description="Contribution to perceived customer benefits",
    )
    uniqueness: float = Field(default=5.0, ge=1, le=10)


class CoreCompetencyRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    competencies: List[CompetencySchema] = Field(..., min_length=1)


# =============================================================================
# 8. Strategic Intent
# =============================================================================


class ObjectiveSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    description: str = Field(..., min_length=1)
    target_value: float = Field(..., gt=0)
    current_value: float = Field(default=0.0, ge=0)


class StrategicIntentRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    vision: str = Field(default="", min_length=0)
    mission: str = Field(default="", min_length=0)
    objectives: List[ObjectiveSchema] = Field(default_factory=list)
    current_performance: float = Field(
        default=0.0, ge=0, le=100,
        description="Overall performance index 0-100 vs ambition baseline",
    )
    gap_to_ambition_pct: float = Field(
        default=0.0, ge=0,
        description="Gap between current state and ambition level (%)",
    )


# =============================================================================
# 9. Value Innovation
# =============================================================================


class BenchmarkElementSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    cost: float = Field(default=0.0, ge=0)
    perceived_value: float = Field(default=5.0, ge=0, le=10)


class ValueElementSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    current_cost: float = Field(default=0.0, ge=0)
    customer_perceived_value: float = Field(default=5.0, ge=0, le=10)


class ValueInnovationRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    value_elements: List[ValueElementSchema] = Field(..., min_length=1)
    competitor_benchmark: List[BenchmarkElementSchema] = Field(default_factory=list)


# =============================================================================
# 10. Disruptive Innovation
# =============================================================================


class MarketSegmentSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    size: float = Field(
        default=100.0, gt=0,
        description="Segment size in addressable customers or revenue units",
    )
    growth_rate_pct: float = Field(default=0.0)
    current_satisfaction: float = Field(
        default=5.0, ge=1, le=10,
        description="Incumbent-served satisfaction (10 = fully satisfied)",
    )
    technology_trajectory: float = Field(
        default=1.0,
        description="Annual improvement rate of relevant technology (multiplier)",
    )


class DisruptiveInnovationRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    market_segments: List[MarketSegmentSchema] = Field(..., min_length=1)


# =============================================================================
# 11. Platform Strategy
# =============================================================================


class NetworkEffectsSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    same_side_strength: float = Field(
        default=5.0, ge=1, le=10,
        description="Value of more users of the SAME type to each user",
    )
    cross_side_strength: float = Field(
        default=5.0, ge=1, le=10,
        description="Value of one side's participation to the OTHER side",
    )


class EcosystemPartnerSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    role: str = Field(default="DEVELOPER", description="DEVELOPER, SUPPLIER, CHANNEL, COMPLEMENTOR")
    strength: float = Field(default=5.0, ge=1, le=10)


class PlatformStrategyRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    platform_type: str = Field(
        default="PRODUCT", description="PRODUCT, SERVICE, or DATA"
    )
    network_effects: NetworkEffectsSchema
    switching_costs: float = Field(default=5.0, ge=1, le=10)
    ecosystem_partners: List[EcosystemPartnerSchema] = Field(default_factory=list)


# =============================================================================
# 12. Ecosystem Strategy
# =============================================================================


class EcosystemActorSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    role: str = Field(
        default="COMPLEMENTOR",
        description="KEYSTONE, SUPPLIER, COMPLEMENTOR, CUSTOMER, REGULATOR, COMPETITOR",
    )
    value_creation: float = Field(default=5.0, ge=1, le=10)
    dependency_level: float = Field(
        default=5.0, ge=1, le=10,
        description="How much WE depend on this actor",
    )
    relationship_strength: float = Field(default=5.0, ge=1, le=10)


class EcosystemStrategyRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    actors: List[EcosystemActorSchema] = Field(..., min_length=1)
