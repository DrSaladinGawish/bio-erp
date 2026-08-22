"""
Risk & Uncertainty Management Services — 6 Techniques with Real Business Logic
BIO-ERP v5.3.0 — risk_uncertainty_organ
"""

import numpy as np
from scipy import stats


# =============================================================================
# 1. Value at Risk (VaR) Engine
# =============================================================================


class VaREngine:
    """Value at Risk — Parametric, Historical, and Monte Carlo methods."""

    @staticmethod
    def parametric_var(
        portfolio_value: float,
        expected_return: float,
        volatility: float,
        confidence_level: float = 0.95,
        time_horizon_days: int = 1,
    ) -> dict:
        z = stats.norm.ppf(1 - confidence_level)
        period_return = expected_return * time_horizon_days / 252
        period_vol = volatility * np.sqrt(time_horizon_days / 252)
        var_pct = -(z * period_vol - period_return)
        var_amount = portfolio_value * var_pct
        es_z = stats.norm.pdf(stats.norm.ppf(1 - confidence_level)) / (1 - confidence_level)
        cvar_pct = period_vol * es_z - period_return
        cvar_amount = portfolio_value * cvar_pct
        return {
            "method": "PARAMETRIC",
            "var_pct": round(var_pct * 100, 4),
            "var_amount": round(var_amount, 2),
            "cvar_pct": round(cvar_pct * 100, 4),
            "cvar_amount": round(cvar_amount, 2),
            "z_score": round(z, 4),
            "period_return": round(period_return * 100, 4),
            "period_volatility": round(period_vol * 100, 4),
        }

    @staticmethod
    def historical_var(
        portfolio_value: float,
        historical_returns: list,
        confidence_level: float = 0.95,
    ) -> dict:
        returns = np.array(historical_returns)
        alpha = 1 - confidence_level
        var_pct = -np.percentile(returns, alpha * 100)
        var_amount = portfolio_value * var_pct
        tail = returns[returns <= -var_pct]
        cvar_pct = -np.mean(tail) if len(tail) > 0 else var_pct
        cvar_amount = portfolio_value * cvar_pct
        skew = float(stats.skew(returns))
        kurt = float(stats.kurtosis(returns))
        shapiro_stat, shapiro_p = stats.shapiro(returns[:min(len(returns), 5000)])
        return {
            "method": "HISTORICAL",
            "var_pct": round(var_pct * 100, 4),
            "var_amount": round(var_amount, 2),
            "cvar_pct": round(cvar_pct * 100, 4),
            "cvar_amount": round(cvar_amount, 2),
            "data_points": len(returns),
            "mean_return": round(float(np.mean(returns)) * 100, 4),
            "std_return": round(float(np.std(returns)) * 100, 4),
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "min_return": round(float(np.min(returns)) * 100, 4),
            "max_return": round(float(np.max(returns)) * 100, 4),
        }

    @staticmethod
    def monte_carlo_var(
        portfolio_value: float,
        positions: list,
        confidence_level: float = 0.95,
        n_simulations: int = 10000,
        time_horizon_days: int = 1,
        seed: int = 42,
    ) -> dict:
        rng = np.random.default_rng(seed)
        n_assets = len(positions)
        weights = np.array([p["weight"] for p in positions])
        returns_arr = np.array([p["expected_return"] for p in positions])
        vols_arr = np.array([p["volatility"] for p in positions])
        corr_matrix = np.eye(n_assets)
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                rho = positions[i].get("correlation", 0.3)
                corr_matrix[i, j] = rho
                corr_matrix[j, i] = rho
        cov_matrix = np.outer(vols_arr, vols_arr) * corr_matrix
        L = np.linalg.cholesky(cov_matrix)
        z = rng.standard_normal((n_simulations, n_assets))
        simulated_returns = returns_arr * time_horizon_days / 252 + (z @ L.T) * np.sqrt(time_horizon_days / 252)
        portfolio_returns = simulated_returns @ weights
        var_pct = -np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        var_amount = portfolio_value * var_pct
        tail = portfolio_returns[portfolio_returns <= -var_pct]
        cvar_pct = -np.mean(tail) if len(tail) > 0 else var_pct
        cvar_amount = portfolio_value * cvar_pct
        hist_counts, bin_edges = np.histogram(portfolio_returns, bins=50)
        hist_data = {
            "counts": hist_counts.tolist(),
            "bin_edges": bin_edges.tolist(),
        }
        percentiles = {
            "P1": round(float(np.percentile(portfolio_returns, 1)) * 100, 4),
            "P5": round(float(np.percentile(portfolio_returns, 5)) * 100, 4),
            "P10": round(float(np.percentile(portfolio_returns, 10)) * 100, 4),
            "P25": round(float(np.percentile(portfolio_returns, 25)) * 100, 4),
            "P50": round(float(np.percentile(portfolio_returns, 50)) * 100, 4),
            "P75": round(float(np.percentile(portfolio_returns, 75)) * 100, 4),
            "P90": round(float(np.percentile(portfolio_returns, 90)) * 100, 4),
            "P95": round(float(np.percentile(portfolio_returns, 95)) * 100, 4),
            "P99": round(float(np.percentile(portfolio_returns, 99)) * 100, 4),
        }
        return {
            "method": "MONTE_CARLO",
            "var_pct": round(var_pct * 100, 4),
            "var_amount": round(var_amount, 2),
            "cvar_pct": round(cvar_pct * 100, 4),
            "cvar_amount": round(cvar_amount, 2),
            "n_simulations": n_simulations,
            "mean_return": round(float(np.mean(portfolio_returns)) * 100, 4),
            "std_return": round(float(np.std(portfolio_returns)) * 100, 4),
            "percentiles": percentiles,
            "distribution_histogram": hist_data,
            "probability_of_loss": round(
                float(np.mean(portfolio_returns < 0)) * 100, 2
            ),
        }

    @staticmethod
    def calculate(
        portfolio_value: float,
        positions: list,
        method: str,
        confidence_level: float = 0.95,
        time_horizon_days: int = 1,
        n_simulations: int = 10000,
        historical_returns: list | None = None,
        seed: int = 42,
    ) -> dict:
        pos_weights = [p["weight"] for p in positions]
        weight_sum = sum(pos_weights)
        if abs(weight_sum - 1.0) > 0.01:
            norm_positions = []
            for p in positions:
                norm_p = dict(p)
                norm_p["weight"] = p["weight"] / weight_sum
                norm_positions.append(norm_p)
        else:
            norm_positions = positions

        wavg_return = sum(
            p["weight"] * p["expected_return"] for p in norm_positions
        )
        wavg_vol = sum(
            p["weight"] * p["volatility"] for p in norm_positions
        )

        if method == "HISTORICAL" and historical_returns:
            return VaREngine.historical_var(
                portfolio_value, historical_returns, confidence_level
            )
        elif method == "MONTE_CARLO":
            return VaREngine.monte_carlo_var(
                portfolio_value, norm_positions, confidence_level,
                n_simulations, time_horizon_days, seed,
            )
        else:
            return VaREngine.parametric_var(
                portfolio_value, wavg_return, wavg_vol,
                confidence_level, time_horizon_days,
            )


