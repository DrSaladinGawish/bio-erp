"""Bio-manufacturing calculator endpoints.

Ported from Flask bio_analysis.py — exact input/output shapes.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.calculator_engine import (
    calculate_atp_cost,
    enzyme_efficiency,
    batch_optimization,
    sensitivity_analysis,
    gene_expression_cost,
    organ_line_throughput,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/bio/calculators", tags=["calculators"])


# ── Schemas ──────────────────────────────────────────────────────

class ATPCostInput(BaseModel):
    substrate_mol: float = Field(..., ge=0, description="Moles of substrate")
    atp_per_mol: float = Field(..., ge=0, description="ATP yield per mole of substrate")
    egp_per_atp: float = Field(0.001, ge=0, description="Cost per ATP in EGP")

class ATPCostOutput(BaseModel):
    total_atp_mol: float
    total_cost_egp: float
    cost_per_product_mol: float

class EnzymeInput(BaseModel):
    vmax: float = Field(..., ge=0, description="Maximum reaction velocity")
    km: float = Field(..., gt=0, description="Michaelis constant (must be > 0)")
    substrate_conc: float = Field(..., ge=0, description="Substrate concentration")

class EnzymeOutput(BaseModel):
    reaction_rate: float

class BatchOptInput(BaseModel):
    biomass_target_gl: float = Field(..., gt=0, description="Target biomass in g/L")
    time_limit_hr: float = Field(..., gt=0, description="Time limit in hours")
    cost_constraint_egp: float = Field(..., gt=0, description="Cost constraint in EGP")
    doubling_time_hr: float = Field(24.0, gt=0, description="Cell doubling time in hours")
    cost_per_l_per_hr: float = Field(0.5, ge=0, description="Cost per liter per hour")

class SensitivityInput(BaseModel):
    base_value: float = Field(..., description="Base parameter value")
    param_range: float = Field(..., ge=0, description="Perturbation range")
    steps: int = Field(10, ge=2, description="Number of steps")

class GeneCostInput(BaseModel):
    plasmid_size_kb: float = Field(..., gt=0, description="Plasmid size in kilobases")
    copy_number: int = Field(50, ge=1, description="Plasmid copy number")
    induction_method: str = Field("iptg", description="Induction method (iptg, heat, auto, constitutive)")

class ThroughputInput(BaseModel):
    organ_type: str = Field("liver", description="Organ type (liver, kidney, heart, lung, pancreas)")
    cell_density_cells_per_ml: float = Field(1e7, gt=0, description="Cell density")
    perfusion_rate_ml_per_min: float = Field(1.0, gt=0, description="Perfusion rate")


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/atp")
async def calc_atp(payload: ATPCostInput):
    try:
        result = calculate_atp_cost(
            substrate_mol=payload.substrate_mol,
            atp_per_mol=payload.atp_per_mol,
            egp_per_atp=payload.egp_per_atp,
        )
        return ATPCostOutput(
            total_atp_mol=result.total_atp_mol,
            total_cost_egp=result.total_cost_egp,
            cost_per_product_mol=result.cost_per_product_mol,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/enzyme")
async def calc_enzyme(payload: EnzymeInput):
    try:
        rate = enzyme_efficiency(
            vmax=payload.vmax,
            km=payload.km,
            substrate_conc=payload.substrate_conc,
        )
        return EnzymeOutput(reaction_rate=rate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/optimize")
async def calc_optimize(payload: BatchOptInput):
    try:
        return batch_optimization(
            biomass_target_gl=payload.biomass_target_gl,
            time_limit_hr=payload.time_limit_hr,
            cost_constraint_egp=payload.cost_constraint_egp,
            doubling_time_hr=payload.doubling_time_hr,
            cost_per_l_per_hr=payload.cost_per_l_per_hr,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sensitivity")
async def calc_sensitivity(payload: SensitivityInput):
    try:
        results = sensitivity_analysis(
            base_value=payload.base_value,
            param_range=payload.param_range,
            steps=payload.steps,
        )
        return {
            "parameter": "input",
            "base_value": payload.base_value,
            "results": results,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/gene-cost")
async def calc_gene_cost(payload: GeneCostInput):
    try:
        return gene_expression_cost(
            plasmid_size_kb=payload.plasmid_size_kb,
            copy_number=payload.copy_number,
            induction_method=payload.induction_method,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/throughput")
async def calc_throughput(payload: ThroughputInput):
    try:
        return organ_line_throughput(
            organ_type=payload.organ_type,
            cell_density_cells_per_ml=payload.cell_density_cells_per_ml,
            perfusion_rate_ml_per_min=payload.perfusion_rate_ml_per_min,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
