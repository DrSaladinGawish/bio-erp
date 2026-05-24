"""Pure math functions for bio-manufacturing calculators.

Ported from Flask bio_calculator.py — exact formulas, exact defaults.
Separated from HTTP layer for unit testability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# ── ATP Cost ─────────────────────────────────────────────────────

@dataclass
class ATPCostResult:
    total_atp_mol: float = 0.0
    total_cost_egp: float = 0.0
    cost_per_product_mol: float = 0.0


def calculate_atp_cost(
    substrate_mol: float,
    atp_per_mol: float,
    egp_per_atp: float = 0.001,
) -> ATPCostResult:
    if substrate_mol < 0:
        raise ValueError("substrate_mol must be >= 0")
    if atp_per_mol < 0:
        raise ValueError("atp_per_mol must be >= 0")
    if egp_per_atp < 0:
        raise ValueError("egp_per_atp must be >= 0")
    total_atp = substrate_mol * atp_per_mol
    return ATPCostResult(
        total_atp_mol=total_atp,
        total_cost_egp=total_atp * egp_per_atp,
        cost_per_product_mol=egp_per_atp * atp_per_mol,
    )


# ── Enzyme Efficiency (Michaelis-Menten) ─────────────────────────

def enzyme_efficiency(
    vmax: float,
    km: float,
    substrate_conc: float,
) -> float:
    if vmax < 0:
        raise ValueError("vmax must be >= 0")
    if km <= 0:
        raise ValueError("km must be > 0")
    if substrate_conc < 0:
        raise ValueError("substrate_conc must be >= 0")
    return vmax * substrate_conc / (km + substrate_conc)


# ── Batch Optimization ───────────────────────────────────────────

def batch_optimization(
    biomass_target_gl: float,
    time_limit_hr: float,
    cost_constraint_egp: float,
    doubling_time_hr: float = 24.0,
    cost_per_l_per_hr: float = 0.5,
) -> dict[str, Any]:
    if biomass_target_gl <= 0:
        raise ValueError("biomass_target_gl must be > 0")
    if time_limit_hr <= 0:
        raise ValueError("time_limit_hr must be > 0")
    if cost_constraint_egp <= 0:
        raise ValueError("cost_constraint_egp must be > 0")
    if doubling_time_hr <= 0:
        raise ValueError("doubling_time_hr must be > 0")
    if cost_per_l_per_hr < 0:
        raise ValueError("cost_per_l_per_hr must be >= 0")

    generations_needed = math.log2(max(biomass_target_gl, 1))
    min_time = generations_needed * doubling_time_hr
    feasible = min_time <= time_limit_hr
    optimal_time = min_time if feasible else time_limit_hr

    estimated_cost = optimal_time * cost_per_l_per_hr
    if estimated_cost > cost_constraint_egp:
        scale_factor = cost_constraint_egp / estimated_cost if estimated_cost > 0 else 0
        optimal_cost = cost_constraint_egp
        optimal_yield = biomass_target_gl * scale_factor
    else:
        optimal_cost = estimated_cost
        optimal_yield = biomass_target_gl

    return {
        "feasible": feasible,
        "optimal_time_hr": round(optimal_time, 2),
        "optimal_yield_gl": round(optimal_yield, 4),
        "optimal_cost_egp": round(optimal_cost, 2),
        "generations_needed": round(generations_needed, 1),
        "min_time_hr": round(min_time, 2),
    }


# ── Sensitivity Analysis ─────────────────────────────────────────

def sensitivity_analysis(
    base_value: float,
    param_range: float,
    steps: int = 10,
) -> list[dict[str, float]]:
    if param_range < 0:
        raise ValueError("param_range must be >= 0")
    if steps < 2:
        return [{"step": 0, "value": base_value}]
    step_size = (param_range * 2) / (steps - 1)
    results = []
    for i in range(steps):
        val = base_value - param_range + i * step_size
        results.append({"step": i, "value": round(val, 4)})
    return results


# ── Gene Expression Cost ─────────────────────────────────────────

INDUCTION_COST_MAP = {
    "iptg": 5.0,
    "heat": 2.0,
    "auto": 1.0,
    "constitutive": 0.0,
}

def gene_expression_cost(
    plasmid_size_kb: float,
    copy_number: int = 50,
    induction_method: str = "iptg",
) -> dict[str, float]:
    if plasmid_size_kb <= 0:
        raise ValueError("plasmid_size_kb must be > 0")
    if copy_number < 1:
        raise ValueError("copy_number must be >= 1")

    base_cost = 50.0
    size_factor = plasmid_size_kb * 10.0
    copy_factor = copy_number * 0.5
    induction = INDUCTION_COST_MAP.get(induction_method.lower(), 5.0)
    total = base_cost + size_factor + copy_factor + induction

    return {
        "construction_cost_egp": round(total, 2),
        "size_factor_egp": round(size_factor, 2),
        "copy_factor_egp": round(copy_factor, 2),
        "induction_cost_egp": induction,
    }


# ── Organ Line Throughput ────────────────────────────────────────

ORGAN_EFFICIENCY_FACTORS = {
    "liver": 0.8,
    "kidney": 0.6,
    "heart": 0.5,
    "lung": 0.7,
    "pancreas": 0.4,
}

def organ_line_throughput(
    organ_type: str = "liver",
    cell_density_cells_per_ml: float = 1e7,
    perfusion_rate_ml_per_min: float = 1.0,
) -> dict[str, float]:
    if cell_density_cells_per_ml <= 0:
        raise ValueError("cell_density_cells_per_ml must be > 0")
    if perfusion_rate_ml_per_min <= 0:
        raise ValueError("perfusion_rate_ml_per_min must be > 0")

    factor = ORGAN_EFFICIENCY_FACTORS.get(organ_type.lower(), 0.5)
    daily_volume_ml = perfusion_rate_ml_per_min * 60 * 24
    throughput = daily_volume_ml * cell_density_cells_per_ml * factor / 1e6

    return {
        "throughput_million_cells_per_day": round(throughput, 2),
        "daily_volume_ml": round(daily_volume_ml, 2),
        "efficiency_factor": factor,
    }
