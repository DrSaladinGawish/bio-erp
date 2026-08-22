"""
Environmental Scanning Organ — Business Logic Engines
BIO-ERP v5.3.0 — env_scanning_organ

10 stateless engines with real analysis logic.
"""

import math
from typing import List, Optional


class PESTELEngine:
    """1. PESTEL Analysis — weighted category scoring with radar chart data."""

    CATEGORY_WEIGHTS = {
        "political": 0.15,
        "economic": 0.20,
        "social": 0.15,
        "technological": 0.20,
        "environmental": 0.15,
        "legal": 0.15,
    }

    @staticmethod
    def score_category(factors: list) -> dict:
        if not factors:
            return {"raw_score": 0.0, "weighted_score": 0.0, "count": 0, "factors": []}
        scored = []
        total = 0.0
        for f in factors:
            ws = round(f["impact_score"] * f["probability"], 4)
            total += ws
            scored.append({**f, "weighted_score": ws})
        avg = total / len(factors)
        return {
            "raw_score": round(total, 4),
            "weighted_score": round(avg, 4),
            "count": len(factors),
            "factors": scored,
        }

    @staticmethod
    def analyze(categories: dict) -> dict:
        category_results = {}
        overall_weighted = 0.0
        all_factors = []
        for cat, factors in categories.items():
            result = PESTELEngine.score_category(factors)
            category_results[cat] = result
            w = PESTELEngine.CATEGORY_WEIGHTS.get(cat.lower(), 0.15)
            overall_weighted += result["weighted_score"] * w
            for f in factors:
                all_factors.append({**f, "category": cat})

        sorted_by_impact = sorted(all_factors, key=lambda x: x["impact_score"], reverse=True)
        opportunities = [
            f for f in sorted_by_impact if f["impact_score"] >= 7
        ][:3]
        threats = [
            f for f in sorted_by_impact if f["impact_score"] >= 6 and f["probability"] >= 0.5
        ][:3]

        radar = {cat: category_results[cat]["weighted_score"] for cat in categories}

        if overall_weighted >= 7:
            interpretation = "High-impact macro environment — significant opportunities and threats present."
        elif overall_weighted >= 4:
            interpretation = "Moderate macro environment — selective factors warrant close monitoring."
        else:
            interpretation = "Low macro impact — relatively stable external environment."

        return {
            "category_scores": category_results,
            "overall_pestel_score": round(overall_weighted, 4),
            "total_factors": len(all_factors),
            "top_opportunities": opportunities,
            "top_threats": threats,
            "radar_chart_data": radar,
            "interpretation": interpretation,
        }


