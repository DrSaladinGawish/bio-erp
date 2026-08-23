from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


# =============================================================================
# 1. Balanced Scorecard (BSC) Engine
# =============================================================================


class BSCEngine:
    """Weighted Balanced Scorecard with perspective-level and KPI-level scoring."""

    def calculate_scorecard(
        self,
        perspectives: List[Dict[str, Any]],
        period: str,
    ) -> Dict[str, Any]:
        perspective_scores = []
        total_weighted_score = 0.0
        total_weight = 0.0

        for p in perspectives:
            name = p["perspective_name"]
            weight = p["weight_pct"] / 100.0
            kpis = p.get("kpis", [])

            if not kpis:
                perspective_score = 0.0
            else:
                kpi_total_weight = sum(k.get("weight_pct", 1.0) for k in kpis)
                if kpi_total_weight == 0:
                    kpi_total_weight = len(kpis)

                kpi_weighted_sum = 0.0
                for kpi in kpis:
                    actual = kpi.get("actual_value", 0)
                    target = kpi.get("target_value", 1)
                    kpi_weight = kpi.get("weight_pct", 1.0) / kpi_total_weight
                    ratio = _safe_div(actual, target, 0.0)
                    kpi_weighted_sum += min(ratio, 1.5) * kpi_weight * 100

                perspective_score = round(kpi_weighted_sum, 2)

            total_weighted_score += perspective_score * weight
            total_weight += weight

            perspective_scores.append(
                {
                    "perspective_name": name,
                    "weight_pct": p["weight_pct"],
                    "kpis_count": len(kpis),
                    "score": perspective_score,
                    "weighted_contribution": round(perspective_score * weight, 2),
                }
            )

        overall_weight = total_weight if total_weight > 0 else 1.0
        overall_index = round(total_weighted_score / overall_weight, 2)
        rating = self._classify_score(overall_index)

        return {
            "perspective_scores": perspective_scores,
            "weighted_total_score": round(total_weighted_score, 2),
            "overall_performance_index": round(overall_index, 2),
            "rating": rating,
            "measurement_period": period,
        }

    @staticmethod
    def _classify_score(score: float) -> str:
        if score >= 90:
            return "EXCELLENT"
        if score >= 75:
            return "GOOD"
        if score >= 50:
            return "SATISFACTORY"
        if score >= 30:
            return "NEEDS_IMPROVEMENT"
        return "CRITICAL"


# =============================================================================
# 2. EFQM Excellence Model Engine
# =============================================================================