# =============================================================================
# 2. Monte Carlo Simulation Engine
# =============================================================================


class MonteCarloEngine:
    """Probabilistic scenario generation with multiple distributions."""

    @staticmethod
    def generate_variable_samples(
        var: dict, n: int, rng: np.random.Generator
    ) -> np.ndarray:
        dist = var["distribution"]
        mean = var.get("mean", 0.0)
        std = var.get("std", 1.0)
        low = var.get("min_val")
        high = var.get("max_val")
        mode = var.get("mode")

        if dist == "normal":
            return rng.normal(mean, std, size=n)
        elif dist == "uniform":
            if low is None or high is None:
                low = mean - 2 * std
                high = mean + 2 * std
            return rng.uniform(low, high, size=n)
        elif dist == "triangular":
            if low is None or high is None:
                low = mean - 2 * std
                high = mean + 2 * std
            if mode is None:
                mode = mean
            return rng.triangular(low, mode, high, size=n)
        elif dist == "lognormal":
            normal_mean = np.log(mean**2 / np.sqrt(std**2 + mean**2))
            normal_std = np.sqrt(np.log(1 + (std / mean) ** 2))
            return rng.lognormal(normal_mean, normal_std, size=n)
        else:
            return rng.normal(mean, std, size=n)

    @staticmethod
    def run_simulation(
        variables: list,
        n_simulations: int = 10000,
        seed: int | None = None,
    ) -> dict:
        rng = np.random.default_rng(seed)
        samples = {}
        for var in variables:
            samples[var["name"]] = MonteCarloEngine.generate_variable_samples(
                var, n_simulations, rng
            )
        combined = np.column_stack([samples[v["name"]] for v in variables])
        var_names = [v["name"] for v in variables]
        sum_result = np.sum(combined, axis=1)
        result = sum_result
        mean_val = float(np.mean(result))
        std_val = float(np.std(result))
        percentiles = {
            "P5": round(float(np.percentile(result, 5)), 4),
            "P25": round(float(np.percentile(result, 25)), 4),
            "P50": round(float(np.percentile(result, 50)), 4),
            "P75": round(float(np.percentile(result, 75)), 4),
            "P95": round(float(np.percentile(result, 95)), 4),
        }
        skewness = round(float(stats.skew(result)), 4)
        kurtosis = round(float(stats.kurtosis(result)), 4)
        prob_loss = round(float(np.mean(result < 0)) * 100, 2)
        var_95 = round(float(np.percentile(result, 5)) * -1, 4)
        cvar_95_arr = result[result <= np.percentile(result, 5)]
        cvar_95 = round(float(-np.mean(cvar_95_arr)), 4) if len(cvar_95_arr) > 0 else var_95
        hist_counts, bin_edges = np.histogram(result, bins=50)
        return {
            "n_simulations": n_simulations,
            "variables_simulated": var_names,
            "mean": round(mean_val, 4),
            "std": round(std_val, 4),
            "min": round(float(np.min(result)), 4),
            "max": round(float(np.max(result)), 4),
            "percentiles": percentiles,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "probability_of_loss_pct": prob_loss,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "confidence_interval_95": [
                round(float(np.percentile(result, 2.5)), 4),
                round(float(np.percentile(result, 97.5)), 4),
            ],
            "distribution_histogram": {
                "counts": hist_counts.tolist(),
                "bin_edges": bin_edges.tolist(),
            },
        }


