"""
SCM ERP Module — Supply Chain Costing & Performance Engines
Follows OR module pattern: dataclass models + class-based stateless engines
Source: Arabic accounting curriculum — 36 files verified
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any
from enum import Enum
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import math

# =============================================================================
# DATA MODELS — TDABC (P0)
# =============================================================================

@dataclass
class TDABCResourcePool:
    name: str
    total_cost: float
    resources_count: int
    days_per_year: int = 250
    hours_per_day: int = 8
    efficiency_pct: float = 85.0

@dataclass
class TDABCProduct:
    product_name: str
    volume: int
    time_per_unit_minutes: float

@dataclass
class TradCostPool:
    pool_name: str
    total_overhead: float
    allocation_base: str
    base_quantity: float

@dataclass
class TradProductAllocation:
    product_name: str
    actual_base_consumption: float

# =============================================================================
# DATA MODELS — ABC / RCA / TARGET (P1)
# =============================================================================

@dataclass
class ABCActivityPool:
    pool_name: str
    total_cost: float
    cost_category: str
    description: str = ""

@dataclass
class ABCCostDriver:
    driver_name: str
    driver_type: str
    measurement_unit: str

@dataclass
class ABCAllocation:
    driver_quantity: float

@dataclass
class ABCProductCost:
    product_name: str
    consumption_quantity: float

@dataclass
class RCAResource:
    resource_name: str
    fixed_cost: float = 0.0
    proportional_cost: float = 0.0
    measurable_output_unit: str = "units"

@dataclass
class RCAResourceOutput:
    planned_quantity: float
    actual_quantity: float

@dataclass
class TargetMarketModel:
    product_name: str
    market_price: float
    target_profit_pct: float

@dataclass
class TargetCostSheet:
    cost_component: str
    as_is_cost: float
    target_cost: float

@dataclass
class TargetVEAction:
    action_name: str
    estimated_savings: float
    implementation_cost: float

# =============================================================================
# DATA MODELS — BSC / RESPONSIBILITY / ROI-EVA (P2)
# =============================================================================

@dataclass
class BSCPerspective:
    perspective_name: str
    weight_pct: float = 25.0

@dataclass
class BSCStrategicObjective:
    objective_name: str
    perspective_id: int
    target_value: Optional[float] = None

@dataclass
class BSCKPI:
    kpi_name: str
    formula: str
    objective_id: int
    measurement_unit: str = ""

@dataclass
class BSCKPIMeasurement:
    actual_value: float
    target_value: float

@dataclass
class ResponsibilityCenter:
    center_code: str
    center_name: str
    center_type: str
    parent_center_code: Optional[str] = None
    manager_name: str = ""

@dataclass
class ResponsibilityBudget:
    budgeted_amount: float
    actual_amount: float = 0.0

@dataclass
class ROI_EVABaseline:
    investment_name: str
    initial_investment: float
    operating_profit: float
    total_assets: float
    current_liabilities: float = 0.0

@dataclass
class ROI_EVACalculation:
    nopat: float
    wacc_pct: float

# =============================================================================
# ENGINE 1: TDABC + Traditional Costing (P0)
# =============================================================================

class TDABCCostingEngine:
    """Time-Driven Activity-Based Costing + Traditional Costing computations"""

    @staticmethod
    def calculate_practical_capacity(pool: TDABCResourcePool) -> dict:
        theoretical = pool.resources_count * pool.days_per_year * pool.hours_per_day * 60
        practical = int(theoretical * pool.efficiency_pct / 100.0)
        cost_per_min = pool.total_cost / practical if practical > 0 else 0
        return {
            "theoretical_minutes": theoretical,
            "practical_minutes": practical,
            "cost_per_minute": round(cost_per_min, 4),
        }

    @staticmethod
    def calculate_product_cost(pool: TDABCResourcePool, product: TDABCProduct) -> float:
        metrics = TDABCCostingEngine.calculate_practical_capacity(pool)
        cost = product.volume * product.time_per_unit_minutes * metrics["cost_per_minute"]
        return round(cost, 4)

    @staticmethod
    def calculate_idle_capacity(pool: TDABCResourcePool, used_minutes: float) -> dict:
        metrics = TDABCCostingEngine.calculate_practical_capacity(pool)
        practical = metrics["practical_minutes"]
        if used_minutes < practical:
            idle = practical - used_minutes
            deficit = 0
            vtype = "IDLE_CAPACITY"
        elif used_minutes > practical:
            idle = 0
            deficit = used_minutes - practical
            vtype = "CAPACITY_DEFICIT"
        else:
            idle = 0
            deficit = 0
            vtype = "BALANCED"
        return {
            "idle_minutes": round(idle, 2),
            "deficit_minutes": round(deficit, 2),
            "variance_type": vtype,
            "practical_minutes": practical,
            "cost_per_minute": metrics["cost_per_minute"],
        }

    @staticmethod
    def calculate_traditional_rate(pool: TradCostPool) -> float:
        if pool.base_quantity <= 0:
            return 0.0
        return round(pool.total_overhead / pool.base_quantity, 4)

    @staticmethod
    def calculate_traditional_allocation(pool: TradCostPool, allocation: TradProductAllocation) -> float:
        rate = TDABCCostingEngine.calculate_traditional_rate(pool)
        return round(allocation.actual_base_consumption * rate, 4)

    @staticmethod
    def compare_costing(tdabc_pool: TDABCResourcePool, tdabc_product: TDABCProduct,
                        trad_pool: TradCostPool, trad_allocation: TradProductAllocation) -> dict:
        tdabc_cost = TDABCCostingEngine.calculate_product_cost(tdabc_pool, tdabc_product)
        trad_cost = TDABCCostingEngine.calculate_traditional_allocation(trad_pool, trad_allocation)
        distortion = abs(tdabc_cost - trad_cost)
        distortion_pct = round((distortion / trad_cost) * 100, 2) if trad_cost > 0 else 100.0
        if tdabc_cost > trad_cost:
            interp = f"Traditional system UNDER-costs by {distortion:.2f} ({distortion_pct:.2f}%)"
        elif tdabc_cost < trad_cost:
            interp = f"Traditional system OVER-costs by {distortion:.2f} ({distortion_pct:.2f}%)"
        else:
            interp = "No distortion detected — identical cost"
        return {
            "tdabc_cost": round(tdabc_cost, 4),
            "traditional_cost": round(trad_cost, 4),
            "cost_distortion": round(distortion, 4),
            "distortion_pct": distortion_pct,
            "interpretation": interp,
        }

# =============================================================================
# ENGINE 2: ABC + RCA + Target Costing (P1)
# =============================================================================

class ABCRCATargetEngine:
    """Activity-Based Costing, Resource Consumption Accounting, Target Costing"""

    # --- ABC ---
    @staticmethod
    def calculate_activity_rate(pool: ABCActivityPool, driver_quantity: float) -> float:
        if driver_quantity <= 0:
            return 0.0
        return round(pool.total_cost / driver_quantity, 4)

    @staticmethod
    def calculate_abc_product_cost(pool: ABCActivityPool, driver_quantity: float, consumption: float) -> float:
        rate = ABCRCATargetEngine.calculate_activity_rate(pool, driver_quantity)
        return round(consumption * rate, 4)

    @staticmethod
    def seed_pump_exercise_data() -> dict:
        """Seed data for the classic Pump A vs Pump B ABC exercise"""
        return {
            "pools": [
                {"pool_name": "Machine Setup", "total_cost": 10000.0, "cost_category": "BATCH_LEVEL"},
                {"pool_name": "Quality Inspection", "total_cost": 8000.0, "cost_category": "BATCH_LEVEL"},
                {"pool_name": "Machine Hours", "total_cost": 40000.0, "cost_category": "UNIT_LEVEL"},
            ],
            "drivers": [
                {"driver_name": "Number of Setups", "driver_type": "TRANSACTION", "measurement_unit": "setups"},
                {"driver_name": "Number of Inspections", "driver_type": "TRANSACTION", "measurement_unit": "inspections"},
                {"driver_name": "Machine Hours", "driver_type": "DURATION", "measurement_unit": "hours"},
            ],
            "allocations": [
                {"pool": "Machine Setup", "driver": "Number of Setups", "quantity": 20.0},
                {"pool": "Quality Inspection", "driver": "Number of Inspections", "quantity": 20.0},
                {"pool": "Machine Hours", "driver": "Machine Hours", "quantity": 5000.0},
            ],
            "pump_a_costs": [
                {"pool": "Machine Setup", "consumption": 10.0},
                {"pool": "Quality Inspection", "consumption": 10.0},
                {"pool": "Machine Hours", "consumption": 4000.0},
            ],
            "pump_b_costs": [
                {"pool": "Machine Setup", "consumption": 10.0},
                {"pool": "Quality Inspection", "consumption": 10.0},
                {"pool": "Machine Hours", "consumption": 1000.0},
            ],
        }

    @staticmethod
    def analyze_pump_exercise(data: dict = None) -> dict:
        """Analyze the Pump A/B exercise showing ABC vs Traditional cost distortion"""
        if data is None:
            data = ABCRCATargetEngine.seed_pump_exercise_data()
        pools = {p["pool_name"]: p for p in data["pools"]}
        allocs = {a["pool"]: a["quantity"] for a in data["allocations"]}

        def calc_product(costs: list) -> dict:
            details = []
            total = 0.0
            for c in costs:
                pool = pools[c["pool"]]
                rate = pool["total_cost"] / allocs[c["pool"]]
                cost = c["consumption"] * rate
                details.append({"pool": c["pool"], "rate": round(rate, 4), "cost": round(cost, 4)})
                total += cost
            return {"details": details, "total_cost": round(total, 4)}

        pump_a = calc_product(data["pump_a_costs"])
        pump_b = calc_product(data["pump_b_costs"])

        # Traditional: allocate by machine hours only
        total_machine_cost = pools["Machine Hours"]["total_cost"]
        total_hours = allocs["Machine Hours"]
        trad_rate = total_machine_cost / total_hours
        pump_a_trad = round(4000 * trad_rate, 4)
        pump_b_trad = round(1000 * trad_rate, 4)

        return {
            "pump_a_abc": pump_a,
            "pump_b_abc": pump_b,
            "pump_a_traditional": pump_a_trad,
            "pump_b_traditional": pump_b_trad,
            "abc_vs_traditional": {
                "pump_a": {"abc": pump_a["total_cost"], "traditional": pump_a_trad,
                           "distortion": round(pump_a_trad - pump_a["total_cost"], 4)},
                "pump_b": {"abc": pump_b["total_cost"], "traditional": pump_b_trad,
                           "distortion": round(pump_b_trad - pump_b["total_cost"], 4)},
            },
        }

    # --- RCA ---
    @staticmethod
    def calculate_rca_total_cost(resource: RCAResource) -> float:
        return round(resource.fixed_cost + resource.proportional_cost, 4)

    @staticmethod
    def calculate_rca_utilization(output: RCAResourceOutput) -> float:
        if output.planned_quantity <= 0:
            return 0.0
        return round(output.actual_quantity / output.planned_quantity * 100, 2)

    # --- Target Costing ---
    @staticmethod
    def calculate_target_cost(market_price: float, profit_pct: float) -> dict:
        profit_amount = market_price * profit_pct / 100
        target_cost = market_price - profit_amount
        return {
            "market_price": market_price,
            "target_profit_pct": profit_pct,
            "target_profit_amount": round(profit_amount, 4),
            "target_cost": round(target_cost, 4),
        }

    @staticmethod
    def calculate_target_gap(as_is_cost: float, target_cost: float) -> float:
        return round(as_is_cost - target_cost, 4)

    @staticmethod
    def calculate_target_summary(sheets: list, ve_actions: list, target_cost: float) -> dict:
        total_as_is = sum(s["as_is_cost"] for s in sheets)
        total_gap = sum(s["as_is_cost"] - s["target_cost"] for s in sheets)
        ve_savings = sum(
            a["estimated_savings"] - a["implementation_cost"]
            for a in ve_actions if a.get("status") in ("APPROVED", "IMPLEMENTED")
        )
        achievable = round(total_as_is - ve_savings, 4)
        gap_pct = round(total_gap / target_cost * 100, 2) if target_cost > 0 else 0.0
        if achievable <= target_cost:
            status = "ACHIEVABLE"
        elif achievable <= target_cost * 1.05:
            status = "GAP_REMAINS"
        else:
            status = "OVER_TARGET"
        return {
            "total_as_is": round(total_as_is, 4),
            "total_gap": round(total_gap, 4),
            "gap_pct": gap_pct,
            "ve_net_savings": round(ve_savings, 4),
            "achievable_target": achievable,
            "status": status,
        }

# =============================================================================
# ENGINE 3: BSC + Responsibility Accounting + ROI/EVA (P2)
# =============================================================================

class BSCResponsibilityROIEngine:
    """Balanced Scorecard, Responsibility Accounting, ROI/EVA"""

    # --- BSC ---
    @staticmethod
    def calculate_kpi_variance(actual: float, target: float) -> float:
        if target == 0:
            return 0.0
        return round((actual - target) / target * 100, 2)

    @staticmethod
    def calculate_performance_status(variance_pct: float) -> str:
        if variance_pct >= 0:
            return "ON_TARGET"
        elif variance_pct >= -10.0:
            return "WARNING"
        else:
            return "CRITICAL"

    @staticmethod
    def seed_bsc_perspectives() -> list:
        return [
            {"perspective_name": "FINANCIAL", "weight_pct": 25.0},
            {"perspective_name": "CUSTOMER", "weight_pct": 25.0},
            {"perspective_name": "INTERNAL_PROCESSES", "weight_pct": 25.0},
            {"perspective_name": "LEARNING_GROWTH", "weight_pct": 25.0},
        ]

    @staticmethod
    def calculate_bsc_scorecard(measurements: list, perspectives: list) -> dict:
        """Aggregate KPI measurements into perspective scores and overall BSC score"""
        pers_scores = {p["perspective_name"]: {"total": 0.0, "count": 0, "weight": p["weight_pct"]}
                       for p in perspectives}
        for m in measurements:
            pname = m.get("perspective_name")
            if pname in pers_scores:
                actual = m.get("actual_value", 0)
                target = m.get("target_value", 1)
                pct = (actual / target * 100) if target > 0 else 0
                pers_scores[pname]["total"] += pct
                pers_scores[pname]["count"] += 1

        summaries = []
        weighted_sum = 0.0
        for pname, ps in pers_scores.items():
            avg = round(ps["total"] / ps["count"], 2) if ps["count"] > 0 else 0.0
            weighted = round(avg * ps["weight"] / 100, 2)
            weighted_sum += weighted
            summaries.append({"perspective": pname, "avg_performance": avg, "weight": ps["weight"],
                              "weighted_contribution": weighted})
        overall = round(weighted_sum, 2)
        status = "EXCELLENT" if overall >= 90 else "GOOD" if overall >= 75 else "NEEDS_IMPROVEMENT"
        return {"perspective_summaries": summaries, "overall_score": overall, "status": status}

    # --- Responsibility Accounting ---
    @staticmethod
    def seed_responsibility_hierarchy() -> list:
        return [
            {"center_code": "CORP", "center_name": "Corporate HQ", "center_type": "INVESTMENT_CENTER",
             "parent_center_code": None, "manager_name": "CEO"},
            {"center_code": "MFG", "center_name": "Manufacturing Division", "center_type": "PROFIT_CENTER",
             "parent_center_code": "CORP", "manager_name": "VP Manufacturing"},
            {"center_code": "SALES", "center_name": "Sales Division", "center_type": "REVENUE_CENTER",
             "parent_center_code": "CORP", "manager_name": "VP Sales"},
            {"center_code": "ASSY", "center_name": "Assembly Department", "center_type": "COST_CENTER",
             "parent_center_code": "MFG", "manager_name": "Assembly Manager"},
        ]

    @staticmethod
    def calculate_budget_variance(budgeted: float, actual: float) -> dict:
        variance = actual - budgeted
        variance_pct = round(variance / budgeted * 100, 2) if budgeted != 0 else 0.0
        return {"variance": round(variance, 4), "variance_pct": variance_pct}

    @staticmethod
    def calculate_net_variance(favorable: float, unfavorable: float) -> float:
        return round(favorable - unfavorable, 4)

    # --- ROI/EVA ---
    @staticmethod
    def calculate_capital_employed(total_assets: float, current_liabilities: float) -> float:
        return round(total_assets - current_liabilities, 4)

    @staticmethod
    def calculate_capital_charge(capital_employed: float, wacc_pct: float) -> float:
        return round(capital_employed * wacc_pct / 100, 2)

    @staticmethod
    def calculate_eva(nopat: float, capital_employed: float, wacc_pct: float) -> float:
        charge = BSCResponsibilityROIEngine.calculate_capital_charge(capital_employed, wacc_pct)
        return round(nopat - charge, 2)

    @staticmethod
    def calculate_roi(nopat: float, capital_employed: float) -> float:
        if capital_employed == 0:
            return 0.0
        return round(nopat / capital_employed * 100, 2)

    @staticmethod
    def full_roi_eva_analysis(baseline: ROI_EVABaseline, calc: ROI_EVACalculation) -> dict:
        ce = BSCResponsibilityROIEngine.calculate_capital_employed(baseline.total_assets, baseline.current_liabilities)
        charge = BSCResponsibilityROIEngine.calculate_capital_charge(ce, calc.wacc_pct)
        eva = BSCResponsibilityROIEngine.calculate_eva(calc.nopat, ce, calc.wacc_pct)
        roi = BSCResponsibilityROIEngine.calculate_roi(calc.nopat, ce)
        return {
            "investment_name": baseline.investment_name,
            "capital_employed": ce,
            "nopat": calc.nopat,
            "wacc_pct": calc.wacc_pct,
            "capital_charge": charge,
            "eva": eva,
            "roi_pct": roi,
            "interpretation": f"EVA={eva:.2f} (positive=value created), ROI={roi:.2f}%",
        }

# =============================================================================
# MASTER SCM MODULE — exposes all engines
# =============================================================================

class SCMERPModule:
    """Master SCM ERP module — aggregates all costing & performance engines"""

    def __init__(self):
        self.tdabc_engine = TDABCCostingEngine()
        self.abc_rca_target_engine = ABCRCATargetEngine()
        self.bsc_resp_roi_engine = BSCResponsibilityROIEngine()
        self._audit_trail: list = []

    def _log(self, action: str, data: dict):
        self._audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data_summary": {k: str(v)[:80] for k, v in data.items()},
        })

    def get_audit_trail(self) -> list:
        return self._audit_trail

    def get_module_report(self) -> dict:
        return {
            "module": "SCM ERP",
            "version": "1.0.0",
            "engines": ["TDABC_Costing", "Traditional_Costing", "ABC", "RCA",
                        "Target_Costing", "BSC", "Responsibility_Accounting", "ROI_EVA"],
            "audit_entries": len(self._audit_trail),
        }