class EFQMEngine:
    """EFQM 2020 RADAR-based model with 6 criteria on a 1000-point scale."""

    CRITERIA_WEIGHTS = {
        "LEADERSHIP": 1.0,
        "STRATEGY": 1.0,
        "PEOPLE": 1.0,
        "PARTNERSHIPS_RESOURCES": 1.0,
        "PROCESSES_PRODUCTS_RESULTS": 1.0,
        "RESULTS": 1.0,
    }

    def assess(self, criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        criteria_breakdown = []
        total_score = 0.0
        max_possible = 0.0
        strengths: List[str] = []
        improvement_areas: List[str] = []

        for c in criteria:
            name = c["criteria_name"].upper().replace(" ", "_")
            raw_score = c["score"]
            weight = c.get("weight", 1.0)
            sub_criteria = c.get("sub_criteria", [])

            # Validate sub-criteria consistency
            if sub_criteria:
                sub_total = sum(s.get("score", 0) for s in sub_criteria)
                # Use the minimum of sub-criteria total and raw_score for consistency
                adjusted_score = (
                    min(raw_score, sub_total) if sub_total > 0 else raw_score
                )
            else:
                adjusted_score = raw_score

            weighted = adjusted_score * weight
            percentage = _safe_div(adjusted_score, 1000, 0.0) * 100

            total_score += weighted
            max_possible += 1000 * weight

            if percentage >= 75:
                strengths.append(name)
            elif percentage < 50:
                improvement_areas.append(name)

            criteria_breakdown.append(
                {
                    "criteria_name": name,
                    "raw_score": raw_score,
                    "adjusted_score": round(adjusted_score, 2),
                    "weight": weight,
                    "weighted_score": round(weighted, 2),
                    "percentage": round(percentage, 2),
                    "sub_criteria_count": len(sub_criteria),
                }
            )

        excellence_pct = _safe_div(total_score, max_possible, 0.0) * 100
        radar_profile = self._determine_profile(excellence_pct)

        return {
            "total_score": round(total_score, 2),
            "max_possible": round(max_possible, 2),
            "excellence_percentage": round(excellence_pct, 2),
            "radar_profile": radar_profile,
            "criteria_breakdown": criteria_breakdown,
            "strengths": strengths,
            "improvement_areas": improvement_areas,
        }

    @staticmethod
    def _determine_profile(pct: float) -> str:
        if pct >= 80:
            return "WORLD_CLASS"
        if pct >= 60:
            return "EUROPEAN_EXCELLENCE"
        if pct >= 40:
            return "NATIONAL_EXCELLENCE"
        if pct >= 20:
            return "DEVELOPING"
        return "BEGINNER"


# =============================================================================
# 3. Total Quality Management (TQM) Engine
# =============================================================================


class TQMEngine:
    """8-pillar TQM maturity model with weighted scoring."""

    MATURITY_LABELS = {
        1: "INITIAL",
        2: "DEVELOPING",
        3: "DEFINED",
        4: "MANAGED",
        5: "OPTIMIZED",
    }

    def assess(self, pillars: List[Dict[str, Any]]) -> Dict[str, Any]:
        pillar_details = []
        total_weighted = 0.0
        total_weight = 0.0
        scores: List[Tuple[str, float]] = []

        for p in pillars:
            name = p["pillar_name"]
            level = p["maturity_level"]
            weight = p.get("weight", 1.0)
            sub_items = p.get("sub_items", [])

            # Score: maturity mapped to 0-100 scale
            maturity_score = (level / 5.0) * 100

            # Sub-item adjustment: average sub-item scores pull maturity up/down
            if sub_items:
                sub_avg = _safe_div(
                    sum(s.get("score", level * 20) for s in sub_items),
                    len(sub_items),
                    maturity_score,
                )
                maturity_score = (maturity_score + sub_avg) / 2.0

            weighted = maturity_score * weight
            total_weighted += weighted
            total_weight += weight
            scores.append((name, maturity_score))

            pillar_details.append(
                {
                    "pillar_name": name,
                    "maturity_level": level,
                    "maturity_label": self.MATURITY_LABELS.get(level, "UNKNOWN"),
                    "maturity_score": round(maturity_score, 2),
                    "weight": weight,
                    "weighted_score": round(weighted, 2),
                    "sub_items_count": len(sub_items),
                }
            )

        avg_maturity = _safe_div(
            sum(p["maturity_level"] for p in pillars), len(pillars), 0.0
        )
        weighted_maturity = _safe_div(total_weighted, total_weight, 0.0) / 20.0

        scores.sort(key=lambda x: x[1])
        weakest = (
            [s[0] for s in scores[:2]]
            if len(scores) >= 2
            else [scores[0][0]]
            if scores
            else []
        )
        strongest = (
            [s[0] for s in scores[-2:]]
            if len(scores) >= 2
            else [scores[0][0]]
            if scores
            else []
        )

        overall_rating = self._classify_maturity(avg_maturity)

        return {
            "average_maturity": round(avg_maturity, 2),
            "weighted_maturity": round(weighted_maturity, 2),
            "overall_tqm_rating": overall_rating,
            "pillar_details": pillar_details,
            "weakest_pillars": weakest,
            "strongest_pillars": strongest,
        }

    @staticmethod
    def _classify_maturity(avg: float) -> str:
        if avg >= 4.5:
            return "WORLD_CLASS_QUALITY"
        if avg >= 3.5:
            return "ADVANCED_QUALITY"
        if avg >= 2.5:
            return "ESTABLISHED_QUALITY"
        if avg >= 1.5:
            return "DEVELOPING_QUALITY"
        return "INITIAL_QUALITY"


# =============================================================================
# 4. KPI Frameworks Engine
# =============================================================================


class KPIFrameworkEngine:
    """Custom KPI tracking with weighted variance analysis."""

    def analyze(self, kpis: List[Dict[str, Any]], framework: str) -> Dict[str, Any]:
        results = []
        aggregate_weighted = 0.0
        total_weight = 0.0
        on_track = 0
        at_risk = 0
        behind = 0
        improving = 0
        declining = 0

        for kpi in kpis:
            actual = kpi["actual_value"]
            target = kpi["target_value"]
            weight = kpi.get("weight_pct", 1.0)
            lower_is_better = kpi.get("lower_is_better", False)
            previous = kpi.get("previous_value")

            variance_abs = actual - target
            variance_pct = _safe_div(variance_abs, target, 0.0) * 100

            if lower_is_better:
                if actual <= target:
                    score_pct = 100
                else:
                    score_pct = max(0, 100 - abs(variance_pct))
            else:
                score_pct = min(120, _safe_div(actual, target, 0.0) * 100)

            # Status classification
            if lower_is_better:
                if actual <= target * 0.9:
                    status = "ON_TRACK"
                elif actual <= target * 1.1:
                    status = "AT_RISK"
                else:
                    status = "BEHIND"
            else:
                if actual >= target * 0.9:
                    status = "ON_TRACK"
                elif actual >= target * 0.7:
                    status = "AT_RISK"
                else:
                    status = "BEHIND"

            if status == "ON_TRACK":
                on_track += 1
            elif status == "AT_RISK":
                at_risk += 1
            else:
                behind += 1

            # Trend
            trend = "STABLE"
            if previous is not None and previous != 0:
                trend_change = actual - previous
                if lower_is_better:
                    trend = "IMPROVING" if trend_change < 0 else "DECLINING"
                else:
                    trend = "IMPROVING" if trend_change > 0 else "DECLINING"
                if trend == "IMPROVING":
                    improving += 1
                else:
                    declining += 1

            aggregate_weighted += score_pct * weight
            total_weight += weight

            results.append(
                {
                    "kpi_name": kpi["kpi_name"],
                    "category": kpi.get("category", "OPERATIONAL"),
                    "actual_value": actual,
                    "target_value": target,
                    "variance_abs": round(variance_abs, 2),
                    "variance_pct": round(variance_pct, 2),
                    "score_pct": round(score_pct, 2),
                    "weight": weight,
                    "status": status,
                    "trend": trend,
                    "lower_is_better": lower_is_better,
                    "unit": kpi.get("unit", "%"),
                }
            )

        aggregate_score = round(_safe_div(aggregate_weighted, total_weight, 0.0), 2)

        return {
            "framework": framework,
            "total_kpis": len(kpis),
            "kpi_results": results,
            "aggregate_score": aggregate_score,
            "on_track_count": on_track,
            "at_risk_count": at_risk,
            "behind_count": behind,
            "trend_summary": {
                "improving": improving,
                "declining": declining,
                "stable": len(kpis) - improving - declining,
            },
        }


# =============================================================================
# 5. Performance Dashboards Engine
# =============================================================================


class DashboardEngine:
    """Real-time metric aggregation with traffic-light classification."""

    def aggregate(
        self,
        metrics: List[Dict[str, Any]],
        time_period: str,
        baseline: Optional[str],
    ) -> Dict[str, Any]:
        statuses = []
        total_weighted = 0.0
        total_weight = 0.0
        green = 0
        amber = 0
        red = 0

        for m in metrics:
            current = m["current_value"]
            target = m["target_value"]
            previous = m.get("previous_value", 0.0)
            weight = m.get("weight_pct", 1.0)
            threshold_green = m.get("threshold_green")
            threshold_amber = m.get("threshold_amber")

            ratio = _safe_div(current, target, 0.0)

            # Use explicit thresholds if provided, otherwise use ratio
            if threshold_green is not None and threshold_amber is not None:
                if current >= threshold_green:
                    health = "GREEN"
                elif current >= threshold_amber:
                    health = "AMBER"
                else:
                    health = "RED"
            else:
                if ratio >= 0.9:
                    health = "GREEN"
                elif ratio >= 0.7:
                    health = "AMBER"
                else:
                    health = "RED"

            if health == "GREEN":
                green += 1
            elif health == "AMBER":
                amber += 1
            else:
                red += 1

            delta = current - previous
            delta_pct = _safe_div(delta, previous, 0.0) * 100 if previous else 0.0

            metric_score = min(100, ratio * 100)
            total_weighted += metric_score * weight
            total_weight += weight

            statuses.append(
                {
                    "metric_name": m["metric_name"],
                    "current_value": current,
                    "target_value": target,
                    "previous_value": previous,
                    "delta": round(delta, 2),
                    "delta_pct": round(delta_pct, 2),
                    "health": health,
                    "category": m.get("category", "GENERAL"),
                    "unit": m.get("unit", ""),
                    "weight": weight,
                    "score": round(metric_score, 2),
                }
            )

        aggregate_score = round(_safe_div(total_weighted, total_weight, 0.0), 2)

        total = green + amber + red
        if total == 0:
            overall_health = "NO_DATA"
        elif red > total * 0.3:
            overall_health = "CRITICAL"
        elif amber > total * 0.5:
            overall_health = "WARNING"
        elif green >= total * 0.8:
            overall_health = "HEALTHY"
        else:
            overall_health = "FAIR"

        return {
            "aggregate_score": aggregate_score,
            "metrics_count": len(metrics),
            "metrics_status": statuses,
            "green_count": green,
            "amber_count": amber,
            "red_count": red,
            "time_period": time_period,
            "overall_health": overall_health,
        }


# =============================================================================
# 6. Benchmarking Engine
# =============================================================================


class BenchmarkingEngine:
    """Industry benchmarking with competitive gap analysis."""

    def compare(self, metrics: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
        comparisons = []
        leading = 0
        lagging = 0
        par = 0
        weighted_index = 0.0
        total_importance = 0.0

        for m in metrics:
            org_val = m["organization_value"]
            avg_val = m["industry_average"]
            best_val = m["industry_best"]
            importance = m.get("importance", 1.0)

            vs_avg_gap = _safe_div(org_val - avg_val, avg_val, 0.0) * 100
            vs_best_gap = _safe_div(org_val - best_val, best_val, 0.0) * 100

            # Competitive position relative to average
            if vs_avg_gap > 5:
                position = "LEADING"
                leading += 1
            elif vs_avg_gap < -5:
                position = "LAGGING"
                lagging += 1
            else:
                position = "AT_PAR"
                par += 1

            # Relative strength score: how close to best-in-class
            if best_val > 0:
                strength = min(100, (org_val / best_val) * 100)
            else:
                strength = 0

            weighted_index += strength * importance
            total_importance += importance

            comparisons.append(
                {
                    "metric_name": m["metric_name"],
                    "organization_value": org_val,
                    "industry_average": avg_val,
                    "industry_best": best_val,
                    "vs_average_gap_pct": round(vs_avg_gap, 2),
                    "vs_best_gap_pct": round(vs_best_gap, 2),
                    "position": position,
                    "strength_score": round(strength, 2),
                    "importance": importance,
                    "unit": m.get("unit", "%"),
                }
            )

        overall_index = round(_safe_div(weighted_index, total_importance, 0.0), 2)

        if overall_index >= 80:
            competitive_position = "MARKET_LEADER"
        elif overall_index >= 60:
            competitive_position = "COMPETITIVE"
        elif overall_index >= 40:
            competitive_position = "FOLLOWER"
        else:
            competitive_position = "LAGGARD"

        return {
            "overall_benchmark_index": overall_index,
            "metrics_comparison": comparisons,
            "leading_count": leading,
            "lagging_count": lagging,
            "par_count": par,
            "competitive_position": competitive_position,
        }


# =============================================================================
# 7. Strategy Maps Engine
# =============================================================================


class StrategyMapEngine:
    """Strategy map with causal link validation and critical-path detection."""

    def build_map(
        self, nodes: List[Dict[str, Any]], strategy_name: str
    ) -> Dict[str, Any]:
        nodes_dict = {n["node_id"]: n for n in nodes}
        links = []
        perspective_coverage: Dict[str, int] = {}

        # Validate links and detect cycles
        for node in nodes:
            perspective = node["perspective"]
            perspective_coverage[perspective] = (
                perspective_coverage.get(perspective, 0) + 1
            )

            for parent_id in node.get("parent_ids", []):
                if parent_id in nodes_dict:
                    links.append(
                        {
                            "source": parent_id,
                            "target": node["node_id"],
                            "source_perspective": nodes_dict[parent_id]["perspective"],
                            "target_perspective": perspective,
                        }
                    )

        # Detect circular dependencies using DFS
        circular = self._detect_cycles(nodes, links)
        critical_path = self._find_critical_path(nodes, links)

        return {
            "strategy_name": strategy_name,
            "nodes_count": len(nodes),
            "links_count": len(links),
            "nodes": nodes,
            "links": links,
            "perspective_coverage": perspective_coverage,
            "critical_path": critical_path,
            "circular_dependencies": circular,
        }

    @staticmethod
    def _detect_cycles(nodes: List[Dict], links: List[Dict]) -> List[str]:
        adj: Dict[str, List[str]] = {}
        for node in nodes:
            adj[node["node_id"]] = []
        for link in links:
            if link["source"] in adj:
                adj[link["source"]].append(link["target"])

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in adj}
        cycles: List[str] = []

        def dfs(u: str, path: List[str]) -> None:
            color[u] = GRAY
            path.append(u)
            for v in adj.get(u, []):
                if color.get(v) == GRAY:
                    cycle_start = path.index(v)
                    cycles.append(" -> ".join(path[cycle_start:] + [v]))
                elif color.get(v) == WHITE:
                    dfs(v, path)
            path.pop()
            color[u] = BLACK

        for nid in adj:
            if color[nid] == WHITE:
                dfs(nid, [])

        return cycles

    @staticmethod
    def _find_critical_path(nodes: List[Dict], links: List[Dict]) -> List[str]:
        # Build adjacency and in-degree
        adj: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}
        for node in nodes:
            nid = node["node_id"]
            adj[nid] = []
            in_degree[nid] = 0
        for link in links:
            src, tgt = link["source"], link["target"]
            if src in adj:
                adj[src].append(tgt)
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        # Topological sort, tracking longest path
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        dist = {nid: 0 for nid in in_degree}
        parent_map: Dict[str, Optional[str]] = {nid: None for nid in in_degree}

        while queue:
            current = queue.pop(0)
            for neighbor in adj.get(current, []):
                if dist[current] + 1 > dist.get(neighbor, 0):
                    dist[neighbor] = dist[current] + 1
                    parent_map[neighbor] = current
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if not dist:
            return []

        end_node = max(dist, key=dist.get)
        path = []
        node = end_node
        while node is not None:
            path.append(node)
            node = parent_map.get(node)
        path.reverse()
        return path


