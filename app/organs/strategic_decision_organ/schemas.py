"""
Strategic Decision-Making Schemas — Pydantic v2
BIO-ERP v5.3.0 — strategic_decision_organ
"""

from pydantic import BaseModel, Field
from typing import List

model_config = {"json_schema_extra": {"examples": []}}


# =============================================================================
# 1. AHP (Analytic Hierarchy Process)
# =============================================================================


class AHPPairwiseComparison(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)
    value: float = Field(..., gt=0, description="Saaty scale 1-9")


class AHPSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    criteria_names: List[str] = Field(..., min_length=2)
    comparison_matrix: List[List[float]] = Field(
        ..., description="n×n pairwise comparison matrix"
    )
    alternatives: List[str] = Field(..., min_length=2)
    alternative_scores: List[List[float]] = Field(
        ..., description="alternatives×criteria score matrix"
    )


# =============================================================================
# 2. Real Options Analysis
# =============================================================================


class RealOptionsSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    initial_investment: float = Field(..., gt=0)
    project_value: float = Field(..., gt=0)
    volatility: float = Field(..., gt=0, le=3.0)
    risk_free_rate: float = Field(..., ge=0, le=1.0)
    time_to_expiry: float = Field(..., gt=0, le=30.0, description="Years")
    n_steps: int = Field(default=100, ge=10, le=10000)


# =============================================================================
# 3. Decision Trees
# =============================================================================


class DecisionTreeBranch(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    branch_name: str = Field(..., min_length=1)
    probability: float = Field(default=1.0, ge=0, le=1)
    payoff: float = Field(default=0.0)
    cost: float = Field(default=0.0, ge=0)


class DecisionTreeNode(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    node_id: str = Field(..., min_length=1)
    node_type: str = Field(..., description="DECISION or CHANCE")
    label: str = Field(default="")
    branches: List[DecisionTreeBranch]


class DecisionTreeSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    nodes: List[DecisionTreeNode]
    root_node_id: str = Field(..., min_length=1)


# =============================================================================
# 4. Cost-Benefit Analysis
# =============================================================================


class CashFlowItem(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    timing: int = Field(..., ge=0, description="Year (0=now)")
    category: str = Field(default="OPERATIONAL")


class CostBenefitSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    costs: List[CashFlowItem]
    benefits: List[CashFlowItem]
    discount_rate: float = Field(default=0.08, ge=0, le=1.0)
    project_life: int = Field(default=5, ge=1, le=50)


# =============================================================================
# 5. MCDA (Multi-Criteria Decision Analysis)
# =============================================================================


class MCDMCriterion(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    weight: float = Field(..., gt=0, le=10)
    criterion_type: str = Field(default="BENEFIT", description="BENEFIT or COST")


class MCDAAltScores(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    alternative_name: str = Field(..., min_length=1)
    scores: List[float] = Field(..., min_length=1)


class MCDASchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    alternatives: List[str] = Field(..., min_length=2)
    criteria: List[MCDMCriterion] = Field(..., min_length=2)
    performance_matrix: List[List[float]] = Field(
        ..., description="alternatives×criteria raw scores"
    )


# =============================================================================
# 6. Game Theory
# =============================================================================


class GameTheorySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    player1_strategies: List[str] = Field(..., min_length=2)
    player2_strategies: List[str] = Field(..., min_length=2)
    payoff_matrix: List[List[List[float]]] = Field(
        ..., description="player1_payoffs[i][j] = [p1, p2]"
    )
    game_type: str = Field(
        default="NON_ZERO_SUM", description="ZERO_SUM or NON_ZERO_SUM"
    )


# =============================================================================
# 7. Sensitivity Analysis
# =============================================================================


class SensitivityVariable(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    base_value: float = Field(...)
    low_value: float = Field(...)
    high_value: float = Field(...)
    unit: str = Field(default="%")


class SensitivityAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    base_outcome: float = Field(...)
    variables: List[SensitivityVariable] = Field(..., min_length=1)
    variation_pct: float = Field(default=10.0, gt=0, le=100)


# =============================================================================
# 8. Risk-Reward Analysis
# =============================================================================


class RiskRewardOption(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    expected_return: float = Field(
        ..., description="Expected return (e.g., 0.15 for 15%)"
    )
    risk_std: float = Field(..., gt=0, description="Standard deviation of returns")
    weight: float = Field(default=0.0, ge=0, le=1, description="Portfolio weight")


class RiskRewardSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    risk_free_rate: float = Field(default=0.05, ge=0, le=1.0)
    options: List[RiskRewardOption] = Field(..., min_length=2)


# =============================================================================
# 9. Delphi Method
# =============================================================================


class DelphiRound(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    round_number: int = Field(..., ge=1)
    scores: List[float] = Field(..., min_length=1)


class DelphiSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    experts: List[str] = Field(..., min_length=2)
    rounds: List[DelphiRound] = Field(..., min_length=1)


# =============================================================================
# 10. Strategic Choice
# =============================================================================


class StrategicOption(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    criteria_scores: dict = Field(
        default_factory=dict, description="criterion -> score (0-10)"
    )
    risk_score: float = Field(default=5.0, ge=0, le=10)
    financial_attractiveness: float = Field(default=5.0, ge=0, le=10)
    implementation_effort: float = Field(default=5.0, ge=0, le=10)


class StrategicChoiceSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    decision_name: str = Field(..., min_length=1)
    options: List[StrategicOption] = Field(..., min_length=2)
    criteria_weights: dict = Field(
        default_factory=dict, description="criterion -> weight"
    )
    risk_tolerance: str = Field(default="MODERATE", description="LOW, MODERATE, HIGH")


# =============================================================================
# GENERIC RESPONSE
# =============================================================================


class StrategicDecisionResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    success: bool = True
    technique: str = ""
    result: dict = {}
    interpretation: str = ""
    timestamp: str = ""