class SWOTEngine:
    """2. SWOT Analysis — TOWS matrix and strategic position scoring."""

    @staticmethod
    def _quadrant_score(items: list) -> float:
        if not items:
            return 0.0
        return sum(i["impact_score"] for i in items) / len(items)

    @staticmethod
    def _tows_strategies(strengths: list, weaknesses: list, opportunities: list, threats: list) -> dict:
        s_names = [s["item_name"] for s in strengths[:3]]
        w_names = [w["item_name"] for w in weaknesses[:3]]
        o_names = [o["item_name"] for o in opportunities[:3]]
        t_names = [t["item_name"] for t in threats[:3]]

        so = [f"Leverage {s} to capture {o}" for s in s_names for o in o_names][:5]
        wo = [f"Improve {w} to exploit {o}" for w in w_names for o in o_names][:5]
        st = [f"Use {s} to mitigate {t}" for s in s_names for t in t_names][:5]
        wt = [f"Address {w} to avoid {t}" for w in w_names for t in t_names][:5]

        return {"SO": so, "WO": wo, "ST": st, "WT": wt}

    @staticmethod
    def _priority_matrix(items: list) -> list:
        scored = []
        for item in items:
            priority = item["impact_score"] * item["urgency"]
            scored.append({
                "item_name": item["item_name"],
                "impact_score": item["impact_score"],
                "urgency": item["urgency"],
                "priority_score": round(priority, 2),
            })
        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        for i, s in enumerate(scored):
            s["rank"] = i + 1
        return scored

    @staticmethod
    def analyze(strengths: list, weaknesses: list, opportunities: list, threats: list) -> dict:
        s_score = SWOTEngine._quadrant_score(strengths)
        w_score = SWOTEngine._quadrant_score(weaknesses)
        o_score = SWOTEngine._quadrant_score(opportunities)
        t_score = SWOTEngine._quadrant_score(threats)

        internal = s_score - w_score
        external = o_score - t_score
        overall = internal + external

        if internal > 0 and external > 0:
            position = "AGGRESSIVE"
            desc = "Strong internal position with favorable external environment — pursue growth."
        elif internal > 0 and external <= 0:
            position = "COMPETITIVE"
            desc = "Strong internally but facing external threats — use strengths to defend."
        elif internal <= 0 and external > 0:
            position = "TURNAROUND"
            desc = "External opportunities exist but internal weaknesses limit capture — improve capabilities."
        else:
            position = "DEFENSIVE"
            desc = "Both internal weaknesses and external threats — minimize risk and restructure."

        return {
            "quadrant_scores": {
                "strengths": round(s_score, 4),
                "weaknesses": round(w_score, 4),
                "opportunities": round(o_score, 4),
                "threats": round(t_score, 4),
            },
            "internal_balance": round(internal, 4),
            "external_balance": round(external, 4),
            "overall_score": round(overall, 4),
            "strategic_position": position,
            "position_description": desc,
            "tows_matrix": SWOTEngine._tows_strategies(strengths, weaknesses, opportunities, threats),
            "priority_matrix": {
                "strengths": SWOTEngine._priority_matrix(strengths),
                "weaknesses": SWOTEngine._priority_matrix(weaknesses),
                "opportunities": SWOTEngine._priority_matrix(opportunities),
                "threats": SWOTEngine._priority_matrix(threats),
            },
        }


class ScenarioPlanningEngine:
    """3. Scenario Planning — 2x2 uncertainty matrix with probability-weighted impact."""

    @staticmethod
    def analyze(
        uncertainty_x: str,
        uncertainty_y: str,
        scenarios: list,
        planning_horizon: int,
    ) -> dict:
        total_prob = sum(s.get("probability", 0.25) for s in scenarios)
        expected_impact = sum(
            s.get("probability", 0.25) * s.get("impact_score", 5.0) for s in scenarios
        )

        best = max(scenarios, key=lambda s: s.get("impact_score", 0)) if scenarios else None
        worst = min(scenarios, key=lambda s: s.get("impact_score", 0)) if scenarios else None
        most_likely = max(scenarios, key=lambda s: s.get("probability", 0)) if scenarios else None

        variance = 0.0
        if len(scenarios) > 1:
            mean = expected_impact
            variance = sum(
                s.get("probability", 0.25) * (s.get("impact_score", 5.0) - mean) ** 2
                for s in scenarios
            )
        std_dev = math.sqrt(variance)

        narratives = []
        for s in scenarios:
            narratives.append({
                "name": s.get("name", "Unnamed"),
                "probability": s.get("probability", 0.25),
                "impact_score": s.get("impact_score", 5.0),
                "description": s.get("description", ""),
                "strategic_implications": s.get("strategic_implications", []),
                "variables": s.get("variables", {}),
            })

        return {
            "uncertainties": {"x": uncertainty_x, "y": uncertainty_y},
            "planning_horizon_years": planning_horizon,
            "scenarios_count": len(scenarios),
            "total_probability": round(total_prob, 4),
            "expected_impact_score": round(expected_impact, 4),
            "impact_std_dev": round(std_dev, 4),
            "best_case": best["name"] if best else None,
            "worst_case": worst["name"] if worst else None,
            "most_likely": most_likely["name"] if most_likely else None,
            "scenario_narratives": narratives,
            "risk_assessment": (
                "HIGH" if std_dev > 2.5 else "MODERATE" if std_dev > 1.0 else "LOW"
            ),
        }