# =============================================================================
# 8. Performance Contracts Engine
# =============================================================================


class PerformanceContractEngine:
    """Employee KPI agreement tracking with achievement scoring."""

    def evaluate_contract(
        self,
        employee_id: str,
        employee_name: str,
        period: str,
        kpis: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_weight = sum(k.get("weight_pct", 0) for k in kpis)
        weight_valid = abs(total_weight - 100.0) < 0.01

        achieved_score = 0.0
        for kpi in kpis:
            target = kpi.get("target_value", 0)
            achieved = kpi.get("achieved_value", 0)
            weight = kpi.get("weight_pct", 0) / 100.0
            if target > 0:
                kpi_score = min(120, (achieved / target) * 100)
            else:
                kpi_score = 0
            achieved_score += kpi_score * weight

        achieved_score = round(achieved_score, 2)
        rating = self._classify_achievement(achieved_score)

        return {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "review_period": period,
            "total_weight": round(total_weight, 2),
            "weight_valid": weight_valid,
            "kpis_count": len(kpis),
            "contract_status": "VALID" if weight_valid else "INVALID_WEIGHTS",
            "achieved_score": achieved_score,
            "performance_rating": rating,
        }

    @staticmethod
    def _classify_achievement(score: float) -> str:
        if score >= 110:
            return "EXCEPTIONAL"
        if score >= 90:
            return "EXCEEDS_EXPECTATIONS"
        if score >= 70:
            return "MEETS_EXPECTATIONS"
        if score >= 50:
            return "PARTIALLY_MEETS"
        return "BELOW_EXPECTATIONS"


# =============================================================================
# 9. OKR Cascading Engine
# =============================================================================


class OKRCascadingEngine:
    """Company → Department → Team OKR alignment scoring."""

    def cascade(
        self,
        company_okrs: List[Dict[str, Any]],
        department_okrs: List[Dict[str, Any]],
        team_okrs: List[Dict[str, Any]],
        quarter: str,
    ) -> Dict[str, Any]:
        company_score = self._score_okr_set(company_okrs)
        dept_score = self._score_okr_set(department_okrs)
        team_score = self._score_okr_set(team_okrs)

        # Alignment: departments should support company, teams should support departments
        alignment_score = 0.0
        if company_okrs:
            alignment_score += company_score * 0.4
        if department_okrs:
            alignment_score += dept_score * 0.35
        if team_okrs:
            alignment_score += team_score * 0.25

        # Cascading score: how many lower-level OKRs connect to upper-level
        cascading = self._calculate_cascading_depth(
            company_okrs, department_okrs, team_okrs
        )

        # At-risk OKRs
        at_risk = []
        for okr_set, level in [
            (company_okrs, "company"),
            (department_okrs, "department"),
            (team_okrs, "team"),
        ]:
            for okr in okr_set:
                completion = self._okr_completion(okr)
                if completion < 0.3:
                    at_risk.append(f"[{level}] {okr.get('objective', 'unknown')}")

        return {
            "company_alignment": round(company_score, 2),
            "department_alignment": round(dept_score, 2),
            "team_alignment": round(team_score, 2),
            "overall_alignment": round(alignment_score, 2),
            "cascading_score": round(cascading, 2),
            "okr_summary": {
                "company_okrs": len(company_okrs),
                "department_okrs": len(department_okrs),
                "team_okrs": len(team_okrs),
                "total_key_results": sum(
                    len(o.get("key_results", []))
                    for o in company_okrs + department_okrs + team_okrs
                ),
            },
            "quarter": quarter,
            "at_risk_okrs": at_risk,
        }

    @staticmethod
    def _score_okr_set(okrs: List[Dict[str, Any]]) -> float:
        if not okrs:
            return 0.0
        total = 0.0
        for okr in okrs:
            total += OKRCascadingEngine._okr_completion(okr) * 100
        return total / len(okrs)

    @staticmethod
    def _okr_completion(okr: Dict[str, Any]) -> float:
        key_results = okr.get("key_results", [])
        if not key_results:
            return 0.0
        total = 0.0
        for kr in key_results:
            target = kr.get("target_value", 1)
            current = kr.get("current_value", 0)
            total += min(1.0, current / target) if target > 0 else 0
        return total / len(key_results)

    @staticmethod
    def _calculate_cascading_depth(
        company: List[Dict], dept: List[Dict], team: List[Dict]
    ) -> float:
        depth = 0
        if company:
            depth += 40
        if dept and company:
            dept_connected = sum(
                1
                for d in dept
                if any(
                    d.get("department") and c.get("department") == d.get("department")
                    for c in company
                )
            )
            depth += 35 * (dept_connected / len(dept)) if dept else 0
        if team and dept:
            team_connected = sum(
                1
                for t in team
                if any(
                    t.get("department") and d.get("department") == t.get("department")
                    for d in dept
                )
            )
            depth += 25 * (team_connected / len(team)) if team else 0
        return depth


# =============================================================================
# 10. Performance Reviews Engine
# =============================================================================


class PerformanceReviewEngine:
    """Entity-based performance scoring with weighted metrics."""

    def review(
        self,
        metrics: List[Dict[str, Any]],
        entity_id: str,
        entity_type: str,
        period: str,
    ) -> Dict[str, Any]:
        details = []
        total_weighted = 0.0
        total_weight = 0.0
        strengths: List[str] = []
        improvement_areas: List[str] = []

        for m in metrics:
            actual = m["actual_value"]
            target = m["target_value"]
            weight = m.get("weight_pct", 1.0)

            score = min(100, _safe_div(actual, target, 0.0) * 100) if target > 0 else 0
            total_weighted += score * weight
            total_weight += weight

            if score >= 80:
                strengths.append(m["metric_name"])
            elif score < 50:
                improvement_areas.append(m["metric_name"])

            details.append(
                {
                    "metric_name": m["metric_name"],
                    "actual_value": actual,
                    "target_value": target,
                    "score": round(score, 2),
                    "weight": weight,
                    "variance_pct": round(
                        _safe_div(actual - target, target, 0.0) * 100, 2
                    ),
                }
            )

        overall = round(_safe_div(total_weighted, total_weight, 0.0), 2)
        rating = self._classify(overall)

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "overall_score": overall,
            "rating": rating,
            "metric_details": details,
            "period": period,
            "improvement_areas": improvement_areas,
            "strengths": strengths,
        }

    @staticmethod
    def _classify(score: float) -> str:
        if score >= 90:
            return "A_OUTSTANDING"
        if score >= 75:
            return "B_GOOD"
        if score >= 60:
            return "C_SATISFACTORY"
        if score >= 40:
            return "D_NEEDS_IMPROVEMENT"
        return "E_UNSATISFACTORY"