# =============================================================================
# 3. Black Swan Detection Engine
# =============================================================================


class BlackSwanEngine:
    """Extreme event identification using statistical methods."""

    @staticmethod
    def detect_events(
        time_series: list,
        sigma_threshold: float = 3.0,
    ) -> dict:
        data = np.array(time_series)
        n = len(data)
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1)) if n > 1 else 0.0
        if std == 0:
            return {
                "events": [],
                "total_events": 0,
                "kurtosis": 0.0,
                "skewness": 0.0,
                "tail_risk_score": 0.0,
                "mean": mean,
                "std": std,
                "data_points": n,
                "threshold_sigma": sigma_threshold,
            }
        z_scores = (data - mean) / std
        skewness = round(float(stats.skew(data)), 4)
        kurtosis_raw = float(stats.kurtosis(data))
        excess_kurtosis = round(kurtosis_raw, 4)
        events = []
        for i, z in enumerate(z_scores):
            if abs(z) > sigma_threshold:
                event = {
                    "index": i,
                    "value": round(float(data[i]), 4),
                    "z_score": round(float(z), 4),
                    "deviation_sigma": round(abs(float(z)), 4),
                    "direction": "EXTREME_HIGH" if z > 0 else "EXTREME_LOW",
                    "severity": (
                        "CATASTROPHIC" if abs(z) > 5
                        else "SEVERE" if abs(z) > 4
                        else "SIGNIFICANT"
                    ),
                }
                events.append(event)
        n_tail = max(1, int(n * 0.05))
        sorted_abs_z = np.sort(np.abs(z_scores))[::-1]
        top5_mean = float(np.mean(sorted_abs_z[:n_tail]))
        tail_risk_score = round(min(10.0, top5_mean / sigma_threshold * 5), 4)
        normality_stat, normality_p = stats.shapiro(data[:min(n, 5000)])
        jarque_bera_stat, jarque_bera_p = stats.jarque_bera(data)
        return {
            "data_points": n,
            "mean": round(mean, 4),
            "std": round(std, 4),
            "threshold_sigma": sigma_threshold,
            "events": events,
            "total_events": len(events),
            "skewness": skewness,
            "kurtosis": excess_kurtosis,
            "tail_risk_score": tail_risk_score,
            "normality_test": {
                "shapiro_statistic": round(float(normality_stat), 4),
                "shapiro_p_value": round(float(normality_p), 4),
                "jarque_bera_statistic": round(float(jarque_bera_stat), 4),
                "jarque_bera_p_value": round(float(jarque_bera_p), 4),
                "is_normal_at_5pct": float(normality_p) > 0.05,
            },
            "max_z_score": round(float(np.max(np.abs(z_scores))), 4),
            "percentage_beyond_threshold": round(
                len(events) / n * 100, 2
            ),
        }


