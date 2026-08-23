from pydantic import BaseModel, Field
from typing import List


model_config = {"json_schema_extra": {"examples": []}}


# =============================================================================
# 1. Activity-Based Costing (ABC)
# =============================================================================


class ABCPoolSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    pool_name: str = Field(..., min_length=1)
    total_cost: float = Field(..., gt=0)
    cost_category: str = Field(
        ..., description="UNIT_LEVEL, BATCH_LEVEL, PRODUCT_LEVEL, FACILITY_LEVEL"
    )
    cost_driver_name: str = Field(..., min_length=1)
    total_driver_quantity: float = Field(..., gt=0)


class ABCProductAllocationSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    pool_name: str = Field(..., min_length=1)
    consumption_quantity: float = Field(..., gt=0)


class ABCFullAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    pools: List[ABCPoolSchema]
    allocations: List[ABCProductAllocationSchema]


# =============================================================================
# 2. Time-Driven ABC (TDABC)
# =============================================================================


class TDABCPoolSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    name: str = Field(..., min_length=1)
    total_cost: float = Field(..., gt=0)
    resources_count: int = Field(..., gt=0)
    days_per_year: int = Field(default=250, ge=1, le=366)
    hours_per_day: int = Field(default=8, ge=1, le=24)
    efficiency_pct: float = Field(default=85.0, gt=0, le=100)


class TDABCProductSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    volume: int = Field(..., gt=0)
    time_per_unit_minutes: float = Field(..., gt=0)


class TDABCIdleCapacitySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    total_cost: float = Field(..., gt=0)
    resources_count: int = Field(..., gt=0)
    efficiency_pct: float = Field(default=85.0, gt=0, le=100)
    used_minutes: float = Field(..., ge=0)


# =============================================================================
# 3. Resource Consumption Accounting (RCA)
# =============================================================================


class RCAResourceSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    resource_name: str = Field(..., min_length=1)
    fixed_cost: float = Field(default=0.0, ge=0)
    proportional_cost: float = Field(default=0.0, ge=0)
    measurable_output_unit: str = Field(default="units")


class RCACapacityAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    resources: List[RCAResourceSchema]
    planned_output: float = Field(..., gt=0)
    actual_output: float = Field(..., ge=0)


# =============================================================================
# 4. Traditional Costing
# =============================================================================


class TraditionalCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    pool_name: str = Field(..., min_length=1)
    total_overhead: float = Field(..., gt=0)
    allocation_base: str = Field(
        ...,
        description="DIRECT_LABOR_HOURS, MACHINE_HOURS, DIRECT_LABOR_COST, UNITS_PRODUCED",
    )
    base_quantity: float = Field(..., gt=0)
    product_name: str = Field(..., min_length=1)
    product_base_consumption: float = Field(..., gt=0)


# =============================================================================
# 5. Target Costing
# =============================================================================


class TargetCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    market_price: float = Field(..., gt=0)
    target_profit_pct: float = Field(..., gt=0, le=100)
    current_cost: float = Field(..., gt=0)


class TargetCostSheetSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    cost_component: str = Field(..., min_length=1)
    as_is_cost: float = Field(..., ge=0)
    target_cost: float = Field(..., ge=0)


class TargetCostingSummarySchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    market_price: float = Field(..., gt=0)
    target_profit_pct: float = Field(..., gt=0, le=100)
    sheets: List[TargetCostSheetSchema]


# =============================================================================
# 6. Kaizen Costing
# =============================================================================


class KaizenCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    current_monthly_cost: float = Field(..., gt=0)
    target_reduction_pct: float = Field(..., gt=0, le=50)
    months: int = Field(default=12, ge=1, le=60)


class KaizenPeriodSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    baseline_cost: float = Field(..., gt=0)
    current_cost: float = Field(..., gt=0)
    period_number: int = Field(..., ge=1)


# =============================================================================
# 7. Life Cycle Costing
# =============================================================================


class LifecyclePhaseSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    phase: str = Field(
        ...,
        description="RND, DESIGN, INTRODUCTION, GROWTH, MATURITY, DECLINE, SERVICE, DISPOSAL",
    )
    cost: float = Field(..., ge=0)
    revenue: float = Field(default=0.0, ge=0)
    duration_years: float = Field(default=1.0, gt=0)


class LifeCycleCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    discount_rate_pct: float = Field(default=8.0, ge=0, le=100)
    phases: List[LifecyclePhaseSchema]


# =============================================================================
# 8. Throughput Accounting
# =============================================================================


class ThroughputProductSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    selling_price: float = Field(..., gt=0)
    material_cost: float = Field(..., ge=0)
    units_sold: int = Field(..., gt=0)
    bottleneck_time_minutes: float = Field(..., gt=0)


class ThroughputAccountingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    products: List[ThroughputProductSchema]
    total_operating_expenses: float = Field(..., gt=0)
    bottleneck_minutes_available: float = Field(..., gt=0)


# =============================================================================
# 9. Standard Costing
# =============================================================================


class StandardCostItemSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    item_name: str = Field(..., min_length=1)
    standard_quantity: float = Field(..., gt=0)
    standard_price: float = Field(..., gt=0)
    actual_quantity: float = Field(..., ge=0)
    actual_price: float = Field(..., ge=0)


class StandardCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    items: List[StandardCostItemSchema]
    budgeted_overhead: float = Field(default=0.0, ge=0)
    actual_overhead: float = Field(default=0.0, ge=0)
    budgeted_base: float = Field(default=1.0, gt=0)
    actual_base: float = Field(default=0.0, ge=0)


# =============================================================================
# 10. Variable Costing
# =============================================================================


class VariableCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    selling_price_per_unit: float = Field(..., gt=0)
    variable_cost_per_unit: float = Field(..., ge=0)
    total_fixed_cost: float = Field(..., ge=0)
    units_sold: int = Field(..., gt=0)
    beginning_inventory: int = Field(default=0, ge=0)
    units_produced: int = Field(..., gt=0)
    ending_inventory: int = Field(default=0, ge=0)


# =============================================================================
# 11. Absorption Costing
# =============================================================================


class AbsorptionCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    selling_price_per_unit: float = Field(..., gt=0)
    direct_material_per_unit: float = Field(..., ge=0)
    direct_labor_per_unit: float = Field(..., ge=0)
    variable_overhead_per_unit: float = Field(..., ge=0)
    total_fixed_overhead: float = Field(..., ge=0)
    units_produced: int = Field(..., gt=0)
    units_sold: int = Field(..., gt=0)


# =============================================================================
# 12. Marginal Costing
# =============================================================================


class MarginalCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    selling_price_per_unit: float = Field(..., gt=0)
    variable_cost_per_unit: float = Field(..., ge=0)
    total_fixed_cost: float = Field(..., ge=0)
    target_profit: float = Field(default=0.0, ge=0)
    units_sold: int = Field(..., gt=0)


# =============================================================================
# 13. Process Costing
# =============================================================================


class ProcessDepartmentSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    department_name: str = Field(..., min_length=1)
    direct_material: float = Field(..., ge=0)
    direct_labor: float = Field(..., ge=0)
    overhead: float = Field(..., ge=0)
    units_started: int = Field(..., gt=0)
    units_completed: int = Field(..., gt=0)
    ending_wip_units: int = Field(default=0, ge=0)
    ending_wip_pct_complete: float = Field(default=0.0, ge=0, le=100)


class ProcessCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    departments: List[ProcessDepartmentSchema]


# =============================================================================
# 14. Job Order Costing
# =============================================================================


class JobOrderCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    job_number: str = Field(..., min_length=1)
    customer_name: str = Field(default="")
    quantity: int = Field(..., gt=0)
    direct_material: float = Field(..., ge=0)
    direct_labor_hours: float = Field(..., ge=0)
    labor_rate: float = Field(..., gt=0)
    overhead_rate: float = Field(default=0.0, ge=0)
    quoted_price: float = Field(default=0.0, ge=0)


# =============================================================================
# 15. Batch Costing
# =============================================================================


class BatchCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    batch_number: str = Field(..., min_length=1)
    product_name: str = Field(..., min_length=1)
    batch_size: int = Field(..., gt=0)
    direct_material: float = Field(..., ge=0)
    direct_labor: float = Field(..., ge=0)
    batch_overhead: float = Field(..., ge=0)


# =============================================================================
# 16. Contract Costing
# =============================================================================


class ContractCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    contract_number: str = Field(..., min_length=1)
    client_name: str = Field(..., min_length=1)
    contract_value: float = Field(..., gt=0)
    estimated_total_cost: float = Field(..., gt=0)
    costs_to_date: float = Field(..., ge=0)
    progress_billing: float = Field(default=0.0, ge=0)


# =============================================================================
# 17. Service Costing
# =============================================================================


class ServiceCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    service_name: str = Field(..., min_length=1)
    direct_labor_cost: float = Field(..., ge=0)
    direct_labor_hours: float = Field(..., gt=0)
    overhead_cost: float = Field(..., ge=0)
    support_staff_cost: float = Field(default=0.0, ge=0)
    other_direct_costs: float = Field(default=0.0, ge=0)
    service_units_delivered: int = Field(..., gt=0)
    billing_rate: float = Field(default=0.0, ge=0)


# =============================================================================
# 18. Joint Product Costing
# =============================================================================


class JointProductSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    selling_price_per_unit: float = Field(..., gt=0)


class JointProductCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    production_run: str = Field(..., min_length=1)
    joint_cost: float = Field(..., gt=0)
    split_method: str = Field(
        ..., description="SALES_VALUE, PHYSICAL_UNITS, CONSTANT_GROSS_MARGIN"
    )
    products: List[JointProductSchema]


# =============================================================================
# 19. By-Product Costing
# =============================================================================


class ByProductSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    product_name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    selling_price_per_unit: float = Field(..., gt=0)
    separable_cost: float = Field(default=0.0, ge=0)


class ByProductCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    joint_cost: float = Field(..., gt=0)
    main_product_name: str = Field(..., min_length=1)
    main_product_quantity: int = Field(..., gt=0)
    main_product_price: float = Field(..., gt=0)
    by_products: List[ByProductSchema]
    allocation_method: str = Field(
        ..., description="NET_REALIZABLE_VALUE, SALES_VALUE, NO_ALLOCATION"
    )


# =============================================================================
# 20. Backflush Costing
# =============================================================================


class BOMComponentSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    component_name: str = Field(..., min_length=1)
    standard_qty_per_unit: float = Field(..., gt=0)
    standard_cost_per_unit: float = Field(..., gt=0)


class BackflushCostingSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    production_order: str = Field(..., min_length=1)
    finished_good: str = Field(..., min_length=1)
    quantity_produced: int = Field(..., gt=0)
    bom_components: List[BOMComponentSchema]
    labor_rate_per_hour: float = Field(default=0.0, ge=0)
    labor_hours_per_unit: float = Field(default=0.0, ge=0)
    overhead_rate_per_unit: float = Field(default=0.0, ge=0)


# =============================================================================
# 21. Gemba Costing
# =============================================================================


class GembaObservationSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    area: str = Field(..., min_length=1)
    process: str = Field(..., min_length=1)
    waste_type: str = Field(
        ...,
        description="OVERPRODUCTION, WAITING, TRANSPORT, OVERPROCESSING, INVENTORY, MOTION, DEFECTS",
    )
    estimated_cost_impact: float = Field(..., ge=0)
    time_lost_minutes: float = Field(default=0.0, ge=0)
    root_cause: str = Field(default="")
    recommendation: str = Field(default="")


class GembaAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    observations: List[GembaObservationSchema]
    total_operating_hours: float = Field(..., gt=0)
    hourly_labor_rate: float = Field(..., gt=0)
    monthly_revenue: float = Field(default=0.0, ge=0)


# =============================================================================
# 22. Quality Costing (COQ)
# =============================================================================


class QualityCostSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    period: str = Field(..., min_length=1)
    prevention_cost: float = Field(default=0.0, ge=0)
    appraisal_cost: float = Field(default=0.0, ge=0)
    internal_failure_cost: float = Field(default=0.0, ge=0)
    external_failure_cost: float = Field(default=0.0, ge=0)
    revenue: float = Field(default=0.0, ge=0)
    total_units_produced: int = Field(default=0, ge=0)
    defective_units: int = Field(default=0, ge=0)


# =============================================================================
# 23. Environmental Costing
# =============================================================================


class EnvironmentalCostSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    period: str = Field(..., min_length=1)
    waste_disposal_cost: float = Field(default=0.0, ge=0)
    emission_treatment_cost: float = Field(default=0.0, ge=0)
    compliance_cost: float = Field(default=0.0, ge=0)
    remediation_cost: float = Field(default=0.0, ge=0)
    prevention_cost: float = Field(default=0.0, ge=0)
    carbon_tonnes: float = Field(default=0.0, ge=0)
    carbon_price_per_tonne: float = Field(default=0.0, ge=0)
    revenue: float = Field(default=0.0, ge=0)
    waste_tonnes: float = Field(default=0.0, ge=0)


# =============================================================================
# 24. Strategic Cost Management
# =============================================================================


class StrategicInitiativeSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    initiative_name: str = Field(..., min_length=1)
    technique: str = Field(
        ...,
        description="VALUE_CHAIN, TARGET, KAIZEN, ABC, LIFE_CYCLE, THROUGHPUT, BENCHMARKING",
    )
    current_cost: float = Field(..., gt=0)
    target_cost: float = Field(..., gt=0)
    implementation_cost: float = Field(default=0.0, ge=0)
    payback_months: int = Field(default=12, ge=1)


class StrategicCostAnalysisSchema(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    organization: str = Field(..., min_length=1)
    initiatives: List[StrategicInitiativeSchema]
    total_budget: float = Field(..., gt=0)
    planning_horizon_years: int = Field(default=3, ge=1, le=10)


# =============================================================================
# GENERIC RESPONSE
# =============================================================================


class CostManagementResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": []}}

    success: bool = True
    technique: str = ""
    results: dict = {}
    timestamp: str = ""
