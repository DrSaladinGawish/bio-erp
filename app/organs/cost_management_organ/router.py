from fastapi import APIRouter
from datetime import datetime

from app.organs.cost_management_organ.schemas import (
    ABCPoolSchema,
    ABCProductAllocationSchema,
    ABCFullAnalysisSchema,
    TDABCPoolSchema,
    TDABCProductSchema,
    TDABCIdleCapacitySchema,
    RCAResourceSchema,
    RCACapacityAnalysisSchema,
    TraditionalCostingSchema,
    TargetCostingSchema,
    TargetCostSheetSchema,
    TargetCostingSummarySchema,
    KaizenCostingSchema,
    KaizenPeriodSchema,
    LifeCycleCostingSchema,
    ThroughputAccountingSchema,
    StandardCostingSchema,
    VariableCostingSchema,
    AbsorptionCostingSchema,
    MarginalCostingSchema,
    ProcessCostingSchema,
    JobOrderCostingSchema,
    BatchCostingSchema,
    ContractCostingSchema,
    ServiceCostingSchema,
    JointProductCostingSchema,
    ByProductCostingSchema,
    BackflushCostingSchema,
    GembaAnalysisSchema,
    QualityCostSchema,
    EnvironmentalCostSchema,
    StrategicCostAnalysisSchema,
)
from app.organs.cost_management_organ.services import (
    ABCEngine,
    TDABCEngine,
    RCAEngine,
    TraditionalCostingEngine,
    TargetCostingEngine,
    KaizenCostingEngine,
    LifeCycleCostingEngine,
    ThroughputAccountingEngine,
    StandardCostingEngine,
    VariableCostingEngine,
    AbsorptionCostingEngine,
    MarginalCostingEngine,
    ProcessCostingEngine,
    JobOrderCostingEngine,
    BatchCostingEngine,
    ContractCostingEngine,
    ServiceCostingEngine,
    JointProductCostingEngine,
    ByProductCostingEngine,
    BackflushCostingEngine,
    GembaCostingEngine,
    QualityCostingEngine,
    EnvironmentalCostingEngine,
    StrategicCostManagementEngine,
)

router = APIRouter()


# =============================================================================
# ROOT & HEALTH
# =============================================================================


@router.get("/")
def root():
    return {
        "service": "Cost Management Microservice",
        "version": "5.3.0",
        "techniques_count": 24,
        "techniques": [
            "activity-based-costing",
            "time-driven-abc",
            "resource-consumption-accounting",
            "traditional-costing",
            "target-costing",
            "kaizen-costing",
            "life-cycle-costing",
            "throughput-accounting",
            "standard-costing",
            "variable-costing",
            "absorption-costing",
            "marginal-costing",
            "process-costing",
            "job-order-costing",
            "batch-costing",
            "contract-costing",
            "service-costing",
            "joint-product-costing",
            "by-product-costing",
            "backflush-costing",
            "gemba-costing",
            "quality-costing",
            "environmental-costing",
            "strategic-cost-management",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "cost-management",
        "version": "5.3.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "abc",
            "tdabc",
            "rca",
            "traditional",
            "target",
            "kaizen",
            "life_cycle",
            "throughput",
            "standard",
            "variable",
            "absorption",
            "marginal",
            "process",
            "job_order",
            "batch",
            "contract",
            "service",
            "joint_product",
            "by_product",
            "backflush",
            "gemba",
            "quality",
            "environmental",
            "strategic",
        ],
    }


# =============================================================================
# 1. ACTIVITY-BASED COSTING (ABC)
# =============================================================================