# =============================================================================
# 4. Sensitivity Analysis Engine
# =============================================================================


class SensitivityEngine:
    """One-at-a-time sensitivity analysis with tornado chart data."""

    @staticmethod
    def analyze(
        variables: list,
        base_case_output: float,
    ) -> dict:
        results = []
        for var in variables:
            low_val = var["base_value"] * (1 + var["low_delta_pct"] / 100)
            high_val = var["base_value"] * (1 + var["high_delta_pct"] / 100)
            scale_factor_low = low_val / var["base_value"] if var["base_value"] != 0 else 1
            scale_factor_high = high_val / var["base_value"] if var["base_value"] != 0 else 1
            low_output = base_case_output * scale_factor_low
            high_output = base_case_output * scale_factor_high
            swing = high_output - low_output
            elasticity = (swing / base_case_output) / (
                (high_val - low_val) / var["base_value"]
            ) if var["base_value"] != 0 and (high_val - low_val) != 0 else 0
            results.append({
                "variable_name": var["name"],
                "base_value": var["base_value"],
                "low_value": round(low_val, 4),
                "high_value": round(high_val, 4),
                "low_delta_pct": var["low_delta_pct"],
                "high_delta_pct": var["high_delta_pct"],
                "output_at_low": round(low_output, 4),
                "output_at_high": round(high_output, 4),
                "swing": round(swing, 4),
                "normalized_impact": round(abs(swing) / base_case_output * 100, 4) if base_case_output != 0 else 0,
                "elasticity": round(elasticity, 4),
            })
        results.sort(key=lambda x: abs(x["swing"]), reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1
        tornado_data = {
            "labels": [r["variable_name"] for r in results],
            "low_values": [r["output_at_low"] for r in results],
            "high_values": [r["output_at_high"] for r in results],
            "base_case": base_case_output,
        }
        max_swing = max(abs(r["swing"]) for r in results) if results else 1
        for r in results:
            r["tornado_bar_width"] = round(abs(r["swing"]) / max_swing * 100, 2) if max_swing > 0 else 0
        return {
            "base_case_output": base_case_output,
            "variables_analyzed": len(results),
            "results": results,
            "tornado_chart": tornado_data,
            "most_sensitive_variable": results[0]["variable_name"] if results else None,
            "least_sensitive_variable": results[-1]["variable_name"] if results else None,
            "total_swing_range": round(
                max(r["output_at_high"] for r in results) - min(r["output_at_low"] for r in results), 4
            ) if results else 0,
        }


# =============================================================================
# 5. Decision Tree Engine
# =============================================================================


class DecisionTreeEngine:
    """Sequential decision analysis using backward induction."""

    @staticmethod
    def build_tree(nodes: list) -> dict:
        node_map = {n["node_id"]: dict(n) for n in nodes}
        for nid, node in node_map.items():
            node["children"] = []
        for nid, node in node_map.items():
            pid = node.get("parent_id")
            if pid and pid in node_map:
                node_map[pid]["children"].append(nid)
        return node_map

    @staticmethod
    def backward_induction(node_map: dict, risk_aversion: float = 0.0) -> dict:
        terminal_values = {}
        for nid, node in node_map.items():
            if node["node_type"] == "terminal":
                payoff = node.get("payoff", 0) or 0
                cost = node.get("cost", 0) or 0
                terminal_values[nid] = payoff - cost

        def evaluate(nid: str) -> float:
            node = node_map[nid]
            if node["node_type"] == "terminal":
                return terminal_values.get(nid, 0)
            child_values = [evaluate(cid) for cid in node["children"]]
            if node["node_type"] == "chance":
                child_probs = [node_map[cid].get("probability") for cid in node["children"]]
                if all(p is not None for p in child_probs):
                    probs = [p or 0 for p in child_probs]
                else:
                    node_prob = node.get("probability")
                    if node_prob is not None and len(node["children"]) == 2:
                        probs = [node_prob, 1 - node_prob]
                    else:
                        n_children = len(node["children"])
                        probs = [1.0 / n_children] * n_children if n_children > 0 else []
                ev = sum(p * v for p, v in zip(probs, child_values))
                if risk_aversion > 0:
                    variance = sum(p * (v - ev) ** 2 for p, v in zip(probs, child_values))
                    ev = ev - risk_aversion * variance
                node["emv"] = round(ev, 4)
                return ev
            elif node["node_type"] == "decision":
                node["emv"] = round(max(child_values), 4)
                return max(child_values)
            return 0

        root_id = None
        for nid, node in node_map.items():
            if node.get("parent_id") is None:
                root_id = nid
                break

        if root_id:
            optimal_emv = evaluate(root_id)
        else:
            optimal_emv = 0

        def find_optimal_path(nid: str) -> list:
            node = node_map[nid]
            if node["node_type"] == "terminal":
                return [{"node_id": nid, "label": node.get("label", ""), "value": terminal_values.get(nid, 0)}]
            child_values = {cid: evaluate(cid) for cid in node["children"]}
            if node["node_type"] == "chance":
                best_child = max(child_values, key=child_values.get)
                return [{"node_id": nid, "label": node.get("label", ""), "emv": node.get("emv", 0)}] + find_optimal_path(best_child)
            elif node["node_type"] == "decision":
                best_child = max(child_values, key=child_values.get)
                return [{"node_id": nid, "label": node.get("label", ""), "choice": node_map[best_child].get("label", ""), "emv": node.get("emv", 0)}] + find_optimal_path(best_child)
            return []

        optimal_path = find_optimal_path(root_id) if root_id else []

        risk_profiles = {}
        for nid, node in node_map.items():
            if node["node_type"] == "chance" and node["children"]:
                child_vals = [terminal_values.get(cid, 0) for cid in node["children"]]
                child_probs_raw = [node_map[cid].get("probability") for cid in node["children"]]
                if all(p is not None for p in child_probs_raw):
                    probs = [p or 0 for p in child_probs_raw]
                else:
                    node_prob = node.get("probability")
                    if node_prob is not None and len(node["children"]) == 2:
                        probs = [node_prob, 1 - node_prob]
                    else:
                        n_ch = len(node["children"])
                        probs = [1.0 / n_ch] * n_ch
                if child_vals:
                    risk_profiles[nid] = {
                        "label": node.get("label", ""),
                        "emv": node.get("emv", 0),
                        "min_outcome": round(min(child_vals), 4),
                        "max_outcome": round(max(child_vals), 4),
                        "range": round(max(child_vals) - min(child_vals), 4),
                        "probabilities": probs,
                        "outcomes": [round(v, 4) for v in child_vals],
                    }

        enriched_nodes = []
        for nid, node in node_map.items():
            enriched_nodes.append({
                "node_id": nid,
                "node_type": node["node_type"],
                "label": node.get("label", ""),
                "emv": node.get("emv", None),
                "payoff": node.get("payoff", None),
                "cost": node.get("cost", None),
                "probability": node.get("probability", None),
                "children": node["children"],
            })

        return {
            "nodes": enriched_nodes,
            "optimal_emv": round(optimal_emv, 4),
            "optimal_path": optimal_path,
            "risk_profiles": risk_profiles,
        }


# =============================================================================
# 6. Scenario Analysis Engine
# =============================================================================


class ScenarioAnalysisEngine:
    """Multi-scenario comparison with probability-weighted outcomes."""

    @staticmethod
    def analyze(
        scenarios: list,
        risk_free_rate_pct: float = 0.0,
    ) -> dict:
        total_prob = sum(s["probability"] for s in scenarios)
        outcomes = [s["output_value"] for s in scenarios]
        probs = [s["probability"] for s in scenarios]

        weighted_ev = sum(p * o for p, o in zip(probs, outcomes))
        variance = sum(p * (o - weighted_ev) ** 2 for p, o in zip(probs, outcomes))
        std_dev = np.sqrt(variance)
        sorted_scenarios = sorted(scenarios, key=lambda s: s["output_value"], reverse=True)
        best = sorted_scenarios[0]
        worst = sorted_scenarios[-1]
        downside_scenarios = [s for s in scenarios if s["output_value"] < weighted_ev]
        upside_scenarios = [s for s in scenarios if s["output_value"] > weighted_ev]
        downside_dev = 0
        if downside_scenarios:
            downside_dev = np.sqrt(
                sum(s["probability"] * (s["output_value"] - weighted_ev) ** 2
                    for s in downside_scenarios)
            )
        upside_dev = 0
        if upside_scenarios:
            upside_dev = np.sqrt(
                sum(s["probability"] * (s["output_value"] - weighted_ev) ** 2
                    for s in upside_scenarios)
            )
        sharpe_ratio = (
            (weighted_ev - risk_free_rate_pct) / std_dev
            if std_dev > 0 else 0
        )
        sortino_denom = downside_dev if downside_dev > 0 else 1
        sortino_ratio = (weighted_ev - risk_free_rate_pct) / sortino_denom
        ranked = []
        for i, s in enumerate(sorted_scenarios):
            ranked.append({
                "rank": i + 1,
                "name": s["name"],
                "probability": s["probability"],
                "output_value": s["output_value"],
                "deviation_from_ev": round(s["output_value"] - weighted_ev, 4),
                "variables": s.get("variables"),
            })
        prob_loss = sum(
            s["probability"] for s in scenarios if s["output_value"] < 0
        )
        return {
            "n_scenarios": len(scenarios),
            "probability_sum": round(total_prob, 4),
            "weighted_expected_value": round(weighted_ev, 4),
            "std_deviation": round(float(std_dev), 4),
            "variance": round(float(variance), 4),
            "best_case": {
                "name": best["name"],
                "value": best["output_value"],
                "probability": best["probability"],
            },
            "worst_case": {
                "name": worst["name"],
                "value": worst["output_value"],
                "probability": worst["probability"],
            },
            "upside_asymmetry": round(upside_dev, 4),
            "downside_asymmetry": round(downside_dev, 4),
            "asymmetry_ratio": round(
                upside_dev / downside_dev, 4
            ) if downside_dev > 0 else float("inf"),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "sortino_ratio": round(sortino_ratio, 4),
            "probability_of_loss_pct": round(prob_loss * 100, 2),
            "scenario_rankings": ranked,
        }
