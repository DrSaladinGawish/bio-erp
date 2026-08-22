from fastapi import APIRouter
from datetime import datetime

from app.organs.risk_uncertainty_organ.schemas import (
    VaRCalculationSchema,
    MonteCarloSimulationSchema,
    BlackSwanDetectionSchema,
    SensitivityAnalysisSchema,
    DecisionTreeSchema,
    ScenarioAnalysisSchema,
)
from app.organs.risk_uncertainty_organ.services import (
    VaREngine,
    MonteCarloEngine,
    BlackSwanEngine,
    SensitivityEngine,
    DecisionTreeEngine,
    ScenarioAnalysisEngine,
)

router = APIRouter()


# =============================================================================
# ROOT & HEALTH
# =============================================================================


@router.get("/")
def root():
    return {
        "service": "Risk & Uncertainty Management Microservice",
        "version": "5.3.0",
        "techniques_count": 6,
        "techniques": [
            "value-at-risk",
            "monte-carlo-simulation",
            "black-swan-detection",
            "sensitivity-analysis",
            "decision-trees",
            "scenario-analysis",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "risk-uncertainty",
        "version": "5.3.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "var",
            "monte_carlo",
            "black_swan",
            "sensitivity",
            "decision_tree",
            "scenario",
        ],
    }


# =============================================================================
# 1. VALUE AT RISK (VaR)
# =============================================================================


@router.post("/var/calculate")
def var_calculate(req: VaRCalculationSchema):
    positions_data = [p.model_dump() for p in req.positions]
    result = VaREngine.calculate(
        portfolio_value=req.portfolio_value,
        positions=positions_data,
        method=req.method.value,
        confidence_level=req.confidence_level,
        time_horizon_days=req.time_horizon_days,
        n_simulations=req.n_simulations,
        historical_returns=req.historical_returns,
    )
    return {
        "success": True,
        "technique": "VALUE_AT_RISK",
        "portfolio_name": req.portfolio_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 2. MONTE CARLO SIMULATION
# =============================================================================


@router.post("/monte-carlo/run")
def monte_carlo_run(req: MonteCarloSimulationSchema):
    variables_data = [v.model_dump() for v in req.variables]
    result = MonteCarloEngine.run_simulation(
        variables=variables_data,
        n_simulations=req.n_simulations,
        seed=req.seed,
    )
    return {
        "success": True,
        "technique": "MONTE_CARLO",
        "simulation_name": req.simulation_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 3. BLACK SWAN DETECTION
# =============================================================================


@router.post("/black-swan/detect")
def black_swan_detect(req: BlackSwanDetectionSchema):
    result = BlackSwanEngine.detect_events(
        time_series=req.time_series,
        sigma_threshold=req.sigma_threshold,
    )
    return {
        "success": True,
        "technique": "BLACK_SWAN",
        "series_name": req.series_name,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 4. SENSITIVITY ANALYSIS
# =============================================================================


@router.post("/sensitivity/analyze")
def sensitivity_analyze(req: SensitivityAnalysisSchema):
    variables_data = [v.model_dump() for v in req.variables]
    result = SensitivityEngine.analyze(
        variables=variables_data,
        base_case_output=req.base_case_output,
    )
    return {
        "success": True,
        "technique": "SENSITIVITY",
        "analysis_name": req.analysis_name,
        "output_unit": req.output_unit,
        **result,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 5. DECISION TREES
# =============================================================================


@router.post("/decision-tree/evaluate")
def decision_tree_evaluate(req: DecisionTreeSchema):
    nodes_data = [n.model_dump() for n in req.nodes]
    node_map = DecisionTreeEngine.build_tree(nodes_data)
    result = DecisionTreeEngine.backward_induction(
        node_map, req.risk_aversion_factor,
    )
    return {
        "success": True,
        "technique": "DECISION_TREE",
        "tree_name": req.tree_name,
        **result,
        "risk_aversion_factor": req.risk_aversion_factor,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# 6. SCENARIO ANALYSIS
# =============================================================================


@router.post("/scenario/analyze")
def scenario_analyze(req: ScenarioAnalysisSchema):
    scenarios_data = [s.model_dump() for s in req.scenarios]
    result = ScenarioAnalysisEngine.analyze(
        scenarios=scenarios_data,
        risk_free_rate_pct=req.risk_free_rate_pct,
    )
    return {
        "success": True,
        "technique": "SCENARIO_ANALYSIS",
        "analysis_name": req.analysis_name,
        "output_metric": req.output_metric,
        **result,
        "timestamp": datetime.now().isoformat(),
    }