class CompetitorIntelligenceEngine:
    """4. Competitor Intelligence — multi-dimensional competitive positioning."""

    DIMENSION_WEIGHTS = {
        "price": 0.25,
        "quality": 0.25,
        "innovation": 0.25,
        "market_presence": 0.25,
    }

    @staticmethod
    def _composite_score(comp: dict) -> float:
        return (
            comp.get("price_score", 5) * 0.25
            + comp.get("quality_score", 5) * 0.25
            + comp.get("innovation_score", 5) * 0.25
            + comp.get("market_presence_score", 5) * 0.25
        )

    @staticmethod
    def analyze(our_scores: dict, competitors: list) -> dict:
        our_composite = CompetitorIntelligenceEngine._composite_score(our_scores)
        comp_results = []
        for c in competitors:
            cs = CompetitorIntelligenceEngine._composite_score(c)
            diff = cs - our_composite
            market_share = c.get("market_share", 0)
            threat = (
                "CRITICAL" if diff > 1.5 and market_share > 15
                else "HIGH" if diff > 1.0 or market_share > 20
                else "MEDIUM" if diff > 0.5
                else "LOW"
            )
            comp_results.append({
                "name": c["name"],
                "market_share": market_share,
                "composite_score": round(cs, 4),
                "gap_to_us": round(diff, 4),
                "threat_level": threat,
                "strengths": c.get("strengths", []),
                "weaknesses": c.get("weaknesses", []),
                "recent_moves": c.get("recent_moves", []),
                "dimension_scores": {
                    "price": c.get("price_score", 5),
                    "quality": c.get("quality_score", 5),
                    "innovation": c.get("innovation_score", 5),
                    "market_presence": c.get("market_presence_score", 5),
                },
            })
        comp_results.sort(key=lambda x: x["composite_score"], reverse=True)

        our_dimension_gaps = {}
        if comp_results:
            n = len(comp_results)
            avg_price = sum(r["dimension_scores"]["price"] for r in comp_results) / n
            avg_quality = sum(r["dimension_scores"]["quality"] for r in comp_results) / n
            avg_innovation = sum(r["dimension_scores"]["innovation"] for r in comp_results) / n
            avg_presence = sum(r["dimension_scores"]["market_presence"] for r in comp_results) / n
            our_dimension_gaps = {
                "price": round(our_scores.get("price_score", 5) - avg_price, 2),
                "quality": round(our_scores.get("quality_score", 5) - avg_quality, 2),
                "innovation": round(our_scores.get("innovation_score", 5) - avg_innovation, 2),
                "market_presence": round(our_scores.get("our_market_presence_score", 5) - avg_presence, 2),
            }

        high_threats = [r for r in comp_results if r["threat_level"] in ("HIGH", "CRITICAL")]
        positioning_map = [
            {"name": r["name"], "x": r["dimension_scores"]["quality"],
             "y": r["dimension_scores"]["innovation"], "size": r["market_share"]}
            for r in comp_results
        ]

        return {
            "our_composite_score": round(our_composite, 4),
            "competitor_rankings": comp_results,
            "competitive_positioning_map": positioning_map,
            "high_threat_competitors": len(high_threats),
            "our_dimension_gaps": our_dimension_gaps,
            "market_concentration": round(
                sum(c.get("market_share", 0) for c in competitors), 2
            ),
        }


