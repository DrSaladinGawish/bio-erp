"""
Strategic Decision-Making Services — 10 Techniques with Real Business Logic
BIO-ERP v5.3.0 — strategic_decision_organ

All engines are stateless static methods. No DB required for calculations.
numpy is used for matrix operations and statistical calculations.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np


# =============================================================================
# Saaty's Random Index for AHP consistency check
# =============================================================================
SAATY_RI = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}


class AHPEngine:
    """1. Analytic Hierarchy Process — Saaty's eigenvalue method"""

    @staticmethod
    def calculate_weights(matrix: List[List[float]]) -> dict:
        arr = np.array(matrix, dtype=float)
        n = arr.shape[0]
        eigenvalues, eigenvectors = np.linalg.eig(arr)
        max_idx = np.argmax(eigenvalues.real)
        lambda_max = eigenvalues[max_idx].real
        raw_weights = eigenvectors[:, max_idx].real
        weights = raw_weights / raw_weights.sum()

        ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
        ri = SAATY_RI.get(n, 1.59)
        cr = ci / ri if ri > 0 else 0.0
        is_consistent = cr < 0.10

        return {
            "weights": [round(float(w), 6) for w in weights],
            "lambda_max": round(float(lambda_max), 6),
            "consistency_index": round(float(ci), 6),
            "random_index": round(float(ri), 6),
            "consistency_ratio": round(float(cr), 6),
            "is_consistent": is_consistent,
            "interpretation": (
                "Consistent — judgments are reliable"
                if is_consistent
                else "Inconsistent — review pairwise comparisons (CR >= 0.10)"
            ),
        }

    @staticmethod
    def rank_alternatives(
        weights: List[float],
        alternative_scores: List[List[float]],
        alternatives: List[str],
    ) -> List[dict]:
        w = np.array(weights)
        scores = np.array(alternative_scores)
        weighted_scores = scores @ w
        ranking = np.argsort(-weighted_scores)
        results = []
        for rank_pos, idx in enumerate(ranking):
            results.append(
                {
                    "alternative": alternatives[idx],
                    "weighted_score": round(float(weighted_scores[idx]), 6),
                    "rank": rank_pos + 1,
                }
            )
        return results


class RealOptionsEngine:
    """2. Real Options Analysis — Black-Scholes option pricing"""

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return float(0.5 * (1.0 + math.erf(x / math.sqrt(2.0))))

    @staticmethod
    def black_scholes_call(
        spot: float, strike: float, time: float, rate: float, sigma: float
    ) -> dict:
        if time <= 0 or sigma <= 0:
            option_value = max(spot - strike, 0.0)
            return {
                "call_price": round(option_value, 6),
                "d1": 0.0,
                "d2": 0.0,
                "delta": 1.0 if spot > strike else 0.0,
                "gamma": 0.0,
                "theta": 0.0,
            }

        sqrt_t = math.sqrt(time)
        d1 = (math.log(spot / strike) + (rate + 0.5 * sigma**2) * time) / (
            sigma * sqrt_t
        )
        d2 = d1 - sigma * sqrt_t

        n_d1 = RealOptionsEngine._norm_cdf(d1)
        n_d2 = RealOptionsEngine._norm_cdf(d2)

        call = spot * n_d1 - strike * math.exp(-rate * time) * n_d2

        pdf_d1 = math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)
        delta = n_d1
        gamma = pdf_d1 / (spot * sigma * sqrt_t) if (spot * sigma * sqrt_t) > 0 else 0.0
        theta = (
            (
                -(spot * pdf_d1 * sigma) / (2 * sqrt_t)
                - rate * strike * math.exp(-rate * time) * n_d2
            )
            if time > 0
            else 0.0
        )

        return {
            "call_price": round(float(call), 6),
            "d1": round(float(d1), 6),
            "d2": round(float(d2), 6),
            "delta": round(float(delta), 6),
            "gamma": round(float(gamma), 6),
            "theta": round(float(theta), 6),
        }

    @staticmethod
    def evaluate_investment(
        initial_investment: float,
        project_value: float,
        volatility: float,
        risk_free_rate: float,
        time_to_expiry: float,
        n_steps: int,
    ) -> dict:
        bs = RealOptionsEngine.black_scholes_call(
            project_value,
            initial_investment,
            time_to_expiry,
            risk_free_rate,
            volatility,
        )

        if (
            bs["call_price"] > initial_investment * 0.1
            and project_value > initial_investment
        ):
            decision = "INVEST_NOW"
            rationale = "Option value exceeds threshold; project value justifies immediate investment"
        elif project_value > initial_investment * 0.8:
            decision = "WAIT"
            rationale = "Project has potential but timing could improve option value"
        else:
            decision = "ABANDON"
            rationale = "Project value insufficient to justify investment risk"

        return {
            "option_value": bs["call_price"],
            "intrinsic_value": round(max(project_value - initial_investment, 0.0), 4),
            "time_value": round(
                bs["call_price"] - max(project_value - initial_investment, 0.0), 4
            ),
            "d1": bs["d1"],
            "d2": bs["d2"],
            "delta": bs["delta"],
            "gamma": bs["gamma"],
            "theta": bs["theta"],
            "decision": decision,
            "rationale": rationale,
        }


