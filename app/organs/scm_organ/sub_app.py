"""
SCM Sub-Application for BIO-ERP v5
======================================
Mount at: app.mount("/api/v1/scm", scm_app) in BIO-ERP's main.py

Source: Arabic accounting curriculum — 36 files verified
Engines: TDABC, Traditional Costing, ABC, RCA, Target Costing, BSC, Responsibility, ROI/EVA
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from decimal import Decimal
import warnings
warnings.filterwarnings("ignore", message=".*protected namespace.*")

from app.organs.scm_organ.scm_erp_module import (
    SCMERPModule,
    TDABCResourcePool, TDABCProduct, TradCostPool, TradProductAllocation,
    ABCActivityPool, ABCCostDriver, ABCAllocation, ABCProductCost,
    RCAResource, RCAResourceOutput,
    TargetMarketModel, TargetCostSheet, TargetVEAction,
    ROI_EVABaseline, ROI_EVACalculation,
    ResponsibilityBudget,
    BSCKPIMeasurement,
)

scm_app = FastAPI(
    title="SCM Costing & Performance Microservice",
    description="Supply Chain Costing Module — TDABC, ABC, RCA, Target, BSC, Responsibility, ROI/EVA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

scm_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scm_module = SCMERPModule()

# =============================================================================
# PYDANTIC SCHEMAS — TDABC (P0)
# =============================================================================

class TDABCPoolSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    total_cost: float = Field(..., gt=0)
    resources_count: int = Field(..., gt=0)
    days_per_year: int = Field(default=250, ge=1, le=366)
    hours_per_day: int = Field(default=8, ge=1, le=24)
    efficiency_pct: float = Field(default=85.0, gt=0, le=100)

class TDABCProductSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    volume: int = Field(..., gt=0)
    time_per_unit_minutes: float = Field(..., gt=0)

class TDABCVarianceSchema(BaseModel):
    total_cost: float = Field(..., gt=0)
    resources_count: int = Field(..., gt=0)
    efficiency_pct: float = Field(default=85.0, gt=0, le=100)
    used_minutes: float = Field(..., ge=0)

class TradPoolSchema(BaseModel):
    pool_name: str = Field(..., min_length=1)
    total_overhead: float = Field(..., gt=0)
    allocation_base: Literal["DIRECT_LABOR_HOURS", "MACHINE_HOURS", "DIRECT_LABOR_COST", "UNITS_PRODUCED"]
    base_quantity: float = Field(..., gt=0)

class TradAllocationSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    actual_base_consumption: float = Field(..., gt=0)

class CostComparisonSchema(BaseModel):
    tdabc_pool: TDABCPoolSchema
    tdabc_product: TDABCProductSchema
    trad_pool: TradPoolSchema
    trad_allocation: TradAllocationSchema

# =============================================================================
# PYDANTIC SCHEMAS — ABC (P1)
# =============================================================================

class ABCPoolSchema(BaseModel):
    pool_name: str = Field(..., min_length=1)
    total_cost: float = Field(..., gt=0)
    cost_category: Literal["UNIT_LEVEL", "BATCH_LEVEL", "PRODUCT_LEVEL", "FACILITY_LEVEL"]

class ABCDriverSchema(BaseModel):
    driver_name: str = Field(..., min_length=1)
    driver_type: Literal["TRANSACTION", "DURATION", "INTENSITY"]
    measurement_unit: str = Field(..., min_length=1)

class ABCAllocationSchema(BaseModel):
    driver_quantity: float = Field(..., gt=0)

class ABCProductCostSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    consumption_quantity: float = Field(..., gt=0)

class RCAResourceSchema(BaseModel):
    resource_name: str = Field(..., min_length=1)
    fixed_cost: float = Field(default=0.0, ge=0)
    proportional_cost: float = Field(default=0.0, ge=0)
    measurable_output_unit: str = Field(default="units")

class RCAOutputSchema(BaseModel):
    planned_quantity: float = Field(..., gt=0)
    actual_quantity: float = Field(..., ge=0)

class TargetModelSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    market_price: float = Field(..., gt=0)
    target_profit_pct: float = Field(..., gt=0, le=100)

class TargetSheetSchema(BaseModel):
    cost_component: Literal["MATERIAL_SOURCING", "DIRECT_LABOR", "MACHINE_COSTS", "PURCHASE_ORDERS", "INSPECTION", "STORAGE"]
    as_is_cost: float = Field(..., ge=0)
    target_cost: float = Field(..., ge=0)

class TargetVESchema(BaseModel):
    action_name: str = Field(..., min_length=1)
    estimated_savings: float = Field(..., ge=0)
    implementation_cost: float = Field(..., ge=0)
    status: str = Field(default="PROPOSED")

# =============================================================================
# PYDANTIC SCHEMAS — BSC / RESPONSIBILITY / ROI-EVA (P2)
# =============================================================================

class BSCPerspectiveSchema(BaseModel):
    perspective_name: Literal["FINANCIAL", "CUSTOMER", "INTERNAL_PROCESSES", "LEARNING_GROWTH"]
    weight_pct: float = Field(default=25.0, ge=0, le=100)

class BSCMeasurementSchema(BaseModel):
    perspective_name: str
    actual_value: float = Field(..., ge=0)
    target_value: float = Field(..., gt=0)

class RespCenterSchema(BaseModel):
    center_code: str = Field(..., min_length=1)
    center_name: str = Field(..., min_length=1)
    center_type: Literal["COST_CENTER", "REVENUE_CENTER", "PROFIT_CENTER", "INVESTMENT_CENTER"]
    parent_center_code: Optional[str] = None
    manager_name: str = ""

class RespBudgetSchema(BaseModel):
    budgeted_amount: float = Field(..., gt=0)
    actual_amount: float = Field(default=0.0)

class ROI_BaselineSchema(BaseModel):
    investment_name: str = Field(..., min_length=1)
    initial_investment: float = Field(..., gt=0)
    operating_profit: float = Field(...)
    total_assets: float = Field(..., gt=0)
    current_liabilities: float = Field(default=0.0, ge=0)

class ROI_CalcSchema(BaseModel):
    nopat: float = Field(...)
    wacc_pct: float = Field(..., ge=0, le=100)

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================

@scm_app.get("/")
def root():
    return {
        "service": "SCM Costing & Performance Microservice",
        "version": "1.0.0",
        "source": "Arabic accounting curriculum — 36 files verified",
        "engines": ["TDABC_Costing", "Traditional_Costing", "ABC", "RCA",
                    "Target_Costing", "BSC", "Responsibility_Accounting", "ROI_EVA"],
        "docs": "/docs",
        "health": "/health",
    }

@scm_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "scm-erp",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "tdabc_costing", "traditional_costing", "abc",
            "rca", "target_costing", "bsc",
            "responsibility_accounting", "roi_eva",
        ],
    }

# =============================================================================
# ENDPOINTS — TDABC (P0)
# =============================================================================

@scm_app.post("/tdabc/calculate-pool")
def tdabc_calculate_pool(pool: TDABCPoolSchema):
    try:
        p = TDABCResourcePool(**pool.model_dump())
        result = scm_module.tdabc_engine.calculate_practical_capacity(p)
        scm_module._log("TDABC_CALCULATE_POOL", pool.model_dump())
        return {"success": True, "pool_name": p.name, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/tdabc/calculate-product-cost")
def tdabc_product_cost(pool: TDABCPoolSchema, product: TDABCProductSchema):
    try:
        p = TDABCResourcePool(**pool.model_dump())
        pr = TDABCProduct(**product.model_dump())
        cost = scm_module.tdabc_engine.calculate_product_cost(p, pr)
        scm_module._log("TDABC_PRODUCT_COST", {"pool": pool.model_dump(), "product": product.model_dump()})
        return {"success": True, "product_name": pr.product_name, "total_cost": cost,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/tdabc/idle-capacity")
def tdabc_idle_capacity(variance: TDABCVarianceSchema):
    try:
        pool = TDABCResourcePool(
            name="variance_analysis", total_cost=variance.total_cost,
            resources_count=variance.resources_count, efficiency_pct=variance.efficiency_pct,
        )
        result = scm_module.tdabc_engine.calculate_idle_capacity(pool, variance.used_minutes)
        scm_module._log("TDABC_IDLE_CAPACITY", variance.model_dump())
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Traditional Costing (P0)
# =============================================================================

@scm_app.post("/traditional/calculate-rate")
def trad_calculate_rate(pool: TradPoolSchema):
    try:
        p = TradCostPool(**pool.model_dump())
        rate = scm_module.tdabc_engine.calculate_traditional_rate(p)
        scm_module._log("TRAD_RATE", pool.model_dump())
        return {"success": True, "pool_name": p.pool_name, "predetermined_rate": rate,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/traditional/allocate")
def trad_allocate(pool: TradPoolSchema, allocation: TradAllocationSchema):
    try:
        p = TradCostPool(**pool.model_dump())
        a = TradProductAllocation(**allocation.model_dump())
        cost = scm_module.tdabc_engine.calculate_traditional_allocation(p, a)
        scm_module._log("TRAD_ALLOCATE", {"pool": pool.model_dump(), "allocation": allocation.model_dump()})
        return {"success": True, "product_name": a.product_name, "allocated_cost": cost,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Cost Comparison (P0)
# =============================================================================

@scm_app.post("/comparison/cost-distortion")
def cost_comparison(req: CostComparisonSchema):
    try:
        tp = TDABCResourcePool(**req.tdabc_pool.model_dump())
        tpr = TDABCProduct(**req.tdabc_product.model_dump())
        trp = TradCostPool(**req.trad_pool.model_dump())
        tra = TradProductAllocation(**req.trad_allocation.model_dump())
        result = scm_module.tdabc_engine.compare_costing(tp, tpr, trp, tra)
        scm_module._log("COST_COMPARISON", req.model_dump())
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — ABC (P1)
# =============================================================================

@scm_app.post("/abc/calculate-activity-rate")
def abc_activity_rate(pool: ABCPoolSchema, allocation: ABCAllocationSchema):
    try:
        p = ABCActivityPool(**pool.model_dump())
        rate = scm_module.abc_rca_target_engine.calculate_activity_rate(p, allocation.driver_quantity)
        scm_module._log("ABC_RATE", pool.model_dump())
        return {"success": True, "pool_name": p.pool_name, "activity_rate": rate,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/abc/calculate-product-cost")
def abc_product_cost(pool: ABCPoolSchema, allocation: ABCAllocationSchema, product_cost: ABCProductCostSchema):
    try:
        p = ABCActivityPool(**pool.model_dump())
        cost = scm_module.abc_rca_target_engine.calculate_abc_product_cost(
            p, allocation.driver_quantity, product_cost.consumption_quantity
        )
        scm_module._log("ABC_PRODUCT_COST", {"pool": pool.model_dump(), "product": product_cost.model_dump()})
        return {"success": True, "product_name": product_cost.product_name, "allocated_cost": cost,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.get("/abc/pump-exercise")
def abc_pump_exercise():
    result = scm_module.abc_rca_target_engine.analyze_pump_exercise()
    scm_module._log("ABC_PUMP_EXERCISE", {})
    return {"success": True, **result, "timestamp": datetime.now().isoformat()}

@scm_app.post("/abc/pump-exercise-custom")
def abc_pump_exercise_custom(data: dict):
    try:
        result = scm_module.abc_rca_target_engine.analyze_pump_exercise(data)
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — RCA (P1)
# =============================================================================

@scm_app.post("/rca/total-cost")
def rca_total_cost(resource: RCAResourceSchema):
    try:
        r = RCAResource(**resource.model_dump())
        total = scm_module.abc_rca_target_engine.calculate_rca_total_cost(r)
        scm_module._log("RCA_TOTAL_COST", resource.model_dump())
        return {"success": True, "resource_name": r.resource_name, "total_cost": total,
                "fixed_cost": r.fixed_cost, "proportional_cost": r.proportional_cost,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/rca/utilization")
def rca_utilization(output: RCAOutputSchema):
    try:
        o = RCAResourceOutput(**output.model_dump())
        util = scm_module.abc_rca_target_engine.calculate_rca_utilization(o)
        scm_module._log("RCA_UTILIZATION", output.model_dump())
        return {"success": True, "capacity_utilization_pct": util,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Target Costing (P1)
# =============================================================================

@scm_app.post("/target/calculate")
def target_calculate(model: TargetModelSchema):
    try:
        m = TargetMarketModel(**model.model_dump())
        result = scm_module.abc_rca_target_engine.calculate_target_cost(m.market_price, m.target_profit_pct)
        scm_module._log("TARGET_CALCULATE", model.model_dump())
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/target/cost-sheet")
def target_cost_sheet(sheet: TargetSheetSchema):
    try:
        gap = scm_module.abc_rca_target_engine.calculate_target_gap(sheet.as_is_cost, sheet.target_cost)
        scm_module._log("TARGET_SHEET", sheet.model_dump())
        return {"success": True, "cost_component": sheet.cost_component,
                "as_is_cost": sheet.as_is_cost, "target_cost": sheet.target_cost,
                "gap": gap, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/target/summary")
def target_summary(sheets: List[TargetSheetSchema], ve_actions: List[TargetVESchema], model: TargetModelSchema):
    try:
        m = TargetMarketModel(**model.model_dump())
        target = scm_module.abc_rca_target_engine.calculate_target_cost(m.market_price, m.target_profit_pct)
        result = scm_module.abc_rca_target_engine.calculate_target_summary(
            [s.model_dump() for s in sheets],
            [a.model_dump() for a in ve_actions],
            target["target_cost"],
        )
        scm_module._log("TARGET_SUMMARY", {"model": model.model_dump(), "sheets": len(sheets), "ve": len(ve_actions)})
        return {"success": True, "product_name": m.product_name, "target_cost": target["target_cost"],
                **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — BSC (P2)
# =============================================================================

@scm_app.post("/bsc/measurement")
def bsc_measurement(measurement: BSCMeasurementSchema):
    try:
        vp = scm_module.bsc_resp_roi_engine.calculate_kpi_variance(measurement.actual_value, measurement.target_value)
        status = scm_module.bsc_resp_roi_engine.calculate_performance_status(vp)
        scm_module._log("BSC_MEASUREMENT", measurement.model_dump())
        return {"success": True, "perspective": measurement.perspective_name,
                "variance_pct": vp, "performance_status": status,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/bsc/scorecard")
def bsc_scorecard(measurements: List[BSCMeasurementSchema],
                  perspectives: List[BSCPerspectiveSchema] = None):
    try:
        if perspectives is None:
            perspectives = [BSCPerspectiveSchema(perspective_name=p, weight_pct=25.0)
                           for p in ["FINANCIAL", "CUSTOMER", "INTERNAL_PROCESSES", "LEARNING_GROWTH"]]
        result = scm_module.bsc_resp_roi_engine.calculate_bsc_scorecard(
            [m.model_dump() for m in measurements],
            [p.model_dump() for p in perspectives],
        )
        scm_module._log("BSC_SCORECARD", {"measurements": len(measurements), "perspectives": len(perspectives)})
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.get("/bsc/seed-perspectives")
def bsc_seed_perspectives():
    result = scm_module.bsc_resp_roi_engine.seed_bsc_perspectives()
    return {"success": True, "perspectives": result, "timestamp": datetime.now().isoformat()}

# =============================================================================
# ENDPOINTS — Responsibility Accounting (P2)
# =============================================================================

@scm_app.post("/resp/budget-variance")
def resp_budget_variance(budget: RespBudgetSchema):
    try:
        b = ResponsibilityBudget(**budget.model_dump())
        result = scm_module.bsc_resp_roi_engine.calculate_budget_variance(b.budgeted_amount, b.actual_amount)
        scm_module._log("RESP_BUDGET_VARIANCE", budget.model_dump())
        return {"success": True, "budgeted": b.budgeted_amount, "actual": b.actual_amount,
                **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/resp/net-variance")
def resp_net_variance(favorable: float = Query(...), unfavorable: float = Query(...)):
    net = scm_module.bsc_resp_roi_engine.calculate_net_variance(favorable, unfavorable)
    return {"success": True, "favorable": favorable, "unfavorable": unfavorable,
            "net_variance": net, "timestamp": datetime.now().isoformat()}

@scm_app.get("/resp/seed-hierarchy")
def resp_seed_hierarchy():
    result = scm_module.bsc_resp_roi_engine.seed_responsibility_hierarchy()
    return {"success": True, "centers": result, "timestamp": datetime.now().isoformat()}

# =============================================================================
# ENDPOINTS — ROI/EVA (P2)
# =============================================================================

@scm_app.post("/roi-eva/analyze")
def roi_eva_analyze(baseline: ROI_BaselineSchema, calculation: ROI_CalcSchema):
    try:
        b = ROI_EVABaseline(**baseline.model_dump())
        c = ROI_EVACalculation(**calculation.model_dump())
        result = scm_module.bsc_resp_roi_engine.full_roi_eva_analysis(b, c)
        scm_module._log("ROI_EVA", {"baseline": baseline.model_dump(), "calculation": calculation.model_dump()})
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@scm_app.post("/roi-eva/quick")
def roi_eva_quick(nopat: float = Query(...), capital_employed: float = Query(...), wacc_pct: float = Query(...)):
    try:
        eva = scm_module.bsc_resp_roi_engine.calculate_eva(nopat, capital_employed, wacc_pct)
        roi = scm_module.bsc_resp_roi_engine.calculate_roi(nopat, capital_employed)
        charge = scm_module.bsc_resp_roi_engine.calculate_capital_charge(capital_employed, wacc_pct)
        return {"success": True, "nopat": nopat, "capital_employed": capital_employed,
                "wacc_pct": wacc_pct, "capital_charge": charge, "eva": eva, "roi_pct": roi,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Audit & Module Report
# =============================================================================

@scm_app.get("/audit-trail")
def audit_trail(limit: int = 100):
    trail = scm_module.get_audit_trail()
    return {"operations_count": len(trail), "operations": trail[-limit:] if limit else trail,
            "timestamp": datetime.now().isoformat()}

@scm_app.get("/report")
def module_report():
    return scm_module.get_module_report()


# =============================================================================
# P3 — Lightweight SCM Endpoints (Staging-Isolated)
# =============================================================================
from app.organs.scm_organ.scm_router import router as p3_scm_router
scm_app.include_router(p3_scm_router)

from app.organs.scm_organ.bank_reimport_router import router as bank_reimport_router
scm_app.include_router(bank_reimport_router)