class CustomerAnalysisEngine:
    """5. Customer Analysis — segment attractiveness and CLV estimation."""

    @staticmethod
    def _segment_attractiveness(seg: dict) -> float:
        size_score = min(seg.get("size", 0) / 1000, 10.0)
        growth = max(min(seg.get("growth_rate", 0) / 5, 10.0), 0.0)
        satisfaction = seg.get("satisfaction_score", 5.0)
        wtp = seg.get("willingness_to_pay", 5.0)
        return round(size_score * 0.25 + growth * 0.25 + satisfaction * 0.25 + wtp * 0.25, 4)

    @staticmethod
    def estimate_clv(avg_revenue: float, retention_rate: float, discount_rate_pct: float) -> float:
        r = retention_rate / 100
        d = discount_rate_pct / 100
        if d >= r:
            return round(avg_revenue / (1 + d - r), 4) if (1 + d - r) > 0 else 0.0
        return round(avg_revenue / (1 - r + d), 4)

    @staticmethod
    def analyze(segments: list, discount_rate_pct: float = 10.0) -> dict:
        results = []
        for seg in segments:
            attract = CustomerAnalysisEngine._segment_attractiveness(seg)
            clv = CustomerAnalysisEngine.estimate_clv(
                seg.get("average_revenue", 0),
                seg.get("retention_rate", 80.0),
                discount_rate_pct,
            )
            retention = seg.get("retention_rate", 80.0)
            churn_risk = (
                "HIGH" if retention < 60
                else "MEDIUM" if retention < 80
                else "LOW"
            )
            results.append({
                "segment_name": seg["name"],
                "size": seg.get("size", 0),
                "growth_rate": seg.get("growth_rate", 0),
                "satisfaction_score": seg.get("satisfaction_score", 5),
                "willingness_to_pay": seg.get("willingness_to_pay", 5),
                "attractiveness_score": attract,
                "estimated_clv": clv,
                "churn_risk": churn_risk,
                "priority": (
                    "HIGH" if attract >= 7
                    else "MEDIUM" if attract >= 4
                    else "LOW"
                ),
            })
        results.sort(key=lambda x: x["attractiveness_score"], reverse=True)

        total_size = sum(r["size"] for r in results)
        weighted_growth = (
            sum(r["growth_rate"] * r["size"] for r in results) / total_size
            if total_size > 0 else 0
        )
        high_priority = [r for r in results if r["priority"] == "HIGH"]

        return {
            "segment_rankings": results,
            "total_market_size": total_size,
            "weighted_avg_growth_pct": round(weighted_growth, 4),
            "high_priority_count": len(high_priority),
            "best_segment": results[0]["segment_name"] if results else None,
            "total_estimated_clv": round(sum(r["estimated_clv"] for r in results), 4),
        }


class TrendAnalysisEngine:
    """6. Trend Analysis — linear regression, moving average, and forecasting."""

    @staticmethod
    def _linear_regression(values: list) -> tuple:
        n = len(values)
        if n < 2:
            return 0.0, values[0] if values else 0.0, 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        ss_xy = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        ss_xx = sum((i - x_mean) ** 2 for i in range(n))
        slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
        intercept = y_mean - slope * x_mean

        ss_res = sum((values[i] - (slope * i + intercept)) ** 2 for i in range(n))
        ss_tot = sum((v - y_mean) ** 2 for v in values)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return round(slope, 6), round(intercept, 6), round(max(r_squared, 0.0), 6)

    @staticmethod
    def _moving_average(values: list, window: int = 3) -> list:
        if len(values) < window:
            return values[:]
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            result.append(round(sum(values[start:i + 1]) / (i - start + 1), 4))
        return result

    @staticmethod
    def _find_inflection_points(values: list) -> list:
        inflections = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i - 1] and values[i] > values[i + 1]:
                inflections.append({"index": i, "type": "LOCAL_MAX", "value": values[i]})
            elif values[i] < values[i - 1] and values[i] < values[i + 1]:
                inflections.append({"index": i, "type": "LOCAL_MIN", "value": values[i]})
        return inflections

    @staticmethod
    def analyze(data_points: list, forecast_periods: int = 3) -> dict:
        if not data_points:
            return {"error": "No data points provided"}

        values = [dp["value"] for dp in data_points]
        metric_name = data_points[0].get("metric_name", "unknown")

        slope, intercept, r_squared = TrendAnalysisEngine._linear_regression(values)
        smoothed = TrendAnalysisEngine._moving_average(values)
        inflections = TrendAnalysisEngine._find_inflection_points(values)

        n = len(values)
        forecasts = []
        for i in range(1, forecast_periods + 1):
            predicted = round(slope * (n + i - 1) + intercept, 4)
            forecasts.append({
                "period": f"forecast_{i}",
                "predicted_value": predicted,
            })

        direction = (
            "GROWTH" if slope > 0.01
            else "DECLINE" if slope < -0.01
            else "STABLE"
        )

        volatility = 0.0
        if len(values) > 1:
            mean_v = sum(values) / len(values)
            variance = sum((v - mean_v) ** 2 for v in values) / len(values)
            volatility = math.sqrt(variance)

        change_pct = (
            ((values[-1] - values[0]) / values[0] * 100)
            if values[0] != 0 else 0.0
        )

        return {
            "metric_name": metric_name,
            "data_points_count": n,
            "trend_direction": direction,
            "slope": slope,
            "r_squared": r_squared,
            "trend_interpretation": (
                "Strong upward trend" if slope > 0.1 and r_squared > 0.7
                else "Moderate upward trend" if slope > 0.01
                else "Strong downward trend" if slope < -0.1 and r_squared > 0.7
                else "Moderate downward trend" if slope < -0.01
                else "Stable / no significant trend"
            ),
            "total_change_pct": round(change_pct, 2),
            "volatility": round(volatility, 4),
            "smoothed_values": smoothed,
            "inflection_points": inflections,
            "forecast": forecasts,
            "forecast_quality": (
                "HIGH" if r_squared > 0.8
                else "MODERATE" if r_squared > 0.5
                else "LOW"
            ),
        }