class DecisionTreeEngine:
    """3. Decision Trees — backward induction (fold-back)"""

    @staticmethod
    def solve_tree(nodes: dict, root_id: str) -> dict:
        node_values = {}

        for _ in range(len(nodes) + 1):
            changed = False
            for nid, node in nodes.items():
                if nid in node_values:
                    continue
                if node["node_type"] == "CHANCE":
                    all_resolved = all(
                        b.get("child_id") is None or b.get("child_id") in node_values
                        for b in node["branches"]
                    )
                    if all_resolved:
                        emv = 0.0
                        for b in node["branches"]:
                            child_val = (
                                node_values.get(b.get("child_id"), 0.0)
                                if b.get("child_id")
                                else 0.0
                            )
                            emv += b["probability"] * (
                                b["payoff"] - b["cost"] + child_val
                            )
                        node_values[nid] = emv
                        changed = True
                elif node["node_type"] == "DECISION":
                    all_resolved = all(
                        b.get("child_id") is None or b.get("child_id") in node_values
                        for b in node["branches"]
                    )
                    if all_resolved:
                        best_val = -float("inf")
                        best_branch = None
                        for b in node["branches"]:
                            child_val = (
                                node_values.get(b.get("child_id"), 0.0)
                                if b.get("child_id")
                                else 0.0
                            )
                            val = b["payoff"] - b["cost"] + child_val
                            if val > best_val:
                                best_val = val
                                best_branch = b["branch_name"]
                        node_values[nid] = best_val
                        node_values[f"{nid}__best"] = best_branch
                        changed = True
            if not changed:
                break

        return node_values

    @staticmethod
    def calculate_evpi(chance_nodes: List[dict]) -> float:
        evpi = 0.0
        for node in chance_nodes:
            outcomes = [
                (b["probability"], b["payoff"] - b["cost"]) for b in node["branches"]
            ]
            expected = sum(p * v for p, v in outcomes)
            best_outcome = max(v for _, v in outcomes)
            evpi += max(best_outcome - expected, 0.0)
        return round(evpi, 4)