@router.post("/abc/calculate-rate")
def abc_rate(pool: ABCPoolSchema):
    rate = ABCEngine.calculate_activity_rate(pool.total_cost, pool.total_driver_quantity)
    return {
        "success": True,
        "technique": "ABC",
        "pool_name": pool.pool_name,
        "activity_rate": rate,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/abc/allocate")
def abc_allocate(pool: ABCPoolSchema, allocation: ABCProductAllocationSchema):
    cost = ABCEngine.allocate_to_product(
        pool.total_cost, pool.total_driver_quantity, allocation.consumption_quantity
    )
    return {
        "success": True,
        "technique": "ABC",
        "product_name": allocation.product_name,
        "allocated_cost": cost,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/abc/full-analysis")
def abc_full_analysis(req: ABCFullAnalysisSchema):
    pools = [p.model_dump() for p in req.pools]
    allocs = [a.model_dump() for a in req.allocations]
    result = ABCEngine.full_analysis(pools, allocs)
    return {
        "success": True,
        "technique": "ABC",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 2. TIME-DRIVEN ABC (TDABC)
# =============================================================================


@router.post("/tdabc/calculate-pool")
def tdabc_pool(pool: TDABCPoolSchema):
    result = TDABCEngine.calculate_practical_capacity(
        pool.total_cost, pool.resources_count,
        pool.days_per_year, pool.hours_per_day, pool.efficiency_pct,
    )
    return {
        "success": True,
        "technique": "TDABC",
        "pool_name": pool.name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/tdabc/product-cost")
def tdabc_product(pool: TDABCPoolSchema, product: TDABCProductSchema):
    result = TDABCEngine.calculate_product_cost(
        pool.total_cost, pool.resources_count, product.volume,
        product.time_per_unit_minutes, pool.days_per_year,
        pool.hours_per_day, pool.efficiency_pct,
    )
    return {
        "success": True,
        "technique": "TDABC",
        "product_name": product.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/tdabc/idle-capacity")
def tdabc_idle(req: TDABCIdleCapacitySchema):
    result = TDABCEngine.calculate_idle_capacity(
        req.total_cost, req.resources_count,
        req.used_minutes, req.efficiency_pct,
    )
    return {
        "success": True,
        "technique": "TDABC",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 3. RESOURCE CONSUMPTION ACCOUNTING (RCA)
# =============================================================================


@router.post("/rca/total-cost")
def rca_total(resource: RCAResourceSchema):
    total = RCAEngine.calculate_total_cost(resource.fixed_cost, resource.proportional_cost)
    return {
        "success": True,
        "technique": "RCA",
        "resource_name": resource.resource_name,
        "total_cost": total,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/rca/capacity-analysis")
def rca_capacity(req: RCACapacityAnalysisSchema):
    resources = [r.model_dump() for r in req.resources]
    result = RCAEngine.capacity_analysis(resources, req.planned_output, req.actual_output)
    return {
        "success": True,
        "technique": "RCA",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 4. TRADITIONAL COSTING
# =============================================================================


@router.post("/traditional/calculate")
def traditional(req: TraditionalCostingSchema):
    result = TraditionalCostingEngine.full_analysis(
        req.pool_name, req.total_overhead, req.allocation_base,
        req.base_quantity, req.product_name, req.product_base_consumption,
    )
    return {
        "success": True,
        "technique": "TRADITIONAL",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 5. TARGET COSTING
# =============================================================================


@router.post("/target/calculate")
def target_calculate(req: TargetCostingSchema):
    target = TargetCostingEngine.calculate_target_cost(req.market_price, req.target_profit_pct)
    gap = TargetCostingEngine.cost_gap(req.current_cost, target["target_cost"])
    return {
        "success": True,
        "technique": "TARGET",
        "product_name": req.product_name,
        **target,
        **gap,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/target/cost-sheet")
def target_sheet(sheet: TargetCostSheetSchema):
    gap = TargetCostingEngine.cost_gap(sheet.as_is_cost, sheet.target_cost)
    return {
        "success": True,
        "technique": "TARGET",
        "component": sheet.cost_component,
        **gap,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/target/summary")
def target_summary(req: TargetCostingSummarySchema):
    sheets = [s.model_dump() for s in req.sheets]
    result = TargetCostingEngine.summary(
        req.product_name, req.market_price, req.target_profit_pct, sheets,
    )
    return {
        "success": True,
        "technique": "TARGET",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 6. KAIZEN COSTING
# =============================================================================


@router.post("/kaizen/reduction-path")
def kaizen_path(req: KaizenCostingSchema):
    path = KaizenCostingEngine.calculate_reduction_path(
        req.current_monthly_cost, req.target_reduction_pct, req.months,
    )
    return {
        "success": True,
        "technique": "KAIZEN",
        "product_name": req.product_name,
        "monthly_path": path,
        "final_cost": path[-1]["cost"] if path else req.current_monthly_cost,
        "total_reduction_pct": path[-1]["cumulative_reduction_pct"] if path else 0,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/kaizen/period-analysis")
def kaizen_period(req: KaizenPeriodSchema):
    result = KaizenCostingEngine.period_analysis(
        req.baseline_cost, req.current_cost, req.period_number,
    )
    return {
        "success": True,
        "technique": "KAIZEN",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 7. LIFE CYCLE COSTING
# =============================================================================


@router.post("/lifecycle/npv-analysis")
def lifecycle_npv(req: LifeCycleCostingSchema):
    phases = [p.model_dump() for p in req.phases]
    result = LifeCycleCostingEngine.npv_analysis(phases, req.discount_rate_pct)
    return {
        "success": True,
        "technique": "LIFE_CYCLE",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 8. THROUGHPUT ACCOUNTING
# =============================================================================


@router.post("/throughput/ranking")
def throughput_ranking(req: ThroughputAccountingSchema):
    products = [p.model_dump() for p in req.products]
    result = ThroughputAccountingEngine.ranking_analysis(
        products, req.total_operating_expenses, req.bottleneck_minutes_available,
    )
    return {
        "success": True,
        "technique": "THROUGHPUT",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 9. STANDARD COSTING
# =============================================================================


@router.post("/standard/variances")
def standard_variances(req: StandardCostingSchema):
    items = [i.model_dump() for i in req.items]
    item_variances = StandardCostingEngine.calculate_variances(items)
    overhead = StandardCostingEngine.overhead_variances(
        req.budgeted_overhead, req.actual_overhead,
        req.budgeted_base, req.actual_base,
    )
    total_item_var = sum(v["total_variance"] for v in item_variances)
    return {
        "success": True,
        "technique": "STANDARD",
        "product_name": req.product_name,
        "item_variances": item_variances,
        "overhead_variances": overhead,
        "total_item_variance": round(total_item_var, 4),
        "total_overhead_variance": overhead["total_overhead_variance"],
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 10. VARIABLE COSTING
# =============================================================================


@router.post("/variable/income-statement")
def variable_income(req: VariableCostingSchema):
    result = VariableCostingEngine.income_statement(
        req.selling_price_per_unit, req.variable_cost_per_unit,
        req.total_fixed_cost, req.units_sold,
        req.beginning_inventory, req.units_produced, req.ending_inventory,
    )
    return {
        "success": True,
        "technique": "VARIABLE",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/variable/break-even")
def variable_breakeven(req: VariableCostingSchema):
    result = VariableCostingEngine.income_statement(
        req.selling_price_per_unit, req.variable_cost_per_unit,
        req.total_fixed_cost, req.units_sold,
    )
    return {
        "success": True,
        "technique": "VARIABLE",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 11. ABSORPTION COSTING
# =============================================================================


@router.post("/absorption/income-statement")
def absorption_income(req: AbsorptionCostingSchema):
    result = AbsorptionCostingEngine.income_statement(
        req.selling_price_per_unit, req.direct_material_per_unit,
        req.direct_labor_per_unit, req.variable_overhead_per_unit,
        req.total_fixed_overhead, req.units_produced, req.units_sold,
    )
    return {
        "success": True,
        "technique": "ABSORPTION",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 12. MARGINAL COSTING
# =============================================================================


@router.post("/marginal/full-analysis")
def marginal_analysis(req: MarginalCostingSchema):
    result = MarginalCostingEngine.full_analysis(
        req.selling_price_per_unit, req.variable_cost_per_unit,
        req.total_fixed_cost, req.target_profit, req.units_sold,
    )
    return {
        "success": True,
        "technique": "MARGINAL",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/marginal/breakeven")
def marginal_breakeven(req: MarginalCostingSchema):
    be = MarginalCostingEngine.breakeven_analysis(
        req.selling_price_per_unit, req.variable_cost_per_unit, req.total_fixed_cost,
    )
    return {
        "success": True,
        "technique": "MARGINAL",
        "product_name": req.product_name,
        **be,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/marginal/target-profit")
def marginal_target(req: MarginalCostingSchema):
    tp = MarginalCostingEngine.target_profit_analysis(
        req.selling_price_per_unit, req.variable_cost_per_unit,
        req.total_fixed_cost, req.target_profit,
    )
    return {
        "success": True,
        "technique": "MARGINAL",
        "product_name": req.product_name,
        **tp,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 13. PROCESS COSTING
# =============================================================================


@router.post("/process/calculate")
def process_costing(req: ProcessCostingSchema):
    departments = [d.model_dump() for d in req.departments]
    result = ProcessCostingEngine.process_departments(departments)
    return {
        "success": True,
        "technique": "PROCESS",
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 14. JOB ORDER COSTING
# =============================================================================


@router.post("/job-order/calculate")
def job_order(req: JobOrderCostingSchema):
    result = JobOrderCostingEngine.job_profitability(
        req.job_number, req.customer_name, req.quantity,
        req.direct_material, req.direct_labor_hours,
        req.labor_rate, req.overhead_rate, req.quoted_price,
    )
    return {
        "success": True,
        "technique": "JOB_ORDER",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 15. BATCH COSTING
# =============================================================================


@router.post("/batch/calculate")
def batch_costing(req: BatchCostingSchema):
    result = BatchCostingEngine.calculate_batch_cost(
        req.direct_material, req.direct_labor,
        req.batch_overhead, req.batch_size,
    )
    return {
        "success": True,
        "technique": "BATCH",
        "batch_number": req.batch_number,
        "product_name": req.product_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 16. CONTRACT COSTING
# =============================================================================


@router.post("/contract/percentage-of-completion")
def contract_poc(req: ContractCostingSchema):
    result = ContractCostingEngine.percentage_of_completion(
        req.contract_value, req.estimated_total_cost,
        req.costs_to_date, req.progress_billing,
    )
    return {
        "success": True,
        "technique": "CONTRACT",
        "contract_number": req.contract_number,
        "client_name": req.client_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 17. SERVICE COSTING
# =============================================================================


@router.post("/service/profitability")
def service_profitability(req: ServiceCostingSchema):
    result = ServiceCostingEngine.profitability(
        req.service_name, req.direct_labor_cost,
        req.direct_labor_hours, req.overhead_cost,
        req.support_staff_cost, req.other_direct_costs,
        req.service_units_delivered, req.billing_rate,
    )
    return {
        "success": True,
        "technique": "SERVICE",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/service/calculate-cost")
def service_cost(req: ServiceCostingSchema):
    result = ServiceCostingEngine.calculate_service_cost(
        req.direct_labor_cost, req.direct_labor_hours,
        req.overhead_cost, req.support_staff_cost,
        req.other_direct_costs, req.service_units_delivered,
    )
    return {
        "success": True,
        "technique": "SERVICE",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 18. JOINT PRODUCT COSTING
# =============================================================================


@router.post("/joint-product/split")
def joint_split(req: JointProductCostingSchema):
    products = [p.model_dump() for p in req.products]
    result = JointProductCostingEngine.full_analysis(
        req.joint_cost, products, req.split_method,
    )
    return {
        "success": True,
        "technique": "JOINT_PRODUCT",
        "production_run": req.production_run,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 19. BY-PRODUCT COSTING
# =============================================================================


@router.post("/by-product/allocate")
def byproduct_allocate(req: ByProductCostingSchema):
    by_products = [b.model_dump() for b in req.by_products]
    if req.allocation_method == "NO_ALLOCATION":
        result = ByProductCostingEngine.no_allocation_method(
            req.joint_cost, req.main_product_name,
            req.main_product_quantity, req.main_product_price, by_products,
        )
    else:
        result = ByProductCostingEngine.nrv_method(
            req.joint_cost, req.main_product_name,
            req.main_product_quantity, req.main_product_price, by_products,
        )
    return {
        "success": True,
        "technique": "BY_PRODUCT",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 20. BACKFLUSH COSTING
# =============================================================================


@router.post("/backflush/calculate")
def backflush(req: BackflushCostingSchema):
    components = [c.model_dump() for c in req.bom_components]
    result = BackflushCostingEngine.calculate(
        req.quantity_produced, components,
        req.labor_rate_per_hour, req.labor_hours_per_unit,
        req.overhead_rate_per_unit,
    )
    return {
        "success": True,
        "technique": "BACKFLUSH",
        "production_order": req.production_order,
        "finished_good": req.finished_good,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 21. GEMBA COSTING
# =============================================================================


@router.post("/gemba/analyze")
def gemba_analyze(req: GembaAnalysisSchema):
    observations = [o.model_dump() for o in req.observations]
    result = GembaCostingEngine.analyze_observations(
        observations, req.total_operating_hours,
        req.hourly_labor_rate, req.monthly_revenue,
    )
    return {
        "success": True,
        "technique": "GEMBA",
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 22. QUALITY COSTING (COQ)
# =============================================================================


@router.post("/quality/coq-analysis")
def quality_coq(req: QualityCostSchema):
    result = QualityCostingEngine.calculate_coq(req.model_dump())
    return {
        "success": True,
        "technique": "QUALITY_COQ",
        "period": req.period,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 23. ENVIRONMENTAL COSTING
# =============================================================================


@router.post("/environmental/analyze")
def environmental_analyze(req: EnvironmentalCostSchema):
    result = EnvironmentalCostingEngine.full_analysis(req.model_dump())
    return {
        "success": True,
        "technique": "ENVIRONMENTAL",
        "period": req.period,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 24. STRATEGIC COST MANAGEMENT
# =============================================================================


@router.post("/strategic/analyze")
def strategic_analyze(req: StrategicCostAnalysisSchema):
    initiatives = [i.model_dump() for i in req.initiatives]
    result = StrategicCostManagementEngine.full_analysis(
        req.organization, initiatives,
        req.total_budget, req.planning_horizon_years,
    )
    return {
        "success": True,
        "technique": "STRATEGIC",
        **result,
        "timestamp": datetime.now().isoformat(),
    }