# =============================================================================
# 11. Gap Analysis Engine
# =============================================================================


class GapAnalysisEngine:
    """Current vs Target gap analysis with priority ranking."""

    def analyze(
        self, metrics: List[Dict[str, Any]], target_date: Optional[str]
    ) -> Dict[str, Any]:
        analysis = []
        critical = 0
        moderate = 0
        minor = 0

        for m in metrics:
            current = m["current_value"]
            target = m["target_value"]
            gap = target - current
            gap_pct = _safe_div(gap, target, 0.0) * 100 if target else 0
            priority = m.get("priority", 1)

            if abs(gap_pct) > 30:
                severity = "CRITICAL"
                critical += 1
            elif abs(gap_pct) > 15:
                severity = "MODERATE"
                moderate += 1
            else:
                severity = "MINOR"
                minor += 1

            completion = (
                min(100, _safe_div(current, target, 0.0) * 100) if target > 0 else 0
            )

            analysis.append(
                {
                    "metric_name": m["metric_name"],
                    "current_value": current,
                    "target_value": target,
                    "gap": round(gap, 2),
                    "gap_pct": round(gap_pct, 2),
                    "severity": severity,
                    "priority": priority,
                    "category": m.get("category", "GENERAL"),
                    "completion_pct": round(completion, 2),
                }
            )

        # Priority ranking by gap magnitude and priority
        ranked = sorted(
            analysis,
            key=lambda x: abs(x["gap_pct"]) * (6 - x["priority"]),
            reverse=True,
        )

        overall_gap = _safe_div(
            sum(abs(a["gap_pct"]) for a in analysis), len(analysis), 0.0
        )

        return {
            "overall_gap_percentage": round(overall_gap, 2),
            "metrics_analysis": analysis,
            "critical_gaps": critical,
            "moderate_gaps": moderate,
            "minor_gaps": minor,
            "priority_ranking": [
                {
                    "metric": r["metric_name"],
                    "gap_pct": r["gap_pct"],
                    "severity": r["severity"],
                }
                for r in ranked
            ],
        }