class BenchmarkingEngine:
    """7. Benchmarking — gap analysis and improvement priority ranking."""

    @staticmethod
    def analyze(metrics: list) -> dict:
        results = []
        for m in metrics:
            your = m.get("your_value", 0)
            bench = m.get("industry_benchmark", 0)
            best = m.get("best_in_class", 0)
            higher_is = m.get("higher_is_better", True)

            gap_bench = ((your - bench) / bench * 100) if bench != 0 else 0.0
            gap_best = ((your - best) / best * 100) if best != 0 else 0.0

            if higher_is:
                performance = (
                    "ABOVE_BENCHMARK" if gap_bench > 0
                    else "AT_BENCHMARK" if gap_bench > -5
                    else "BELOW_BENCHMARK"
                )
                priority = (
                    "MAINTAIN" if gap_bench > 10
                    else "OPTIMIZE" if gap_bench > 0
                    else "IMPROVE_URGENT" if gap_bench < -20
                    else "IMPROVE"
                )
            else:
                gap_bench = -gap_bench
                gap_best = -gap_best
                performance = (
                    "ABOVE_BENCHMARK" if gap_bench > 0
                    else "AT_BENCHMARK" if gap_bench > -5
                    else "BELOW_BENCHMARK"
                )
                priority = (
                    "MAINTAIN" if gap_bench > 10
                    else "OPTIMIZE" if gap_bench > 0
                    else "IMPROVE_URGENT" if gap_bench < -20
                    else "IMPROVE"
                )

            results.append({
                "metric_name": m.get("metric_name", ""),
                "your_value": your,
                "industry_benchmark": bench,
                "best_in_class": best,
                "gap_to_benchmark_pct": round(gap_bench, 2),
                "gap_to_best_pct": round(gap_best, 2),
                "unit": m.get("unit", ""),
                "performance": performance,
                "priority": priority,
            })

        results.sort(key=lambda x: x["gap_to_benchmark_pct"])
        for i, r in enumerate(results):
            r["improvement_rank"] = i + 1

        above = len([r for r in results if r["performance"] == "ABOVE_BENCHMARK"])
        below = len([r for r in results if r["performance"] == "BELOW_BENCHMARK"])
        urgent = len([r for r in results if r["priority"] == "IMPROVE_URGENT"])

        avg_gap = (
            sum(r["gap_to_benchmark_pct"] for r in results) / len(results)
            if results else 0
        )

        return {
            "metrics_count": len(results),
            "rankings": results,
            "above_benchmark_count": above,
            "below_benchmark_count": below,
            "urgent_improvements": urgent,
            "average_gap_to_benchmark_pct": round(avg_gap, 2),
            "overall_position": (
                "LEADER" if below == 0
                else "COMPETITIVE" if above > below
                else "LAGGING"
            ),
        }


