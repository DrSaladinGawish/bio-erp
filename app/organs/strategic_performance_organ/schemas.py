from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class ApiResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    items: List[Any]


# =============================================================================
# 1. Balanced Scorecard (BSC) — 4 perspectives with weighted KPIs
# =============================================================================


class BSCPerspectiveInput(BaseModel):
    perspective_name: str = Field(
        ..., description="FINANCIAL, CUSTOMER, INTERNAL_PROCESSES, LEARNING_GROWTH"
    )
    weight_pct: float = Field(default=25.0, ge=0, le=100)
    kpis: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of KPI dicts with keys: kpi_name, actual_value, target_value, weight_pct",
    )


class BSCScorecardRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    perspectives: List[BSCPerspectiveInput]
    measurement_period: str = Field(default="Q1-2026")


class BSCScorecardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    perspective_scores: List[Dict[str, Any]]
    weighted_total_score: float
    overall_performance_index: float
    rating: str
    measurement_period: str


# =============================================================================
# 2. EFQM Excellence Model — 6 criteria scoring (1000-point scale)
# =============================================================================


class EFQMCriteriaInput(BaseModel):
    criteria_name: str = Field(
        ...,
        description="Leadership, Strategy, People, Partnerships_Resources, Processes_Products_Results, Results",
    )
    score: float = Field(..., ge=0, le=1000)
    sub_criteria: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional sub-criteria with name and score",
    )


class EFQMAssessmentRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    organization_name: str
    criteria: List[EFQMCriteriaInput]


class EFQMAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_score: float
    max_possible: float
    excellence_percentage: float
    radar_profile: str
    criteria_breakdown: List[Dict[str, Any]]
    strengths: List[str]
    improvement_areas: List[str]


# =============================================================================
# 3. Total Quality Management (TQM) — 8 pillars maturity assessment
# =============================================================================


class TQMPillarInput(BaseModel):
    pillar_name: str = Field(
        ...,
        description="Customer_Focus, Process_Improvement, Employee_Involvement, "
        "Continuous_Improvement, Fact_Based_Decision, Leadership_Commitment, "
        "Supplier_Partnership, Strategic_Quality_Planning",
    )
    maturity_level: int = Field(..., ge=1, le=5)
    weight: float = Field(default=1.0, ge=0, le=5)
    sub_items: List[Dict[str, Any]] = Field(default_factory=list)


class TQMAssessmentRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    organization_name: str
    pillars: List[TQMPillarInput]


class TQMAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    average_maturity: float
    weighted_maturity: float
    overall_tqm_rating: str
    pillar_details: List[Dict[str, Any]]
    weakest_pillars: List[str]
    strongest_pillars: List[str]


# =============================================================================
# 4. KPI Frameworks — Custom KPI tracking with variance analysis
# =============================================================================


class KPIEntryInput(BaseModel):
    kpi_name: str
    category: str = Field(default="OPERATIONAL")
    actual_value: float
    target_value: float
    previous_value: Optional[float] = None
    unit: str = Field(default="%")
    frequency: str = Field(default="monthly")
    weight_pct: float = Field(default=1.0, ge=0)
    lower_is_better: bool = Field(default=False)


class KPIFrameworkRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    kpis: List[KPIEntryInput]
    framework: str = Field(default="custom")


class KPIFrameworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    framework: str
    total_kpis: int
    kpi_results: List[Dict[str, Any]]
    aggregate_score: float
    on_track_count: int
    at_risk_count: int
    behind_count: int
    trend_summary: Dict[str, Any]


# =============================================================================
# 5. Performance Dashboards — Real-time metric aggregation
# =============================================================================


class DashboardMetricInput(BaseModel):
    metric_name: str
    current_value: float
    target_value: float
    previous_value: float = 0.0
    category: str = Field(default="GENERAL")
    unit: str = Field(default="")
    weight_pct: float = Field(default=1.0, ge=0)
    threshold_green: Optional[float] = None
    threshold_amber: Optional[float] = None


class PerformanceDashboardRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    metrics: List[DashboardMetricInput]
    time_period: str = Field(default="last_quarter")
    comparison_baseline: Optional[str] = None


class PerformanceDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    aggregate_score: float
    metrics_count: int
    metrics_status: List[Dict[str, Any]]
    green_count: int
    amber_count: int
    red_count: int
    time_period: str
    overall_health: str


# =============================================================================
# 6. Benchmarking — Industry comparison with gap analysis
# =============================================================================


class BenchmarkMetricInput(BaseModel):
    metric_name: str
    organization_value: float
    industry_average: float
    industry_best: float
    unit: str = Field(default="%")
    importance: float = Field(default=1.0, ge=0, le=5)


class BenchmarkingRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    organization_name: str
    metrics: List[BenchmarkMetricInput]
    benchmark_source: str = Field(default="industry_average")


class BenchmarkingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_benchmark_index: float
    metrics_comparison: List[Dict[str, Any]]
    leading_count: int
    lagging_count: int
    par_count: int
    competitive_position: str


# =============================================================================
# 7. Strategy Maps — Causal linkages between objectives
# =============================================================================


class StrategyMapNodeInput(BaseModel):
    node_id: str
    perspective: str
    objective: str
    kpi_id: Optional[str] = None
    parent_ids: List[str] = Field(default_factory=list)
    priority: int = Field(default=1, ge=1, le=5)


class StrategyMapRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    nodes: List[StrategyMapNodeInput]
    strategy_name: str


class StrategyMapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy_name: str
    nodes_count: int
    links_count: int
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    perspective_coverage: Dict[str, int]
    critical_path: List[str]
    circular_dependencies: List[str]


# =============================================================================
# 8. Performance Contracts — Employee KPI agreements
# =============================================================================