# =============================================================================
# 12. Improvement Plans Engine
# =============================================================================


class ImprovementPlanEngine:
    """Area-based improvement tracking with feasibility scoring."""

    def plan(
        self,
        area: str,
        current_score: float,
        target_score: float,
        actions: List[Dict[str, Any]],
        timeline: str,
    ) -> Dict[str, Any]:
        gap = target_score - current_score
        gap_pct = _safe_div(gap, target_score, 0.0) * 100 if target_score else 0

        planned = sum(1 for a in actions if a.get("status") == "PLANNED")
        in_progress = sum(1 for a in actions if a.get("status") == "IN_PROGRESS")
        completed = sum(1 for a in actions if a.get("status") == "COMPLETED")

        # Estimated improvement from completed + in-progress actions
        est_improvement = sum(
            a.get("estimated_impact", 0)
            for a in actions
            if a.get("status") in ("COMPLETED", "IN_PROGRESS")
        )
        est_improvement = min(est_improvement, gap)

        # Feasibility: based on gap closability
        closable_pct = _safe_div(est_improvement, gap, 0.0) * 100 if gap > 0 else 100
        action_coverage = _safe_div(len(actions), max(1, gap / 10), 0.0) * 100
        feasibility = min(100, (closable_pct * 0.6 + min(100, action_coverage) * 0.4))

        return {
            "area": area,
            "gap": round(gap, 2),
            "gap_percentage": round(gap_pct, 2),
            "actions_count": len(actions),
            "planned_actions": planned,
            "in_progress_actions": in_progress,
            "completed_actions": completed,
            "estimated_improvement": round(est_improvement, 2),
            "feasibility_score": round(feasibility, 2),
            "timeline": timeline,
        }