class CostBenefitEngine:
    """4. Cost-Benefit Analysis — NPV, BCR, IRR, payback, PI"""

    @staticmethod
    def analyze(
        costs: List[dict],
        benefits: List[dict],
        discount_rate: float,
        project_life: int,
    ) -> dict:
        cf = [0.0] * (project_life + 1)
        for c in costs:
            yr = int(c.get("timing", 0))
            if 0 <= yr <= project_life:
                cf[yr] -= c["amount"]
        for b in benefits:
            yr = int(b.get("timing", 0))
            if 0 <= yr <= project_life:
                cf[yr] += b["amount"]

        npv = sum(cf[t] / (1 + discount_rate) ** t for t in range(project_life + 1))
        total_pv_benefits = sum(
            b["amount"] / (1 + discount_rate) ** int(b.get("timing", 0))
            for b in benefits
        )
        total_pv_costs = sum(
            c["amount"] / (1 + discount_rate) ** int(c.get("timing", 0)) for c in costs
        )
        bcr = total_pv_benefits / total_pv_costs if total_pv_costs > 0 else 0.0
        pi = total_pv_benefits / total_pv_costs if total_pv_costs > 0 else 0.0

        cumulative = 0.0
        payback = float(project_life)
        for t in range(project_life + 1):
            cumulative += cf[t]
            if cumulative >= 0 and t > 0:
                payback = t
                break

        irr = CostBenefitEngine._calculate_irr(cf)

        return {
            "npv": round(float(npv), 4),
            "bcr": round(float(bcr), 4),
            "irr": round(float(irr), 6),
            "payback_period": round(float(payback), 2),
            "profitability_index": round(float(pi), 4),
            "total_pv_benefits": round(float(total_pv_benefits), 4),
            "total_pv_costs": round(float(total_pv_costs), 4),
            "decision": "ACCEPT" if npv > 0 and bcr > 1 else "REJECT",
        }

    @staticmethod
    def _calculate_irr(
        cashflows: List[float], max_iter: int = 200, tol: float = 1e-8
    ) -> float:
        rate = 0.1
        for _ in range(max_iter):
            npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))
            dnpv = sum(
                -t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows)
            )
            if abs(dnpv) < 1e-12:
                break
            rate -= npv / dnpv
            if abs(npv) < tol:
                break
        return float(rate)


class MCDMEngine:
    """5. MCDA — TOPSIS and PROMETHEE"""

    @staticmethod
    def topsis(
        performance_matrix: List[List[float]],
        weights: List[float],
        criterion_types: List[str],
    ) -> dict:
        matrix = np.array(performance_matrix, dtype=float)
        w = np.array(weights)
        w = w / w.sum()

        norm = np.sqrt((matrix**2).sum(axis=0))
        norm[norm == 0] = 1.0
        normalized = matrix / norm
        weighted = normalized * w

        ideal = np.zeros(weighted.shape[1])
        anti_ideal = np.zeros(weighted.shape[1])
        for j in range(weighted.shape[1]):
            if criterion_types[j] == "BENEFIT":
                ideal[j] = weighted[:, j].max()
                anti_ideal[j] = weighted[:, j].min()
            else:
                ideal[j] = weighted[:, j].min()
                anti_ideal[j] = weighted[:, j].max()

        d_plus = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
        d_minus = np.sqrt(((weighted - anti_ideal) ** 2).sum(axis=1))

        denominator = d_plus + d_minus
        denominator[denominator == 0] = 1.0
        closeness = d_minus / denominator

        ranking = np.argsort(-closeness)
        return {
            "d_plus": [round(float(d), 6) for d in d_plus],
            "d_minus": [round(float(d), 6) for d in d_minus],
            "closeness_coefficient": [round(float(c), 6) for c in closeness],
            "ranking": [int(i) for i in ranking],
        }

    @staticmethod
    def promethee(
        performance_matrix: List[List[float]],
        weights: List[float],
        criterion_types: List[str],
        preference_func: str = "LINEAR",
    ) -> dict:
        matrix = np.array(performance_matrix, dtype=float)
        w = np.array(weights)
        w = w / w.sum()
        n = matrix.shape[0]

        pref_matrix = np.zeros((n, n))
        for j in range(matrix.shape[1]):
            for i in range(n):
                for k in range(n):
                    diff = matrix[i, j] - matrix[k, j]
                    if criterion_types[j] == "COST":
                        diff = -diff
                    if diff > 0:
                        pref_matrix[i, k] += w[j] * diff

        pos_flow = pref_matrix.sum(axis=1) / (n - 1) if n > 1 else np.zeros(n)
        neg_flow = pref_matrix.sum(axis=0) / (n - 1) if n > 1 else np.zeros(n)
        net_flow = pos_flow - neg_flow

        ranking = np.argsort(-net_flow)
        return {
            "positive_flow": [round(float(p), 6) for p in pos_flow],
            "negative_flow": [round(float(nf), 6) for nf in neg_flow],
            "net_flow": [round(float(f), 6) for f in net_flow],
            "ranking": [int(i) for i in ranking],
        }