class MarketResearchEngine:
    """8. Market Research — market sizing, attractiveness, and entry feasibility."""

    @staticmethod
    def analyze(data: dict) -> dict:
        tam = data.get("tam", 0)
        sam = data.get("sam", 0)
        som = data.get("som", 0)
        growth = data.get("growth_rate_pct", 0)
        intensity = data.get("competitive_intensity", 5)
        barriers = data.get("barriers_to_entry", 5)
        reg_risk = data.get("regulatory_risk", 5)
        tech_risk = data.get("technology_risk", 5)

        sam_ratio = (sam / tam * 100) if tam > 0 else 0
        som_ratio = (som / sam * 100) if sam > 0 else 0

        market_score = (
            min(growth / 2, 10) * 0.25
            + (10 - intensity) * 0.20
            + (10 - barriers) * 0.15
            + (10 - reg_risk) * 0.20
            + (10 - tech_risk) * 0.20
        )

        if market_score >= 7:
            attractiveness = "HIGH"
            entry_strategy = "AGGRESSIVE_ENTRY"
            feasibility = "STRONG"
        elif market_score >= 5:
            attractiveness = "MODERATE"
            entry_strategy = "SELECTIVE_ENTRY"
            feasibility = "VIABLE"
        elif market_score >= 3:
            attractiveness = "LOW"
            entry_strategy = "CAUTIOUS_ENTRY"
            feasibility = "CHALLENGING"
        else:
            attractiveness = "VERY_LOW"
            entry_strategy = "AVOID_OR_DEFER"
            feasibility = "WEAK"

        return {
            "market_name": data.get("market_name", ""),
            "tam": tam,
            "sam": sam,
            "som": som,
            "sam_to_tam_pct": round(sam_ratio, 2),
            "som_to_sam_pct": round(som_ratio, 2),
            "growth_rate_pct": growth,
            "market_attractiveness_score": round(market_score, 4),
            "attractiveness_rating": attractiveness,
            "entry_feasibility": feasibility,
            "recommended_entry_strategy": entry_strategy,
            "risk_factors": {
                "competitive_intensity": intensity,
                "barriers_to_entry": barriers,
                "regulatory_risk": reg_risk,
                "technology_risk": tech_risk,
            },
        }


class StakeholderMappingEngine:
    """9. Stakeholder Mapping — power/interest grid with engagement strategies."""

    @staticmethod
    def _quadrant(power: int, interest: int) -> str:
        if power >= 6 and interest >= 6:
            return "HIGH_POWER_HIGH_INTEREST"
        elif power >= 6 and interest < 6:
            return "HIGH_POWER_LOW_INTEREST"
        elif power < 6 and interest >= 6:
            return "LOW_POWER_HIGH_INTEREST"
        else:
            return "LOW_POWER_LOW_INTEREST"

    @staticmethod
    def _engagement_strategy(quadrant: str, attitude: str) -> str:
        strategies = {
            "HIGH_POWER_HIGH_INTEREST": {
                "supporter": "COLLABORATE — leverage as strategic champion",
                "neutral": "ENGAGE — convert to supporter through regular dialogue",
                "opponent": "DEFUSE — address concerns directly, negotiate compromises",
            },
            "HIGH_POWER_LOW_INTEREST": {
                "supporter": "MAINTAIN — keep satisfied with periodic updates",
                "neutral": "SATISFY — provide key information, avoid overwhelming detail",
                "opponent": "NEUTRALIZE — ensure they have no reason to oppose",
            },
            "LOW_POWER_HIGH_INTEREST": {
                "supporter": "LEVERAGE — use as grassroots advocates and information source",
                "neutral": "INFORM — keep informed, they may provide useful intelligence",
                "opponent": "MONITOR — watch for escalation in power",
            },
            "LOW_POWER_LOW_INTEREST": {
                "supporter": "ACKNOWLEDGE — minimal effort, show appreciation",
                "neutral": "MONITOR — low priority, check periodically",
                "opponent": "WATCH — unlikely to cause issues but monitor for changes",
            },
        }
        return strategies.get(quadrant, {}).get(attitude, "MONITOR")

    @staticmethod
    def analyze(stakeholders: list) -> dict:
        grid = {
            "HIGH_POWER_HIGH_INTEREST": [],
            "HIGH_POWER_LOW_INTEREST": [],
            "LOW_POWER_HIGH_INTEREST": [],
            "LOW_POWER_LOW_INTEREST": [],
        }

        results = []
        for s in stakeholders:
            quad = StakeholderMappingEngine._quadrant(s["power_score"], s["interest_score"])
            strategy = StakeholderMappingEngine._engagement_strategy(quad, s.get("attitude", "neutral"))
            grid[quad].append(s["name"])
            results.append({
                "name": s["name"],
                "power_score": s["power_score"],
                "interest_score": s["interest_score"],
                "attitude": s.get("attitude", "neutral"),
                "quadrant": quad,
                "engagement_strategy": strategy,
                "influence_notes": s.get("influence_notes", ""),
            })

        opponents_count = len([r for r in results if r["attitude"] == "opponent"])
        supporters_count = len([r for r in results if r["attitude"] == "supporter"])
        critical_zone = grid["HIGH_POWER_HIGH_INTEREST"]

        return {
            "stakeholder_count": len(results),
            "stakeholders": results,
            "power_interest_grid": grid,
            "summary": {
                "supporters": supporters_count,
                "neutral": len(results) - supporters_count - opponents_count,
                "opponents": opponents_count,
                "critical_stakeholders": critical_zone,
            },
            "risk_indicator": (
                "HIGH" if opponents_count > 0 and len(critical_zone) > 0
                else "MODERATE" if opponents_count > 0
                else "LOW"
            ),
        }


