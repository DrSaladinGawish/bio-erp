from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# =============================================================================
# 1. Value at Risk (VaR)
# =============================================================================


class VaRMethod(str, Enum):
    PARAMETRIC = "PARAMETRIC"
    HISTORICAL = "HISTORICAL"
    MONTE_CARLO = "MONTE_CARLO"


class PortfolioPosition(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    asset_name: str = Field(..., min_length=1)
    weight: float = Field(..., gt=0, le=1.0)
    expected_return: float = Field(..., description="Annual expected return")
    volatility: float = Field(..., gt=0, description="Annual volatility")


class VaRCalculationSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    portfolio_name: str = Field(..., min_length=1)
    positions: List[PortfolioPosition]
    method: VaRMethod = Field(default=VaRMethod.PARAMETRIC)
    confidence_level: float = Field(default=0.95, gt=0.9, lt=1.0)
    time_horizon_days: int = Field(default=1, ge=1, le=365)
    portfolio_value: float = Field(..., gt=0, description="Total portfolio value in currency")
    historical_returns: Optional[List[float]] = Field(
        default=None,
        description="Historical daily returns (for historical method)",
    )
    n_simulations: int = Field(default=10000, ge=1000, le=1000000)


# =============================================================================
# 2. Monte Carlo Simulation
# =============================================================================


class DistributionType(str, Enum):
    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"


class MonteCarloVariable(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    distribution: DistributionType
    mean: float = Field(default=0.0)
    std: float = Field(default=1.0, gt=0)
    min_val: Optional[float] = Field(default=None)
    max_val: Optional[float] = Field(default=None)
    mode: Optional[float] = Field(default=None, description="Mode for triangular distribution")


class MonteCarloSimulationSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    simulation_name: str = Field(..., min_length=1)
    variables: List[MonteCarloVariable]
    n_simulations: int = Field(default=10000, ge=1000, le=1000000)
    seed: Optional[int] = Field(default=None)
    output_function: Optional[str] = Field(
        default=None,
        description="Optional: name of registered output function",
    )


# =============================================================================
# 3. Black Swan Detection
# =============================================================================


class BlackSwanDetectionSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    series_name: str = Field(..., min_length=1)
    time_series: List[float] = Field(..., min_length=3)
    sigma_threshold: float = Field(default=3.0, gt=0, le=6.0)
    dates: Optional[List[str]] = Field(default=None)


# =============================================================================
# 4. Sensitivity Analysis
# =============================================================================


class SensitivityVariable(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    base_value: float = Field(..., description="Base case value")
    low_delta_pct: float = Field(
        default=-10.0,
        description="Percentage decrease from base (negative)",
    )
    high_delta_pct: float = Field(
        default=10.0,
        description="Percentage increase from base (positive)",
    )


class SensitivityAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    analysis_name: str = Field(..., min_length=1)
    variables: List[SensitivityVariable]
    base_case_output: float = Field(..., description="Base case output value")
    output_unit: str = Field(default="$", description="Unit of the output")


# =============================================================================
# 5. Decision Trees
# =============================================================================


class NodeType(str, Enum):
    DECISION = "decision"
    CHANCE = "chance"
    TERMINAL = "terminal"


class TreeNode(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    node_id: str = Field(..., min_length=1)
    node_type: NodeType
    label: str = Field(default="")
    probability: Optional[float] = Field(
        default=None,
        ge=0,
        le=1.0,
        description="Required for chance nodes",
    )
    payoff: Optional[float] = Field(
        default=None,
        description="Required for terminal nodes",
    )
    cost: Optional[float] = Field(default=0.0, description="Cost associated with this node")
    parent_id: Optional[str] = Field(default=None)


class DecisionTreeSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    tree_name: str = Field(..., min_length=1)
    nodes: List[TreeNode]
    risk_aversion_factor: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0=risk neutral, 1=fully risk averse",
    )


# =============================================================================
# 6. Scenario Analysis
# =============================================================================


class Scenario(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    probability: float = Field(..., ge=0, le=1.0)
    output_value: float = Field(..., description="Outcome value for this scenario")
    variables: Optional[dict] = Field(
        default=None,
        description="Optional variable values for this scenario",
    )


class ScenarioAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    analysis_name: str = Field(..., min_length=1)
    output_metric: str = Field(
        default="profit",
        description="Name of the output metric being analyzed",
    )
    scenarios: List[Scenario]
    risk_free_rate_pct: float = Field(default=0.0, ge=0)


# =============================================================================
# GENERIC RESPONSE
# =============================================================================


class RiskUncertaintyResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    success: bool = True
    technique: str = ""
    result: dict = {}
    interpretation: str = ""
    timestamp: str = ""