class GameTheoryEngine:
    """6. Game Theory — Nash equilibrium, dominant strategies, minimax"""

    @staticmethod
    def analyze(payoff_matrix, p1_strategies, p2_strategies, game_type: str) -> dict:
        n1 = len(p1_strategies)
        n2 = len(p2_strategies)
        p1_payoffs = np.array(
            [[payoff_matrix[i][j][0] for j in range(n2)] for i in range(n1)]
        )
        p2_payoffs = np.array(
            [[payoff_matrix[i][j][1] for j in range(n2)] for i in range(n1)]
        )

        nash_equilibria = []
        for i in range(n1):
            for j in range(n2):
                p1_best_response = all(
                    p1_payoffs[i, j] >= p1_payoffs[k, j] for k in range(n1)
                )
                p2_best_response = all(
                    p2_payoffs[i, j] >= p2_payoffs[i, k] for k in range(n2)
                )
                if p1_best_response and p2_best_response:
                    nash_equilibria.append(
                        {
                            "player1_strategy": p1_strategies[i],
                            "player2_strategy": p2_strategies[j],
                            "payoffs": [
                                float(p1_payoffs[i, j]),
                                float(p2_payoffs[i, j]),
                            ],
                        }
                    )

        dominant_p1 = []
        for i in range(n1):
            is_dominant = True
            for k in range(n1):
                if k != i:
                    if not all(p1_payoffs[i, j] >= p1_payoffs[k, j] for j in range(n2)):
                        is_dominant = False
                        break
            if is_dominant:
                dominant_p1.append(p1_strategies[i])

        dominant_p2 = []
        for j in range(n2):
            is_dominant = True
            for col in range(n2):
                if col != j:
                    if not all(
                        p2_payoffs[i, j] >= p2_payoffs[i, col] for i in range(n1)
                    ):
                        is_dominant = False
                        break
            if is_dominant:
                dominant_p2.append(p2_strategies[j])

        if game_type == "ZERO_SUM":
            max_col = p1_payoffs.max(axis=0)
            minimax_col = max_col.min()
            minimax_idx = np.unravel_index(
                np.argmin(np.abs(p1_payoffs - minimax_col)), p1_payoffs.shape
            )
            minimax_solution = {
                "player1_strategy": p1_strategies[minimax_idx[0]],
                "player2_strategy": p2_strategies[minimax_idx[1]],
                "value": float(p1_payoffs[minimax_idx]),
            }
        else:
            minimax_solution = None

        return {
            "nash_equilibria": nash_equilibria,
            "nash_count": len(nash_equilibria),
            "dominant_strategies": {
                "player1": dominant_p1,
                "player2": dominant_p2,
            },
            "minimax_solution": minimax_solution,
            "game_type": game_type,
        }


class SensitivityEngine:
    """7. Sensitivity Analysis — OAT variation, tornado, elasticity, breakeven"""

    @staticmethod
    def analyze(
        base_parameters: List[dict],
        base_outcome: float,
        variation_pct: float,
        outcome_func=None,
    ) -> dict:
        tornado = []
        elasticities = {}
        breakeven_points = {}

        for param in base_parameters:
            low_val = param["base_value"] * (1 - variation_pct / 100)
            high_val = param["base_value"] * (1 + variation_pct / 100)

            if outcome_func:
                outcome_low = outcome_func(param["name"], low_val)
                outcome_high = outcome_func(param["name"], high_val)
            else:
                impact = param.get("impact_on_outcome", 0.0)
                delta = high_val - low_val
                outcome_low = base_outcome - impact * delta / 2
                outcome_high = base_outcome + impact * delta / 2

            swing = abs(outcome_high - outcome_low)
            elasticity = (
                (outcome_high - outcome_low) / base_outcome / (variation_pct / 100)
                if base_outcome != 0
                else 0.0
            )

            if outcome_low * outcome_high < 0:
                breakeven = (
                    param["base_value"]
                    - base_outcome * (high_val - low_val) / (outcome_high - outcome_low)
                    if (outcome_high - outcome_low) != 0
                    else param["base_value"]
                )
            else:
                breakeven = None

            tornado.append(
                {
                    "variable": param["name"],
                    "base_value": param["base_value"],
                    "low_value": round(low_val, 6),
                    "high_value": round(high_val, 6),
                    "outcome_at_low": round(float(outcome_low), 6),
                    "outcome_at_high": round(float(outcome_high), 6),
                    "swing": round(float(swing), 6),
                }
            )

            elasticities[param["name"]] = round(float(elasticity), 6)
            if breakeven is not None:
                breakeven_points[param["name"]] = round(float(breakeven), 6)

        tornado.sort(key=lambda x: x["swing"], reverse=True)
        most_sensitive = tornado[0]["variable"] if tornado else None

        return {
            "tornado_data": tornado,
            "elasticities": elasticities,
            "breakeven_points": breakeven_points,
            "most_sensitive_variable": most_sensitive,
        }