class EnvironmentalAssessmentEngine:
    """10. Environmental Assessment — comprehensive external scan aggregation."""

    DEFAULT_WEIGHTS = {
        "pestel": 0.25,
        "swot": 0.20,
        "competitor": 0.20,
        "trend": 0.15,
        "market": 0.20,
    }

    @staticmethod
    def analyze(data: dict) -> dict:
        weights = data.get("custom_weights") or EnvironmentalAssessmentEngine.DEFAULT_WEIGHTS
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        scores = {}
        weighted_sum = 0.0
        available = 0

        for key in ["pestel", "swot", "competitor", "trend", "market"]:
            val = data.get(f"{key}_score")
            if val is not None:
                normalized = max(min(val, 100), 0) if key != "swot" else max(min(val, 100), -100)
                scores[key] = round(normalized, 2)
                w = weights.get(key, 0.2)
                if key == "swot":
                    norm_for_weight = (normalized + 100) / 2
                else:
                    norm_for_weight = normalized
                weighted_sum += norm_for_weight * w
                available += 1

        overall = round(weighted_sum, 2) if available > 0 else 0.0

        if overall >= 75:
            health = "STRONG"
            health_desc = "Favorable environment — pursue offensive strategies."
        elif overall >= 50:
            health = "MODERATE"
            health_desc = "Mixed signals — balanced approach recommended."
        elif overall >= 30:
            health = "CONCERNING"
            health_desc = "Challenging environment — defensive posture advised."
        else:
            health = "CRITICAL"
            health_desc = "Hostile environment — immediate strategic restructuring needed."

        top_issues = data.get("top_issues", [])
        if not top_issues and available > 0:
            weakest = min(scores.items(), key=lambda x: x[1]) if scores else None
            if weakest:
                top_issues = [f"{weakest[0].upper()} dimension requires attention (score: {weakest[1]})"]

        recommendations = []
        if scores.get("pestel", 50) < 40:
            recommendations.append("Conduct deeper PESTEL analysis to identify specific risks")
        if scores.get("swot", 0) < 0:
            recommendations.append("Address internal weaknesses before pursuing growth")
        if scores.get("competitor", 50) < 40:
            recommendations.append("Invest in competitive intelligence and differentiation")
        if scores.get("trend", 50) < 40:
            recommendations.append("Develop trend monitoring capabilities and early warning systems")
        if scores.get("market", 50) < 40:
            recommendations.append("Reassess market attractiveness and consider pivoting")
        if not recommendations:
            recommendations.append("Maintain current strategic direction with periodic reassessment")

        return {
            "assessment_name": data.get("assessment_name", "Comprehensive Assessment"),
            "scores_used": scores,
            "weights_applied": {k: round(v, 4) for k, v in weights.items()},
            "environmental_health_score": overall,
            "health_rating": health,
            "health_description": health_desc,
            "top_5_strategic_issues": top_issues[:5],
            "recommended_actions": recommendations,
            "dimensions_analyzed": available,
        }
