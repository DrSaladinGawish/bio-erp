from datetime import date
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class TargetCostingCreate(BaseModel):
    event_id: Optional[int] = None
    target_price: float
    target_margin_pct: float
    current_cost: float = 0.0
    notes: Optional[str] = None


class TargetCostingResponse(BaseModel):
    id: int
    event_id: Optional[int] = None
    target_price: float
    target_margin_pct: float
    target_cost: float
    current_cost: float
    cost_gap: float
    gap_pct: float
    status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LifeCycleCostCreate(BaseModel):
    event_id: int
    phase: str
    category: str
    description: Optional[str] = None
    planned_amount: float = 0.0
    actual_amount: float = 0.0
    cost_driver: Optional[str] = None
    driver_quantity: float = 0.0
    unit_cost: float = 0.0


class LifeCycleCostResponse(BaseModel):
    id: int
    event_id: int
    phase: str
    category: str
    description: Optional[str] = None
    planned_amount: float
    actual_amount: float
    variance: float
    cost_driver: Optional[str] = None
    driver_quantity: float
    unit_cost: float

    model_config = ConfigDict(from_attributes=True)


class ActivityCostPoolCreate(BaseModel):
    event_id: Optional[int] = None
    pool_name: str
    cost_driver: str
    total_cost: float = 0.0
    driver_quantity: float = 0.0
    notes: Optional[str] = None


class ActivityCostPoolResponse(BaseModel):
    id: int
    event_id: Optional[int] = None
    pool_name: str
    cost_driver: str
    total_cost: float
    driver_quantity: float
    cost_driver_rate: float
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ValueChainCreate(BaseModel):
    event_id: int
    activity_name: str
    activity_type: str
    cost: float = 0.0
    revenue_attributable: float = 0.0
    benchmark_cost: Optional[float] = None
    notes: Optional[str] = None


class ValueChainResponse(BaseModel):
    id: int
    event_id: int
    activity_name: str
    activity_type: str
    cost: float
    revenue_attributable: float
    value_added: float
    value_added_pct: float
    benchmark_cost: Optional[float] = None
    benchmark_gap: Optional[float] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KaizenCreate(BaseModel):
    event_id: Optional[int] = None
    kaizen_number: str
    description: str
    category: Optional[str] = None
    baseline_cost: float
    target_reduction_pct: float
    responsible_person: Optional[str] = None
    notes: Optional[str] = None


class KaizenResponse(BaseModel):
    id: int
    event_id: Optional[int] = None
    kaizen_number: str
    description: str
    category: Optional[str] = None
    baseline_cost: float
    target_reduction_pct: float
    target_cost: float
    actual_cost: float
    achieved_reduction_pct: float
    status: str
    responsible_person: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CostVarianceCreate(BaseModel):
    event_id: Optional[int] = None
    line_item: str
    standard_cost: float = 0.0
    actual_cost: float = 0.0
    standard_quantity: float = 0.0
    actual_quantity: float = 0.0
    standard_price: float = 0.0
    actual_price: float = 0.0
    root_cause: Optional[str] = None


class CostVarianceResponse(BaseModel):
    id: int
    event_id: Optional[int] = None
    line_item: str
    standard_cost: float
    actual_cost: float
    standard_quantity: float
    actual_quantity: float
    standard_price: float
    actual_price: float
    price_variance: float
    quantity_variance: float
    total_variance: float
    is_favorable: bool
    root_cause: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BSCCreate(BaseModel):
    event_id: int
    name: str
    period: str


class BSCResponse(BaseModel):
    id: int
    event_id: int
    name: str
    period: str
    financial_score: float
    customer_score: float
    internal_process_score: float
    learning_growth_score: float
    overall_score: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class BSCObjectiveCreate(BaseModel):
    bsc_id: int
    perspective: str
    objective_name: str
    weight: float = 0.0


class BSCObjectiveResponse(BaseModel):
    id: int
    bsc_id: int
    perspective: str
    objective_name: str
    weight: float
    score: float

    model_config = ConfigDict(from_attributes=True)


class BSCIndicatorCreate(BaseModel):
    bsc_id: int
    objective_id: Optional[int] = None
    perspective: str
    indicator_name: str
    formula: Optional[str] = None
    target_value: float
    weight: float = 0.0
    uom: Optional[str] = None
    frequency: str = "monthly"


class BSCIndicatorResponse(BaseModel):
    id: int
    bsc_id: int
    objective_id: Optional[int] = None
    perspective: str
    indicator_name: str
    formula: Optional[str] = None
    target_value: float
    actual_value: float
    score: float
    weight: float
    uom: Optional[str] = None
    frequency: str

    model_config = ConfigDict(from_attributes=True)


class BSCMeasurementCreate(BaseModel):
    indicator_id: int
    measurement_date: date
    actual_value: float
    target_value: float
    notes: Optional[str] = None


class BSCMeasurementResponse(BaseModel):
    id: int
    indicator_id: int
    measurement_date: date
    actual_value: float
    target_value: float
    score: float
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EventProfitabilityResponse(BaseModel):
    event_id: int
    total_revenue: float
    direct_costs: float
    gross_profit: float
    gross_margin_pct: float
    operating_expenses: float
    net_profit: float
    net_margin_pct: float
    roi: float
    break_even_attendees: float
    actual_attendees: Optional[float] = None
    revenue_per_attendee: float
    cost_per_attendee: float
    contribution_margin: float
    contribution_ratio: float

    model_config = ConfigDict(from_attributes=True)


class ABCEventAnalysis(BaseModel):
    event_id: int
    pools: List[dict]
    pareto: List[dict]
    total_cost: float


class ValueChainAnalysis(BaseModel):
    event_id: int
    primary_activities: list
    support_activities: list
    total_cost: float
    total_value_added: float
    benchmark_gap_total: float


class BSCDashboard(BaseModel):
    bsc: BSCResponse
    objectives: List[BSCObjectiveResponse]
    indicators: List[BSCIndicatorResponse]
    perspectives: dict