class ContractKPIInput(BaseModel):
    kpi_name: str
    target_value: float
    weight_pct: float = Field(..., ge=0, le=100)
    measurement_method: str = Field(default="QUANTITATIVE")


class PerformanceContractRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    employee_id: str
    employee_name: str
    review_period: str
    kpis: List[ContractKPIInput]
    manager_id: Optional[str] = None
    department: Optional[str] = None


class PerformanceContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_name: str
    review_period: str
    total_weight: float
    weight_valid: bool
    kpis_count: int
    contract_status: str
    achieved_score: float
    performance_rating: str


# =============================================================================
# 9. OKR Cascading — Company → Department → Team alignment
# =============================================================================


class KeyResultInput(BaseModel):
    description: str
    target_value: float
    current_value: float = 0.0
    unit: str = Field(default="%")


class OKRInput(BaseModel):
    objective: str
    key_results: List[KeyResultInput]
    owner: str
    level: str = Field(default="company", description="company, department, team")
    department: Optional[str] = None


class OKRCascadingRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    company_okrs: List[OKRInput]
    department_okrs: List[OKRInput] = Field(default_factory=list)
    team_okrs: List[OKRInput] = Field(default_factory=list)
    quarter: str = Field(default="Q1-2026")


class OKRCascadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_alignment: float
    department_alignment: float
    team_alignment: float
    overall_alignment: float
    cascading_score: float
    okr_summary: Dict[str, Any]
    quarter: str
    at_risk_okrs: List[str]


# =============================================================================
# 10. Performance Reviews — Entity-based scoring
# =============================================================================


class ReviewMetricInput(BaseModel):
    metric_name: str
    actual_value: float
    target_value: float
    weight_pct: float = Field(default=1.0, ge=0)


class PerformanceReviewRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    entity_id: str
    entity_type: str = Field(
        default="department", description="department, division, project, team"
    )
    period: str
    metrics: List[ReviewMetricInput]


class PerformanceReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    entity_type: str
    overall_score: float
    rating: str
    metric_details: List[Dict[str, Any]]
    period: str
    improvement_areas: List[str]
    strengths: List[str]


# =============================================================================
# 11. Gap Analysis — Current vs Target with action plans
# =============================================================================


class GapMetricInput(BaseModel):
    metric_name: str
    current_value: float
    target_value: float
    priority: int = Field(default=1, ge=1, le=5)
    category: str = Field(default="GENERAL")


class GapAnalysisRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    metrics: List[GapMetricInput]
    target_date: Optional[str] = None


class GapAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_gap_percentage: float
    metrics_analysis: List[Dict[str, Any]]
    critical_gaps: int
    moderate_gaps: int
    minor_gaps: int
    priority_ranking: List[Dict[str, Any]]


# =============================================================================
# 12. Improvement Plans — Area-based improvement tracking
# =============================================================================


class ImprovementActionInput(BaseModel):
    action_name: str
    responsible: str
    deadline: str
    estimated_impact: float = Field(default=0.0, ge=0, le=100)
    status: str = Field(default="PLANNED")


class ImprovementPlanRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    area: str
    current_score: float = Field(..., ge=0, le=100)
    target_score: float = Field(..., ge=0, le=100)
    actions: List[ImprovementActionInput]
    timeline: str = Field(default="6 months")


class ImprovementPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area: str
    gap: float
    gap_percentage: float
    actions_count: int
    planned_actions: int
    in_progress_actions: int
    completed_actions: int
    estimated_improvement: float
    feasibility_score: float
    timeline: str


# =============================================================================
# 13. Balanced Scorecard Variance — Actual vs Target analysis
# =============================================================================


class BSCVarianceMetricInput(BaseModel):
    perspective: str
    metric_name: str
    actual_value: float
    target_value: float
    weight_pct: float = Field(default=1.0, ge=0)
    tolerance_pct: float = Field(default=10.0, ge=0, le=100)


class BSCVarianceRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    metrics: List[BSCVarianceMetricInput]
    period: str = Field(default="Q1-2026")


class BSCVarianceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str
    perspective_variances: List[Dict[str, Any]]
    overall_variance_pct: float
    total_metrics: int
    within_tolerance: int
    exceeding_tolerance: int
    performance_status: str
    corrective_actions_needed: List[str]


# =============================================================================
# 14. Performance Measurement Systems — Multi-framework integration
# =============================================================================


class FrameworkConfigInput(BaseModel):
    framework_name: str
    metrics_count: int
    weight_pct: float = Field(default=1.0, ge=0)
    score: float = Field(default=0.0, ge=0, le=100)


class MeasurementSystemRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    system_name: str
    frameworks: List[FrameworkConfigInput]


class MeasurementSystemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    system_name: str
    total_frameworks: int
    total_metrics: int
    integration_score: float
    framework_details: List[Dict[str, Any]]
    maturity_level: str
    recommendations: List[str]


# =============================================================================
# 15. Results-Based Management — Outcome-focused evaluation
# =============================================================================


class RBMOutcomeInput(BaseModel):
    outcome_name: str
    target_value: float
    actual_value: float
    indicator_type: str = Field(default="IMPACT", description="IMPACT, OUTPUT, OUTCOME")
    weight_pct: float = Field(default=1.0, ge=0)


class RBMEvaluationRequest(BaseModel):
    org_id: Optional[uuid.UUID] = None
    program_name: str
    outcomes: List[RBMOutcomeInput]
    budget_allocated: Optional[float] = None
    budget_spent: Optional[float] = None


class RBMEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    program_name: str
    efficiency_score: float
    effectiveness_score: float
    impact_score: float
    overall_rbm_score: float
    rbm_rating: str
    outcome_details: List[Dict[str, Any]]
    cost_effectiveness: Optional[float] = None
    recommendations: List[str]
