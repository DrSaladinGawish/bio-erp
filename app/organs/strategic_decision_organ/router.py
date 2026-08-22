"""
Strategic Decision-Making Router — FastAPI Async Endpoints
BIO-ERP v5.3.0 — strategic_decision_organ

10 Techniques with POST endpoints returning {success, result, interpretation, timestamp}
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.organs.strategic_decision_organ.schemas import (
    AHPSchema,
    RealOptionsSchema,
    DecisionTreeSchema,
    CostBenefitSchema,
    MCDASchema,
    GameTheorySchema,
    SensitivityAnalysisSchema,
    RiskRewardSchema,
    DelphiSchema,
    StrategicChoiceSchema,
)
from app.organs.strategic_decision_organ.services import (
    AHPEngine,
    RealOptionsEngine,
    DecisionTreeEngine,
    CostBenefitEngine,
    MCDMEngine,
    GameTheoryEngine,
    SensitivityEngine,
    RiskRewardEngine,
    DelphiEngine,
    StrategicChoiceEngine,
)

router = APIRouter()


# =============================================================================
# ROOT & HEALTH
# =============================================================================


@router.get("/")
def root():
    return {
        "service": "Strategic Decision-Making Microservice",
        "version": "5.3.0",
        "techniques_count": 10,
        "techniques": [
            "ahp",
            "real-options",
            "decision-trees",
            "cost-benefit",
            "mcda",
            "game-theory",
            "sensitivity",
            "risk-reward",
            "delphi",
            "strategic-choice",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "strategic-decision",
        "version": "5.3.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "ahp",
            "real_options",
            "decision_trees",
            "cost_benefit",
            "mcda",
            "game_theory",
            "sensitivity",
            "risk_reward",
            "delphi",
            "strategic_choice",
        ],
    }


# =============================================================================
# 1. AHP (ANALYTIC HIERARCHY PROCESS)
# =============================================================================


@router.post("/ahp/analyze")
async def ahp_analyze(req: AHPSchema):
    try:
        n = len(req.criteria_names)
        if len(req.comparison_matrix) != n:
            raise ValueError("Comparison matrix must be n×n matching criteria count")
        for row in req.comparison_matrix:
            if len(row) != n:
                raise ValueError("Comparison matrix must be square")

        weights_result = AHPEngine.calculate_weights(req.comparison_matrix)
        rankings = AHPEngine.rank_alternatives(
            weights_result["weights"], req.alternative_scores, req.alternatives
        )
        best = rankings[0] if rankings else None

        interpretation = (
            f"AHP analysis for '{req.decision_name}': "
            f"Best alternative is '{best['alternative']}' "
            f"(score: {best['weighted_score']:.4f}). "
            f"Consistency ratio: {weights_result['consistency_ratio']:.4f} "
            f"({'consistent' if weights_result['is_consistent'] else 'inconsistent'})."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                "criteria_weights": dict(
                    zip(req.criteria_names, weights_result["weights"])
                ),
                "lambda_max": weights_result["lambda_max"],
                "consistency_index": weights_result["consistency_index"],
                "consistency_ratio": weights_result["consistency_ratio"],
                "is_consistent": weights_result["is_consistent"],
                "alternative_rankings": rankings,
                "best_alternative": best["alternative"] if best else None,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 2. REAL OPTIONS ANALYSIS
# =============================================================================


@router.post("/real-options/analyze")
async def real_options_analyze(req: RealOptionsSchema):
    try:
        result = RealOptionsEngine.evaluate_investment(
            req.initial_investment,
            req.project_value,
            req.volatility,
            req.risk_free_rate,
            req.time_to_expiry,
            req.n_steps,
        )
        interpretation = (
            f"Real Options for '{req.decision_name}': "
            f"Option value = {result['option_value']:.4f}, "
            f"Decision: {result['decision']}. "
            f"{result['rationale']}. "
            f"Delta = {result['delta']:.4f}, Gamma = {result['gamma']:.4f}, "
            f"Theta = {result['theta']:.4f}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 3. DECISION TREES
# =============================================================================


@router.post("/trees/analyze")
async def decision_trees_analyze(req: DecisionTreeSchema):
    try:
        nodes_map = {}
        for node in req.nodes:
            nodes_map[node.node_id] = {
                "node_type": node.node_type,
                "label": node.label,
                "branches": [b.model_dump() for b in node.branches],
            }

        node_values = DecisionTreeEngine.solve_tree(nodes_map, req.root_node_id)
        root_value = node_values.get(req.root_node_id, 0.0)

        chance_nodes = [
            {"branches": nodes_map[nid]["branches"]}
            for nid in nodes_map
            if nodes_map[nid]["node_type"] == "CHANCE"
        ]
        evpi = DecisionTreeEngine.calculate_evpi(chance_nodes)

        interpretation = (
            f"Decision Tree for '{req.decision_name}': "
            f"Expected value at root = {root_value:.4f}. "
            f"EVPI = {evpi:.4f}. "
            f"Optimal decision: {node_values.get(f'{req.root_node_id}__best', 'N/A')}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                "node_values": {
                    k: round(v, 4)
                    for k, v in node_values.items()
                    if not k.endswith("__best")
                },
                "root_value": round(root_value, 4),
                "evpi": evpi,
                "optimal_first_decision": node_values.get(f"{req.root_node_id}__best"),
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 4. COST-BENEFIT ANALYSIS
# =============================================================================


@router.post("/cost-benefit/analyze")
async def cost_benefit_analyze(req: CostBenefitSchema):
    try:
        costs = [c.model_dump() for c in req.costs]
        benefits = [b.model_dump() for b in req.benefits]
        result = CostBenefitEngine.analyze(
            costs, benefits, req.discount_rate, req.project_life
        )

        interpretation = (
            f"Cost-Benefit Analysis for '{req.decision_name}': "
            f"NPV = {result['npv']:.4f}, BCR = {result['bcr']:.4f}, "
            f"IRR = {result['irr']:.4%}, Payback = {result['payback_period']:.2f} years. "
            f"Decision: {result['decision']}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 5. MCDA (MULTI-CRITERIA DECISION ANALYSIS)
# =============================================================================


@router.post("/mcda/analyze")
async def mcda_analyze(req: MCDASchema):
    try:
        weights = [c.weight for c in req.criteria]
        criterion_types = [c.criterion_type for c in req.criteria]

        topsis = MCDMEngine.topsis(req.performance_matrix, weights, criterion_types)
        promethee = MCDMEngine.promethee(
            req.performance_matrix, weights, criterion_types
        )

        topsis_names = [req.alternatives[i] for i in topsis["ranking"]]
        promethee_names = [req.alternatives[i] for i in promethee["ranking"]]

        interpretation = (
            f"MCDA for '{req.decision_name}': "
            f"TOPSIS best = '{topsis_names[0]}' "
            f"(closeness = {topsis['closeness_coefficient'][topsis['ranking'][0]]:.4f}). "
            f"PROMETHEE best = '{promethee_names[0]}' "
            f"(net flow = {promethee['net_flow'][promethee['ranking'][0]]:.4f})."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                "topsis": {**topsis, "alternatives_ranked": topsis_names},
                "promethee": {**promethee, "alternatives_ranked": promethee_names},
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 6. GAME THEORY
# =============================================================================


@router.post("/game-theory/analyze")
async def game_theory_analyze(req: GameTheorySchema):
    try:
        result = GameTheoryEngine.analyze(
            req.payoff_matrix,
            req.player1_strategies,
            req.player2_strategies,
            req.game_type,
        )

        nash_str = (
            ", ".join(
                f"({ne['player1_strategy']}, {ne['player2_strategy']})"
                for ne in result["nash_equilibria"]
            )
            if result["nash_equilibria"]
            else "None found"
        )
        interpretation = (
            f"Game Theory for '{req.decision_name}': "
            f"{result['nash_count']} Nash equilibrium/a: [{nash_str}]. "
            f"Dominant P1: {result['dominant_strategies']['player1'] or 'None'}. "
            f"Dominant P2: {result['dominant_strategies']['player2'] or 'None'}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 7. SENSITIVITY ANALYSIS
# =============================================================================


@router.post("/sensitivity/analyze")
async def sensitivity_analyze(req: SensitivityAnalysisSchema):
    try:
        params = [v.model_dump() for v in req.variables]
        result = SensitivityEngine.analyze(params, req.base_outcome, req.variation_pct)

        interpretation = (
            f"Sensitivity Analysis for '{req.decision_name}': "
            f"Most sensitive variable: '{result['most_sensitive_variable']}'. "
            f"{len(result['breakeven_points'])} breakeven point(s) identified."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                "base_outcome": req.base_outcome,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 8. RISK-REWARD ANALYSIS
# =============================================================================


@router.post("/risk-reward/analyze")
async def risk_reward_analyze(req: RiskRewardSchema):
    try:
        options = [o.model_dump() for o in req.options]
        result = RiskRewardEngine.analyze(options, req.risk_free_rate)

        best_sharpe = result["max_sharpe_portfolio"]["dominant_asset"]
        interpretation = (
            f"Risk-Reward Analysis for '{req.decision_name}': "
            f"Best Sharpe ratio asset: '{best_sharpe}'. "
            f"Equal-weight portfolio Sharpe = {result['equal_weight_portfolio']['sharpe_ratio']:.4f}. "
            f"Max-Sharpe return = {result['max_sharpe_portfolio']['expected_return']:.4%}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 9. DELPHI METHOD
# =============================================================================


@router.post("/delphi/analyze")
async def delphi_analyze(req: DelphiSchema):
    try:
        rounds_data = [r.model_dump() for r in req.rounds]
        result = DelphiEngine.analyze_rounds(req.question, req.experts, rounds_data)

        interpretation = (
            f"Delphi for '{req.decision_name}': "
            f"Final median = {result['final_median']:.2f}, IQR = {result['final_iqr']:.2f}. "
            f"Consensus score = {result['consensus_score']:.4f}. "
            f"Convergence: {'Yes' if result['convergence_reached'] else 'No'}. "
            f"{result['interpretation']}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 10. STRATEGIC CHOICE
# =============================================================================


@router.post("/strategic-choice/analyze")
async def strategic_choice_analyze(req: StrategicChoiceSchema):
    try:
        options = [o.model_dump() for o in req.options]
        result = StrategicChoiceEngine.analyze(
            options,
            req.criteria_weights,
            req.risk_tolerance,
        )

        interpretation = (
            f"Strategic Choice for '{req.decision_name}': "
            f"Recommended strategy: '{result['recommended_strategy']}' "
            f"(confidence: {result['confidence_score']:.4f}). "
            f"Risk tolerance: {req.risk_tolerance}. "
            f"Mitigation steps: {len(result['risk_mitigation_plan'])}."
        )

        return {
            "success": True,
            "result": {
                "decision_name": req.decision_name,
                **result,
            },
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