# =============================================================================
# 13. Balanced Scorecard Variance Engine
# =============================================================================


class BSCVarianceEngine:
    """BSC variance analysis with corrective action detection."""

    def analyze(self, metrics: List[Dict[str, Any]], period: str) -> Dict[str, Any]:
        perspective_map: Dict[str, List[Dict]] = {}
        for m in metrics:
            persp = m["perspective"]
            if persp not in perspective_map:
                perspective_map[persp] = []
            perspective_map[persp].append(m)

        perspective_variances = []
        overall_weighted_variance = 0.0
        total_weight = 0.0
        within_tol = 0
        exceeding_tol = 0
        corrective: List[str] = []

        for persp, persp_metrics in perspective_map.items():
            persp_variance = 0.0
            persp_weight = 0.0
            persp_details = []

            for m in persp_metrics:
                actual = m["actual_value"]
                target = m["target_value"]
                weight = m.get("weight_pct", 1.0)
                tolerance = m.get("tolerance_pct", 10.0)

                variance_abs = actual - target
                variance_pct = _safe_div(variance_abs, target, 0.0) * 100

                in_tolerance = abs(variance_pct) <= tolerance
                if in_tolerance:
                    within_tol += 1
                else:
                    exceeding_tol += 1
                    if variance_pct < -tolerance:
                        corrective.append(
                            f"{persp}/{m['metric_name']}: "
                            f"below target by {abs(variance_pct):.1f}%"
                        )

                persp_variance += abs(variance_pct) * weight
                persp_weight += weight

                persp_details.append(
                    {
                        "metric_name": m["metric_name"],
                        "actual": actual,
                        "target": target,
                        "variance_abs": round(variance_abs, 2),
                        "variance_pct": round(variance_pct, 2),
                        "within_tolerance": in_tolerance,
                        "weight": weight,
                    }
                )

            avg_persp_var = _safe_div(persp_variance, persp_weight, 0.0)
            perspective_variances.append(
                {
                    "perspective": persp,
                    "average_variance_pct": round(avg_persp_var, 2),
                    "metrics": persp_details,
                }
            )
            overall_weighted_variance += persp_variance
            total_weight += persp_weight

        overall_var = round(_safe_div(overall_weighted_variance, total_weight, 0.0), 2)

        total = within_tol + exceeding_tol
        if overall_var <= 5 and exceeding_tol == 0:
            status = "ON_TRACK"
        elif overall_var <= 15:
            status = "VARIANCE_WARNING"
        else:
            status = "CRITICAL_VARIANCE"

        return {
            "period": period,
            "perspective_variances": perspective_variances,
            "overall_variance_pct": overall_var,
            "total_metrics": total,
            "within_tolerance": within_tol,
            "exceeding_tolerance": exceeding_tol,
            "performance_status": status,
            "corrective_actions_needed": corrective,
        }