class RiskRewardEngine:
    """8. Risk-Reward Analysis — Sharpe ratios, frontier, optimal allocation"""

    @staticmethod
    def analyze(
        options: List[dict],
        risk_free_rate: float,
    ) -> dict:
        n = len(options)
        returns = np.array([o["expected_return"] for o in options])
        stds = np.array([o["risk_std"] for o in options])
        names = [o["name"] for o in options]

        sharpe = (returns - risk_free_rate) / stds
        sharpe_ratios = {names[i]: round(float(sharpe[i]), 6) for i in range(n)}

        equal_weight = np.ones(n) / n
        port_return_eq = float(returns @ equal_weight)
        port_risk_eq = float(np.sqrt(equal_weight @ np.diag(stds**2) @ equal_weight))
        sharpe_eq = (
            (port_return_eq - risk_free_rate) / port_risk_eq if port_risk_eq > 0 else 0
        )

        best_sharpe_idx = int(np.argmax(sharpe))
        max_sharpe_weights = np.zeros(n)
        max_sharpe_weights[best_sharpe_idx] = 1.0
        port_return_ms = float(returns @ max_sharpe_weights)
        port_risk_ms = float(stds[best_sharpe_idx])

        min_var_idx = int(np.argmin(stds))
        min_var_weights = np.zeros(n)
        min_var_weights[min_var_idx] = 1.0

        frontier_points = []
        for w1 in np.linspace(0, 1, 11):
            w = np.array([w1, 1 - w1]) if n == 2 else np.full(n, 1.0 / n)
            if n == 2:
                w = np.array([w1, 1 - w1])
            pr = float(returns @ w)
            pv = float(w @ np.diag(stds**2) @ w)
            frontier_points.append(
                {
                    "weight": round(float(w1), 4),
                    "expected_return": round(pr, 6),
                    "risk": round(math.sqrt(pv), 6),
                    "sharpe": round((pr - risk_free_rate) / math.sqrt(pv), 6)
                    if pv > 0
                    else 0,
                }
            )

        return {
            "individual_sharpe_ratios": sharpe_ratios,
            "equal_weight_portfolio": {
                "expected_return": round(port_return_eq, 6),
                "risk": round(port_risk_eq, 6),
                "sharpe_ratio": round(float(sharpe_eq), 6),
            },
            "max_sharpe_portfolio": {
                "expected_return": round(port_return_ms, 6),
                "risk": round(port_risk_ms, 6),
                "dominant_asset": names[best_sharpe_idx],
            },
            "min_variance_portfolio": {
                "dominant_asset": names[min_var_idx],
                "risk": round(float(stds[min_var_idx]), 6),
            },
            "frontier": frontier_points,
        }


