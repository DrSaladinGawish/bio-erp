"""
Resource & Capability Analysis Organ — Pydantic v2 Schemas
BIO-ERP v5.3.0 — resource_capability_organ
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# 1. VRIO Framework
# =============================================================================


class VRIOResourceSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    value_score: float = Field(
        ...,
        ge=1,
        le=10,
        description="Does it exploit opportunities / neutralize threats?",
    )
    rarity_score: float = Field(
        ..., ge=1, le=10, description="How many competitors control it?"
    )
    imitability_cost: float = Field(
        ..., ge=1, le=10, description="Cost/difficulty to imitate (higher = harder)"
    )
    organization_score: float = Field(
        ..., ge=1, le=10, description="Is the firm organized to capture value?"
    )


class VRIOAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    resources: list[VRIOResourceSchema] = Field(..., min_length=1)


# =============================================================================
# 2. Value Chain Analysis
# =============================================================================


class ValueChainActivityInput(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    cost: float = Field(..., ge=0)
    value_score: float = Field(..., ge=1, le=10)


class PrimaryActivitiesSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    inbound_logistics: ValueChainActivityInput
    operations: ValueChainActivityInput
    outbound_logistics: ValueChainActivityInput
    marketing: ValueChainActivityInput
    service: ValueChainActivityInput


class SupportActivitiesSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    firm_infrastructure: ValueChainActivityInput
    hr: ValueChainActivityInput
    tech_development: ValueChainActivityInput
    procurement: ValueChainActivityInput


class ValueChainAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    primary_activities: PrimaryActivitiesSchema
    support_activities: SupportActivitiesSchema


# =============================================================================
# 3. Core Competency Assessment
# =============================================================================


class CoreCompetencySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    customer_value: float = Field(
        ..., ge=1, le=10, description="Contribution to perceived customer value"
    )
    competitor_rarity: float = Field(
        ..., ge=1, le=10, description="Difficulty for competitors to replicate"
    )
    potential_for_leverage: float = Field(
        ..., ge=1, le=10, description="Access to a wide variety of markets"
    )
    depth_score: float = Field(
        ..., ge=1, le=10, description="Organizational mastery / embeddedness"
    )


class CoreCompetencyAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    competencies: list[CoreCompetencySchema] = Field(..., min_length=1)
    building_horizon_quarters: int = Field(default=8, ge=1, le=20)


# =============================================================================
# 4. Dynamic Capabilities
# =============================================================================


class SensingCapabilitiesSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    market_awareness: float = Field(..., ge=1, le=10)
    technology_scanning: float = Field(..., ge=1, le=10)


class SeizingCapabilitiesSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_speed: float = Field(..., ge=1, le=10)
    resource_mobilization: float = Field(..., ge=1, le=10)


class ReconfiguringCapabilitiesSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organizational_flexibility: float = Field(..., ge=1, le=10)
    learning_rate: float = Field(..., ge=1, le=10)


class DynamicCapabilitiesSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    sensing_capabilities: SensingCapabilitiesSchema
    seizing_capabilities: SeizingCapabilitiesSchema
    reconfiguring_capabilities: ReconfiguringCapabilitiesSchema


# =============================================================================
# 5. Resource Audit
# =============================================================================


class TangibleResourceSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    type: str = Field(
        ..., min_length=1, description="e.g. PLANT, EQUIPMENT, CASH, LAND"
    )
    current_value: float = Field(..., ge=0)
    depreciation_rate_pct: float = Field(..., ge=0, le=100)
    replacement_cost: float = Field(..., ge=0)


class IntangibleResourceSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    type: str = Field(
        ..., min_length=1, description="e.g. BRAND, PATENT, SOFTWARE, REPUTATION"
    )
    estimated_value: float = Field(..., ge=0)
    legal_protection: Literal["NONE", "LOW", "MEDIUM", "HIGH", "REGISTERED"] = "MEDIUM"


class HumanResourceSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    skills: str = Field(
        ..., min_length=1, description="Skill area, e.g. bioinformatics"
    )
    experience_years: float = Field(..., ge=0, le=60)
    headcount: int = Field(default=1, ge=1)
    criticality: float = Field(default=5.0, ge=1, le=10)


class ResourceAuditSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    tangible_resources: list[TangibleResourceSchema] = Field(default_factory=list)
    intangible_resources: list[IntangibleResourceSchema] = Field(default_factory=list)
    human_resources: list[HumanResourceSchema] = Field(default_factory=list)


# =============================================================================
# 6. Capability Mapping
# =============================================================================


class CapabilitySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    current_level: float = Field(..., ge=1, le=10)
    strategic_importance: float = Field(..., ge=1, le=10)
    investment_required: float = Field(default=0.0, ge=0)


class CapabilityMappingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    capabilities: list[CapabilitySchema] = Field(..., min_length=1)


# =============================================================================
# 7. Knowledge Assets Assessment
# =============================================================================


class HumanCapitalSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    expertise_count: int = Field(..., ge=0)
    innovation_output: int = Field(
        ..., ge=0, description="New products/patents/ideas per period"
    )
    avg_expertise_level: float = Field(default=5.0, ge=1, le=10)
    turnover_risk_pct: float = Field(default=10.0, ge=0, le=100)


class StructuralCapitalSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    processes: int = Field(..., ge=0, description="Documented/formalized processes")
    patents: int = Field(..., ge=0)
    databases: int = Field(..., ge=0)
    process_maturity: float = Field(default=5.0, ge=1, le=10)


class RelationalCapitalSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    customer_loyalty_pct: float = Field(..., ge=0, le=100)
    brand_value: float = Field(..., ge=0)


class KnowledgeAssetsSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    human_capital: HumanCapitalSchema
    structural_capital: StructuralCapitalSchema
    relational_capital: RelationalCapitalSchema


# =============================================================================
# 8. Outsourcing Analysis
# =============================================================================


class CostComparisonSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    internal_cost: float = Field(
        ..., ge=0, description="Annual cost to perform in-house"
    )
    external_cost: float = Field(..., ge=0, description="Annual quoted vendor cost")


class OutsourcingActivitySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    strategic_importance: float = Field(..., ge=1, le=10)
    core_competency_fit: float = Field(..., ge=1, le=10)
    cost_comparison: CostComparisonSchema
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    transition_cost: float = Field(default=0.0, ge=0)


class OutsourcingAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    activities: list[OutsourcingActivitySchema] = Field(..., min_length=1)
    contract_years: int = Field(default=3, ge=1, le=10)


# =============================================================================
# GENERIC RESPONSE ENVELOPE
# =============================================================================


class ResourceCapabilityResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    success: bool = True
    technique: str = ""
    result: dict = {}
    interpretation: dict = {}
    timestamp: str = ""