# =============================================================================
# 14. Performance Measurement Systems Engine
# =============================================================================


class MeasurementSystemEngine:
    """Multi-framework integration scoring and maturity assessment."""

    FRAMEWORK_BENCHMARKS = {
        "BSC": {"max_metrics": 20, "typical_weight": 1.2},
        "EFQM": {"max_metrics": 30, "typical_weight": 1.0},
        "TQM": {"max_metrics": 16, "typical_weight": 0.8},
        "OKR": {"max_metrics": 15, "typical_weight": 1.1},
        "KPI": {"max_metrics": 50, "typical_weight": 1.0},
        "SIX_SIGMA": {"max_metrics": 25, "typical_weight": 1.3},
        "ISO9001": {"max_metrics": 20, "typical_weight": 0.9},
        "CUSTOM": {"max_metrics": 30, "typical_weight": 1.0},
    }

    def evaluate(
        self, system_name: str, frameworks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total_metrics = 0
        weighted_score = 0.0
        total_weight = 0.0
        details = []

        for fw in frameworks:
            name = fw["framework_name"].upper().replace(" ", "_")
            metrics_count = fw["metrics_count"]
            weight = fw.get("weight_pct", 1.0)
            score = fw.get("score", 0.0)

            benchmark = self.FRAMEWORK_BENCHMARKS.get(
                name, self.FRAMEWORK_BENCHMARKS["CUSTOM"]
            )
            coverage = min(100, (metrics_count / benchmark["max_metrics"]) * 100)
            effectiveness = score * (coverage / 100)

            total_metrics += metrics_count
            weighted_score += effectiveness * weight
            total_weight += weight

            details.append(
                {
                    "framework_name": name,
                    "metrics_count": metrics_count,
                    "weight": weight,
                    "score": score,
                    "coverage_pct": round(coverage, 2),
                    "effectiveness": round(effectiveness, 2),
                }
            )

        integration_score = round(_safe_div(weighted_score, total_weight, 0.0), 2)
        maturity = self._classify_maturity(integration_score, len(frameworks))
        recommendations = self._generate_recommendations(frameworks, integration_score)

        return {
            "system_name": system_name,
            "total_frameworks": len(frameworks),
            "total_metrics": total_metrics,
            "integration_score": integration_score,
            "framework_details": details,
            "maturity_level": maturity,
            "recommendations": recommendations,
        }

    @staticmethod
    def _classify_maturity(score: float, fw_count: int) -> str:
        if score >= 80 and fw_count >= 3:
            return "INTEGRATED"
        if score >= 60 and fw_count >= 2:
            return "COORDINATED"
        if score >= 40:
            return "PARTIAL"
        return "EMERGING"

    @staticmethod
    def _generate_recommendations(frameworks: List[Dict], score: float) -> List[str]:
        recs = []
        if len(frameworks) < 2:
            recs.append("Consider integrating multiple performance frameworks")
        if score < 50:
            recs.append("Improve metric coverage across existing frameworks")
        names = [fw["framework_name"].upper() for fw in frameworks]
        if "BSC" not in names and "EFQM" not in names:
            recs.append("Consider adding BSC or EFQM for strategic alignment")
        if "KPI" not in names:
            recs.append("Add a KPI tracking framework for operational metrics")
        if not recs:
            recs.append("Current integration is strong; maintain regular reviews")
        return recs


# =============================================================================
# 15. Results-Based Management Engine
# =============================================================================


class RBMEngine:
    """Outcome-focused evaluation with efficiency and effectiveness scoring."""

    def evaluate(
        self,
        program_name: str,
        outcomes: List[Dict[str, Any]],
        budget_allocated: Optional[float],
        budget_spent: Optional[float],
    ) -> Dict[str, Any]:
        impact_details = []
        efficiency_weighted = 0.0
        effectiveness_weighted = 0.0
        impact_weighted = 0.0
        total_weight = 0.0

        for o in outcomes:
            actual = o["actual_value"]
            target = o["target_value"]
            indicator_type = o.get("indicator_type", "IMPACT")
            weight = o.get("weight_pct", 1.0)

            achievement = min(1.5, _safe_div(actual, target, 0.0)) if target > 0 else 0

            efficiency = min(100, achievement * 100)
            effectiveness = min(100, achievement * 100)
            impact = min(100, achievement * 100)

            # Weight by indicator type
            if indicator_type == "IMPACT":
                impact *= 1.2
            elif indicator_type == "OUTCOME":
                effectiveness *= 1.1
            else:
                efficiency *= 1.1

            efficiency = min(100, efficiency)
            effectiveness = min(100, effectiveness)
            impact = min(100, impact)

            efficiency_weighted += efficiency * weight
            effectiveness_weighted += effectiveness * weight
            impact_weighted += impact * weight
            total_weight += weight

            impact_details.append(
                {
                    "outcome_name": o["outcome_name"],
                    "target_value": target,
                    "actual_value": actual,
                    "achievement_ratio": round(achievement, 2),
                    "indicator_type": indicator_type,
                    "efficiency": round(efficiency, 2),
                    "effectiveness": round(effectiveness, 2),
                    "impact": round(impact, 2),
                    "weight": weight,
                }
            )

        eff_score = round(_safe_div(efficiency_weighted, total_weight, 0.0), 2)
        effcy_score = round(_safe_div(effectiveness_weighted, total_weight, 0.0), 2)
        imp_score = round(_safe_div(impact_weighted, total_weight, 0.0), 2)

        overall = round((eff_score * 0.3 + effcy_score * 0.35 + imp_score * 0.35), 2)
        rating = self._classify(overall)

        cost_effectiveness = None
        if budget_allocated and budget_spent and budget_spent > 0:
            cost_effectiveness = round(
                _safe_div(overall, budget_spent / budget_allocated, 0.0), 2
            )

        recommendations = self._recommendations(overall, outcomes)

        return {
            "program_name": program_name,
            "efficiency_score": eff_score,
            "effectiveness_score": effcy_score,
            "impact_score": imp_score,
            "overall_rbm_score": overall,
            "rbm_rating": rating,
            "outcome_details": impact_details,
            "cost_effectiveness": cost_effectiveness,
            "recommendations": recommendations,
        }

    @staticmethod
    def _classify(score: float) -> str:
        if score >= 85:
            return "HIGH_PERFORMING"
        if score >= 70:
            return "SATISFACTORY"
        if score >= 50:
            return "MODERATE"
        return "UNDERPERFORMING"

    @staticmethod
    def _recommendations(score: float, outcomes: List[Dict]) -> List[str]:
        recs = []
        underperforming = [
            o["outcome_name"]
            for o in outcomes
            if o["actual_value"] < o["target_value"] * 0.7
        ]
        if underperforming:
            recs.append(
                f"Focus on underperforming outcomes: {', '.join(underperforming)}"
            )
        if score < 50:
            recs.append("Consider restructuring the program logic model")
        below_target = sum(1 for o in outcomes if o["actual_value"] < o["target_value"])
        if below_target > len(outcomes) * 0.5:
            recs.append(
                "More than half of outcomes are below target; review resource allocation"
            )
        if not recs:
            recs.append("Program is performing well; maintain current approach")
        return recs


# =============================================================================
# Aggregate Service
# =============================================================================


class StrategicPerformanceService:
    """Unified service coordinating all 15 technique engines."""

    def __init__(self):
        self.bsc = BSCEngine()
        self.efqm = EFQMEngine()
        self.tqm = TQMEngine()
        self.kpi = KPIFrameworkEngine()
        self.dashboard = DashboardEngine()
        self.benchmarking = BenchmarkingEngine()
        self.strategy_map = StrategyMapEngine()
        self.contract = PerformanceContractEngine()
        self.okr = OKRCascadingEngine()
        self.review = PerformanceReviewEngine()
        self.gap = GapAnalysisEngine()
        self.improvement = ImprovementPlanEngine()
        self.bsc_variance = BSCVarianceEngine()
        self.measurement_system = MeasurementSystemEngine()
        self.rbm = RBMEngine()