class DelphiEngine:
    """9. Delphi Method — consensus scoring"""

    @staticmethod
    def analyze_rounds(
        question: str,
        experts: List[str],
        rounds: List[dict],
    ) -> dict:
        all_rounds = []
        for rnd in rounds:
            scores = rnd["scores"]
            sorted_scores = sorted(scores)
            n = len(sorted_scores)
            median = float(np.median(scores))
            q1 = float(np.percentile(scores, 25))
            q3 = float(np.percentile(scores, 75))
            iqr = q3 - q1
            mean = float(np.mean(scores))
            std = float(np.std(scores))

            all_rounds.append(
                {
                    "round_number": rnd["round_number"],
                    "median": round(median, 4),
                    "mean": round(mean, 4),
                    "std": round(std, 4),
                    "q1": round(q1, 4),
                    "q3": round(q3, 4),
                    "iqr": round(iqr, 4),
                    "min": round(float(min(scores)), 4),
                    "max": round(float(max(scores)), 4),
                    "n_experts": n,
                }
            )

        convergence = False
        if len(all_rounds) >= 2:
            prev_iqr = all_rounds[-2]["iqr"]
            curr_iqr = all_rounds[-1]["iqr"]
            prev_median = all_rounds[-2]["median"]
            curr_median = all_rounds[-1]["median"]
            iqr_improved = curr_iqr <= prev_iqr * 1.1
            median_stable = abs(curr_median - prev_median) < max(prev_median * 0.1, 1.0)
            convergence = iqr_improved and median_stable

        last = all_rounds[-1] if all_rounds else {"median": 0, "iqr": 0, "mean": 0}
        consensus_score = (
            max(0.0, 1.0 - last["iqr"] / 10.0)
            if last.get("iqr", 10) is not None
            else 0.0
        )

        return {
            "question": question,
            "rounds": all_rounds,
            "final_median": last.get("median", 0),
            "final_iqr": last.get("iqr", 0),
            "consensus_score": round(float(consensus_score), 4),
            "convergence_reached": convergence,
            "interpretation": (
                "Strong consensus — experts converged"
                if convergence and last.get("iqr", 10) < 2
                else "Moderate consensus — some divergence remains"
                if convergence
                else "Consensus not yet reached — consider additional rounds"
            ),
        }


class StrategicChoiceEngine:
    """10. Strategic Choice — composite scoring framework"""

    @staticmethod
    def analyze(
        options: List[dict],
        criteria_weights: dict,
        risk_tolerance: str,
    ) -> dict:
        risk_multipliers = {"LOW": 0.7, "MODERATE": 1.0, "HIGH": 1.3}
        risk_mult = risk_multipliers.get(risk_tolerance, 1.0)

        total_weight = sum(criteria_weights.values()) if criteria_weights else 1.0
        normalized_weights = {k: v / total_weight for k, v in criteria_weights.items()}

        results = []
        for opt in options:
            criteria_score = sum(
                opt.get("criteria_scores", {}).get(c, 5.0) * w
                for c, w in normalized_weights.items()
            )
            risk_score = opt.get("risk_score", 5.0)
            risk_penalty = (10 - risk_score) / 10 * (1 - risk_mult)
            financial_attr = opt.get("financial_attractiveness", 5.0)
            impl_effort = opt.get("implementation_effort", 5.0)
            impl_factor = (10 - impl_effort) / 10

            composite = (
                criteria_score * (1 + risk_penalty) * financial_attr * impl_factor / 100
            )
            confidence = min(10.0, max(0.0, composite * 10))

            results.append(
                {
                    "name": opt["name"],
                    "criteria_score": round(float(criteria_score), 4),
                    "risk_score": risk_score,
                    "risk_penalty": round(float(risk_penalty), 4),
                    "financial_attractiveness": financial_attr,
                    "implementation_factor": round(float(impl_factor), 4),
                    "composite_score": round(float(composite), 6),
                    "confidence": round(float(confidence), 4),
                }
            )

        results.sort(key=lambda x: x["composite_score"], reverse=True)
        best = results[0] if results else None

        mitigation_plan = []
        if best and best["risk_score"] > 6:
            mitigation_plan = [
                "Conduct detailed risk assessment",
                "Develop contingency plans",
                "Phase implementation to limit exposure",
                "Establish monitoring triggers",
            ]
        elif best:
            mitigation_plan = [
                "Monitor key risk indicators",
                "Review quarterly",
            ]

        return {
            "recommendations": results,
            "recommended_strategy": best["name"] if best else None,
            "confidence_score": best["confidence"] if best else 0.0,
            "risk_tolerance": risk_tolerance,
            "risk_mitigation_plan": mitigation_plan,
        }
