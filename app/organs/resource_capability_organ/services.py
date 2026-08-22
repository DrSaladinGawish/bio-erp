"""
Resource & Capability Analysis Services — 8 Techniques with Real Business Logic
BIO-ERP v5.3.0 — resource_capability_organ

All engines are stateless (static methods only). Each analyze() returns:
    {"result": {...}, "interpretation": {...}}
"""

import math
from typing import ClassVar

# =============================================================================
# 1. VRIO FRAMEWORK (Barney)
# =============================================================================


class VRIOEngine:
    """Value / Rarity / Imitability / Organization classification."""

    THRESHOLD: ClassVar[float] = 5.0
    WEIGHTS: ClassVar[dict] = {
        "value": 0.35,
        "rarity": 0.25,
        "imitability": 0.25,
        "organization": 0.15,
    }

    @staticmethod
    def classify(
        value: float, rarity: float, imitability: float, organization: float
    ) -> dict:
        t = VRIOEngine.THRESHOLD
        if value < t:
            cls = "COMPETITIVE_DISADVANTAGE"
        elif rarity < t:
            cls = "COMPETITIVE_PARITY"
        elif imitability < t and organization >= t:
            cls = "TEMPORARY_COMPETITIVE_ADVANTAGE"
        elif organization < t:
            cls = "UNUSED_COMPETITIVE_ADVANTAGE"
        else:
            cls = "SUSTAINED_COMPETITIVE_ADVANTAGE"

        implications = {
            "COMPETITIVE_DISADVANTAGE": "Resource is below competitive threshold — restructure, divest or exit dependence on it.",
            "COMPETITIVE_PARITY": "Valuable but widely held — no advantage; use it efficiently as a baseline capability.",
            "TEMPORARY_COMPETITIVE_ADVANTAGE": "Currently advantaging but imitable — raise imitation barriers (complexity, path dependency) fast.",
            "UNUSED_COMPETITIVE_ADVANTAGE": "Strong potential unrealized — fix organizational alignment to exploit the resource.",
            "SUSTAINED_COMPETITIVE_ADVANTAGE": "Passes all four VRIO tests — protect, deepen and build strategy around this resource.",
        }
        return {
            "classification": cls,
            "strategic_implication": implications[cls],
        }

    @staticmethod
    def investment_priority(classification: str, vrio_index: float) -> str:
        base = {
            "COMPETITIVE_DISADVANTAGE": "HIGH",
            "COMPETITIVE_PARITY": "MEDIUM",
            "TEMPORARY_COMPETITIVE_ADVANTAGE": "HIGH",
            "UNUSED_COMPETITIVE_ADVANTAGE": "CRITICAL",
            "SUSTAINED_COMPETITIVE_ADVANTAGE": "PROTECT",
        }[classification]
        if base in ("MEDIUM",) and vrio_index >= 6.5:
            return "HIGH"
        if base == "PROTECT" and vrio_index < 7.5:
            return "HIGH"
        return base

    @staticmethod
    def weakest_link(scores: dict) -> str:
        return min(scores, key=scores.get)

    @staticmethod
    def analyze(resources: list) -> dict:
        results = []
        counts = {}
        for r in resources:
            scores = {
                "value": r["value_score"],
                "rarity": r["rarity_score"],
                "imitability": r["imitability_cost"],
                "organization": r["organization_score"],
            }
            vrio_index = round(
                sum(scores[k] * w for k, w in VRIOEngine.WEIGHTS.items()), 2
            )
            outcome = VRIOEngine.classify(**scores)
            priority = VRIOEngine.investment_priority(
                outcome["classification"], vrio_index
            )
            wl = VRIOEngine.weakest_link(scores)

            next_step = {
                "COMPETITIVE_DISADVANTAGE": f"Increase VALUE above 5 (currently {scores['value']}) — link to real customer needs.",
                "COMPETITIVE_PARITY": f"Increase RARITY above 5 (currently {scores['rarity']}) — differentiate or acquire exclusivity.",
                "TEMPORARY_COMPETITIVE_ADVANTAGE": f"Raise IMITABILITY COST above 5 (currently {scores['imitability']}) — add causal ambiguity and path dependency.",
                "UNUSED_COMPETITIVE_ADVANTAGE": f"Strengthen ORGANIZATION above 5 (currently {scores['organization']}) — structures, processes and incentives to capture value.",
                "SUSTAINED_COMPETITIVE_ADVANTAGE": "Maintain barriers; monitor substitution threats annually.",
            }[outcome["classification"]]

            results.append(
                {
                    "name": r["name"],
                    **{k: v for k, v in scores.items()},
                    "vrio_index": vrio_index,
                    "classification": outcome["classification"],
                    "strategic_implication": outcome["strategic_implication"],
                    "investment_priority": priority,
                    "weakest_vrio_dimension": wl,
                    "next_ladder_step": next_step,
                }
            )
            counts[outcome["classification"]] = (
                counts.get(outcome["classification"], 0) + 1
            )

        n = len(results)
        avg_index = round(sum(x["vrio_index"] for x in results) / n, 2) if n else 0.0
        sustained = counts.get("SUSTAINED_COMPETITIVE_ADVANTAGE", 0)
        disadv = counts.get("COMPETITIVE_DISADVANTAGE", 0)
        if sustained >= max(1, n // 2):
            posture = "ADVANTAGE-RICH PORTFOLIO"
        elif sustained > 0:
            posture = "SELECTIVE ADVANTAGE"
        elif disadv >= n / 2:
            posture = "DISADVANTAGED PORTFOLIO"
        else:
            posture = "PARITY-DOMINATED PORTFOLIO"

        critical = [
            x for x in results if x["investment_priority"] in ("CRITICAL", "HIGH")
        ]
        critical.sort(
            key=lambda x: (
                -{"CRITICAL": 3, "HIGH": 2}.get(x["investment_priority"], 1),
                x["vrio_index"],
            )
        )

        result = {
            "resources": results,
            "portfolio_summary": {
                "total_resources": n,
                "classification_counts": counts,
                "average_vrio_index": avg_index,
                "competitive_posture": posture,
            },
            "investment_priority_ranking": [
                {
                    "name": x["name"],
                    "priority": x["investment_priority"],
                    "vrio_index": x["vrio_index"],
                }
                for x in critical
            ],
        }
        interpretation = {
            "summary": (
                f"{n} resources assessed: {sustained} sustained advantage(s), "
                f"{counts.get('TEMPORARY_COMPETITIVE_ADVANTAGE', 0)} temporary, "
                f"{counts.get('UNUSED_COMPETITIVE_ADVANTAGE', 0)} unused, "
                f"{counts.get('COMPETITIVE_PARITY', 0)} parity, {disadv} disadvantage. "
                f"Overall posture: {posture} (avg VRIO index {avg_index}/10)."
            ),
            "key_findings": [
                *(
                    f"'{x['name']}' is an UNUSED competitive advantage — highest-priority fix is organizational."
                    for x in results
                    if x["classification"] == "UNUSED_COMPETITIVE_ADVANTAGE"
                ),
                *(
                    f"'{x['name']}' sustains advantage — anchor strategy on it."
                    for x in results
                    if x["classification"] == "SUSTAINED_COMPETITIVE_ADVANTAGE"
                ),
                *(
                    f"'{x['name']}' is a competitive disadvantage — restructure or divest."
                    for x in results
                    if x["classification"] == "COMPETITIVE_DISADVANTAGE"
                ),
            ][:5],
            "recommendations": [
                f"Invest first in '{critical[0]['name']}' ({critical[0]['investment_priority']} priority)"
                if critical
                else "No high-priority investments flagged; maintain current positions.",
                "Re-run VRIO after major strategic moves; advantages erode as rivals imitate.",
            ],
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 2. VALUE CHAIN ANALYSIS (Porter)
# =============================================================================


class ValueChainEngine:
    """Primary + support activity cost/value decomposition."""

    PRIMARY_KEYS: ClassVar[list] = [
        "inbound_logistics",
        "operations",
        "outbound_logistics",
        "marketing",
        "service",
    ]
    SUPPORT_KEYS: ClassVar[list] = [
        "firm_infrastructure",
        "hr",
        "tech_development",
        "procurement",
    ]
    COST_CONCENTRATION_PCT: ClassVar[float] = 30.0

    @staticmethod
    def _activity_rows(
        activities: dict, keys: list, total_cost: float, total_value: float
    ) -> list:
        rows = []
        for key in keys:
            a = activities.get(key)
            if a is None:
                continue
            cost_share = (a["cost"] / total_cost * 100) if total_cost > 0 else 0.0
            value_share = (
                (a["value_score"] / total_value * 100) if total_value > 0 else 0.0
            )
            vc_ratio = (
                (a["value_score"] * 1000 / a["cost"]) if a["cost"] > 0 else float("inf")
            )
            rows.append(
                {
                    "activity": key,
                    "cost": round(a["cost"], 4),
                    "cost_share_pct": round(cost_share, 2),
                    "value_score": a["value_score"],
                    "value_share_pct": round(value_share, 2),
                    "value_per_cost_k": round(vc_ratio, 4)
                    if not math.isinf(vc_ratio)
                    else None,
                }
            )
        return rows

    @staticmethod
    def _assign_role(row: dict) -> str:
        cs, vs = row["cost_share_pct"], row["value_share_pct"]
        if cs >= ValueChainEngine.COST_CONCENTRATION_PCT and vs < 20:
            return "COST_DRIVER_OPTIMIZATION_TARGET"
        if vs >= 20 and cs <= 15:
            return "DIFFERENTIATION_LEVER"
        if vs >= 20 and cs >= ValueChainEngine.COST_CONCENTRATION_PCT:
            return "STRATEGIC_INVESTMENT_AREA"
        if vs < 10:
            return "UNDERPERFORMING"
        return "BALANCED"

    @staticmethod
    def analyze(primary_activities: dict, support_activities: dict) -> dict:
        all_acts = {**primary_activities, **support_activities}
        total_cost = sum(a["cost"] for a in all_acts.values())
        total_value = sum(a["value_score"] for a in all_acts.values())

        primary_rows = ValueChainEngine._activity_rows(
            primary_activities, ValueChainEngine.PRIMARY_KEYS, total_cost, total_value
        )
        support_rows = ValueChainEngine._activity_rows(
            support_activities, ValueChainEngine.SUPPORT_KEYS, total_cost, total_value
        )
        for row in primary_rows + support_rows:
            row["role"] = ValueChainEngine._assign_role(row)

        primary_cost = sum(r["cost"] for r in primary_rows)
        support_cost = sum(r["cost"] for r in support_rows)
        primary_value_pts = sum(r["value_score"] for r in primary_rows)
        support_value_pts = sum(r["value_score"] for r in support_rows)

        roles = {}
        for row in primary_rows + support_rows:
            roles.setdefault(row["role"], []).append(row["activity"])

        optimization = []
        for row in primary_rows + support_rows:
            if row["role"] == "COST_DRIVER_OPTIMIZATION_TARGET":
                optimization.append(
                    f"'{row['activity']}' consumes {row['cost_share_pct']}% of chain cost but delivers only "
                    f"{row['value_share_pct']}% of value — primary cost-reduction target."
                )
            elif row["role"] == "DIFFERENTIATION_LEVER":
                optimization.append(
                    f"'{row['activity']}' delivers {row['value_share_pct']}% of value at {row['cost_share_pct']}% "
                    f"of cost — invest here for differentiation."
                )
            elif row["role"] == "STRATEGIC_INVESTMENT_AREA":
                optimization.append(
                    f"'{row['activity']}' is both costly ({row['cost_share_pct']}%) and high-value "
                    f"({row['value_share_pct']}%) — manage carefully; partial outsourcing may free capital."
                )
            elif row["role"] == "UNDERPERFORMING":
                optimization.append(
                    f"'{row['activity']}' contributes little value ({row['value_share_pct']}%) — "
                    f"restructure, automate or outsource."
                )

        result = {
            "activities": {"primary": primary_rows, "support": support_rows},
            "totals": {
                "total_chain_cost": round(total_cost, 4),
                "primary_cost": round(primary_cost, 4),
                "support_cost": round(support_cost, 4),
                "support_cost_share_pct": round(support_cost / total_cost * 100, 2)
                if total_cost
                else 0,
                "total_value_points": round(total_value, 2),
                "primary_value_points": round(primary_value_pts, 2),
                "support_value_points": round(support_value_pts, 2),
                "chain_efficiency_points_per_million": (
                    round(total_value / total_cost * 1_000_000, 2)
                    if total_cost > 0
                    else None
                ),
            },
            "role_map": roles,
            "optimization_targets": optimization,
        }

        top_cost = max(
            (r for r in primary_rows + support_rows),
            key=lambda r: r["cost"],
            default=None,
        )
        top_value = max(
            (r for r in primary_rows + support_rows),
            key=lambda r: r["value_share_pct"],
            default=None,
        )
        interpretation = {
            "summary": (
                f"Chain totals {round(total_cost, 2)} in cost across 9 activities; support activities absorb "
                f"{round(support_cost / total_cost * 100, 1) if total_cost else 0}% of spend. "
                f"Highest-cost activity: '{top_cost['activity']}' ({top_cost['cost_share_pct']}%). "
                f"Largest value contributor: '{top_value['activity']}' ({top_value['value_share_pct']}%)."
            )
            if top_cost and top_value
            else "Insufficient activity data.",
            "key_findings": [
                *(f"Role assignment: {', '.join(v)} → {k}" for k, v in roles.items()),
            ][:5],
            "recommendations": optimization[:5]
            or [
                "No structural imbalance detected; benchmark costs against industry peers annually."
            ],
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 3. CORE COMPETENCY ASSESSMENT (Prahalad & Hamel)
# =============================================================================


class CoreCompetencyEngine:
    """Three-tests core competency evaluation with building trajectory."""

    TEST_THRESHOLD: ClassVar[float] = 6.0
    WEIGHTS: ClassVar[dict] = {
        "customer_value": 0.35,
        "market_access": 0.25,
        "imitation_barrier": 0.25,
        "depth": 0.15,
    }

    @staticmethod
    def three_tests(c: dict) -> dict:
        return {
            "customer_value_test": c["customer_value"],
            "market_access_test": c["potential_for_leverage"],
            "imitation_barrier_test": round(
                (c["competitor_rarity"] + c["depth_score"]) / 2, 2
            ),
        }

    @staticmethod
    def classify(tests: dict) -> str:
        passed = sum(
            1 for v in tests.values() if v >= CoreCompetencyEngine.TEST_THRESHOLD
        )
        if passed == 3:
            return "CORE"
        if passed == 2:
            return "EMERGING_CORE"
        if passed == 1:
            return "NEAR_CORE"
        return "BASIC"

    @staticmethod
    def trajectory(current_depth: float, target: float, quarters: int) -> list:
        """Diminishing-returns competence-building path toward target depth."""
        path = []
        k = 0.25
        for q in range(quarters + 1):
            level = target - (target - current_depth) * math.exp(-k * q)
            path.append(
                {
                    "quarter": q,
                    "projected_depth": round(level, 2),
                    "gap_closed_pct": round(
                        ((level - current_depth) / (target - current_depth) * 100)
                        if target > current_depth
                        else 100,
                        1,
                    ),
                }
            )
        return path

    @staticmethod
    def tree_mapping(comp: dict, tests: dict, classification: str) -> dict:
        """Competency tree: root competence with market branches enabled by leverage."""
        leverage = comp["potential_for_leverage"]
        branch_count = max(1, min(5, int(leverage // 2)))
        strength = (
            "STRONG_TRUNK"
            if leverage >= 7
            else ("GROWING_BRANCH" if leverage >= 5 else "THIN_SHOOT")
        )
        branches = [
            {
                "market_segment": f"Segment enabled via leverage {i + 1}",
                "reach_strength": strength,
            }
            for i in range(branch_count)
        ]
        return {
            "root_competency": comp["name"],
            "classification": classification,
            "trunk_health": round(sum(tests.values()) / 3, 2),
            "branches": branches,
        }

    @staticmethod
    def analyze(competencies: list, horizon_quarters: int = 8) -> dict:
        results = []
        for c in competencies:
            tests = CoreCompetencyEngine.three_tests(c)
            core_score = round(
                tests["customer_value_test"]
                * CoreCompetencyEngine.WEIGHTS["customer_value"]
                + tests["market_access_test"]
                * CoreCompetencyEngine.WEIGHTS["market_access"]
                + tests["imitation_barrier_test"]
                * CoreCompetencyEngine.WEIGHTS["imitation_barrier"]
                + c["depth_score"] * CoreCompetencyEngine.WEIGHTS["depth"],
                2,
            )
            classification = CoreCompetencyEngine.classify(tests)
            weakest_test = min(tests, key=tests.get)

            priority = {
                "CORE": "PROTECT_DEEPEN",
                "EMERGING_CORE": "HIGH",
                "NEAR_CORE": "MEDIUM",
                "BASIC": "LOW",
            }[classification]
            if classification == "BASIC" and core_score >= 4.5:
                priority = "MEDIUM"

            results.append(
                {
                    "name": c["name"],
                    "tests": tests,
                    "core_score": core_score,
                    "classification": classification,
                    "weakest_test": weakest_test,
                    "investment_priority": priority,
                    "tree": CoreCompetencyEngine.tree_mapping(c, tests, classification),
                    "building_trajectory": CoreCompetencyEngine.trajectory(
                        c["depth_score"], 9.0, horizon_quarters
                    ),
                }
            )

        n = len(results)
        core_count = sum(1 for r in results if r["classification"] == "CORE")
        ranking = sorted(results, key=lambda r: -r["core_score"])

        result = {
            "competencies": results,
            "summary": {
                "total_assessed": n,
                "core_count": core_count,
                "emerging_core_count": sum(
                    1 for r in results if r["classification"] == "EMERGING_CORE"
                ),
                "average_core_score": round(
                    sum(r["core_score"] for r in results) / n, 2
                )
                if n
                else 0,
                "competency_ranking": [r["name"] for r in ranking],
            },
        }
        interpretation = {
            "summary": (
                f"{core_count}/{n} competencies pass all three Prahalad-Hamel tests (CORE). "
                f"Top competency: '{ranking[0]['name']}' (score {ranking[0]['core_score']})."
            )
            if n
            else "No competencies assessed.",
            "key_findings": [
                *(
                    f"'{r['name']}' is CORE — it should anchor corporate strategy and never be outsourced."
                    for r in results
                    if r["classification"] == "CORE"
                ),
                *(
                    f"'{r['name']}' fails mainly on {r['weakest_test']} — targeted investment closes the gap fastest there."
                    for r in results
                    if r["classification"] in ("EMERGING_CORE", "NEAR_CORE")
                ),
            ][:5],
            "recommendations": [
                *(
                    f"Protect & deepen '{r['name']}': allocate ≥40% of competence budget, guard key people."
                    for r in results
                    if r["classification"] == "CORE"
                ),
                *(
                    f"Build '{r['name']}' along the projected trajectory to reach depth 9 within {horizon_quarters} quarters."
                    for r in results
                    if r["classification"] == "EMERGING_CORE"
                ),
            ][:5]
            or ["Develop at least one candidate competency toward CORE status."],
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 4. DYNAMIC CAPABILITIES (Teece)
# =============================================================================


class DynamicCapabilitiesEngine:
    """Sensing → Seizing → Reconfiguring pipeline assessment."""

    MATURITY_BANDS: ClassVar[list] = [
        (4.0, "EMERGING"),
        (6.0, "DEVELOPING"),
        (8.0, "PROFICIENT"),
    ]

    RECOMMENDATIONS: ClassVar[dict] = {
        "sensing": [
            "Institute systematic market-intelligence scanning (quarterly opportunity reviews).",
            "Stand up a technology-watch function tracking adjacent-industry disruption signals.",
        ],
        "seizing": [
            "Delegate investment authority with pre-approved thresholds to cut decision latency.",
            "Create a rapid resource-mobilization playbook (cross-functional teams, staged funding).",
        ],
        "reconfiguring": [
            "Adopt modular org design so assets/processes can be recombined quickly.",
            "Fund deliberate learning loops (post-mortems, experimentation budget) to raise learning rate.",
        ],
    }

    @staticmethod
    def maturity_label(score: float) -> str:
        for bound, label in DynamicCapabilitiesEngine.MATURITY_BANDS:
            if score < bound:
                return label
        return "WORLD_CLASS"

    @staticmethod
    def analyze(sensing: dict, seizing: dict, reconfiguring: dict) -> dict:
        sensing_score = round(
            (sensing["market_awareness"] + sensing["technology_scanning"]) / 2, 2
        )
        seizing_score = round(
            (seizing["decision_speed"] + seizing["resource_mobilization"]) / 2, 2
        )
        reconfiguring_score = round(
            (
                reconfiguring["organizational_flexibility"]
                + reconfiguring["learning_rate"]
            )
            / 2,
            2,
        )
        overall = round((sensing_score + seizing_score + reconfiguring_score) / 3, 2)

        dims = {
            "sensing": sensing_score,
            "seizing": seizing_score,
            "reconfiguring": reconfiguring_score,
        }
        spread = round(max(dims.values()) - min(dims.values()), 2)
        balance = (
            "BALANCED"
            if spread <= 1.5
            else ("MODERATELY_BALANCED" if spread <= 3.0 else "IMBALANCED")
        )
        bottleneck = min(dims, key=dims.get)
        maturity = DynamicCapabilitiesEngine.maturity_label(overall)

        # Sequential pipeline risk: a weak upstream stage starves downstream stages.
        pipeline_risk = []
        ordered = ["sensing", "seizing", "reconfiguring"]
        for i, stage in enumerate(ordered):
            if dims[stage] < 5.0:
                downstream = ordered[i + 1 :]
                pipeline_risk.append(
                    {
                        "stage": stage,
                        "score": dims[stage],
                        "starves": downstream,
                        "severity": "HIGH" if dims[stage] < 3.5 else "MODERATE",
                    }
                )

        improvements = []
        for name, score in sorted(dims.items(), key=lambda kv: kv[1]):
            gap_actions = DynamicCapabilitiesEngine.RECOMMENDATIONS[name]
            improvements.append(
                {
                    "dimension": name,
                    "current_score": score,
                    "target_score": min(10.0, score + 2.0),
                    "actions": gap_actions,
                }
            )

        sub_detail = {
            "sensing": sensing,
            "seizing": seizing,
            "reconfiguring": reconfiguring,
        }

        result = {
            "dimension_scores": dims,
            "sub_capabilities": sub_detail,
            "dynamic_capability_score": overall,
            "maturity": maturity,
            "balance": {
                "spread": spread,
                "status": balance,
                "strongest": max(dims, key=dims.get),
                "bottleneck": bottleneck,
            },
            "pipeline_risks": pipeline_risk,
            "improvement_plan": improvements,
        }
        interpretation = {
            "summary": (
                f"Dynamic capability score {overall}/10 ({maturity}). Dimensions are {balance.lower()} "
                f"(spread {spread}); '{bottleneck}' is the binding constraint on the Teece pipeline."
            ),
            "key_findings": [
                *(
                    f"Weak {p['stage']} stage ({p['score']}) starves {' and '.join(p['starves'])}."
                    for p in pipeline_risk
                ),
                f"Strongest dimension: '{max(dims, key=dims.get)}' at {max(dims.values())}.",
            ],
            "recommendations": [
                (
                    f"Prioritize '{bottleneck}' investment — dynamic capabilities are sequential; "
                    f"strengthening the bottleneck unlocks the whole chain."
                ),
                *(a for imp in improvements[:1] for a in imp["actions"]),
            ],
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 5. RESOURCE AUDIT
# =============================================================================


class ResourceAuditEngine:
    """Tangible / intangible / human resource inventory valuation."""

    PROTECTION_MULTIPLIERS: ClassVar[dict] = {
        "REGISTERED": 1.20,
        "HIGH": 1.15,
        "MEDIUM": 1.00,
        "LOW": 0.70,
        "NONE": 0.40,
    }
    AGING_REPLACEMENT_RATIO: ClassVar[float] = 1.5
    UNDERUTILIZATION_EXPERIENCE_YRS: ClassVar[float] = 2.0

    @staticmethod
    def audit_tangibles(items: list) -> dict:
        rows, flags = [], []
        total_book, total_replacement = 0.0, 0.0
        for t in items:
            projected = t["current_value"] * (1 - t["depreciation_rate_pct"] / 100)
            ratio = (
                (t["replacement_cost"] / t["current_value"])
                if t["current_value"] > 0
                else None
            )
            item_flags = []
            if (
                ratio is not None
                and ratio >= ResourceAuditEngine.AGING_REPLACEMENT_RATIO
            ):
                item_flags.append("AGING_HIGH_REPLACEMENT_COST")
            if t["depreciation_rate_pct"] >= 25:
                item_flags.append("RAPID_DEPRECIATION")
            rows.append(
                {
                    "type": t["type"],
                    "current_value": round(t["current_value"], 4),
                    "projected_value_next_year": round(projected, 4),
                    "depreciation_rate_pct": t["depreciation_rate_pct"],
                    "replacement_cost": round(t["replacement_cost"], 4),
                    "replacement_ratio": round(ratio, 3) if ratio is not None else None,
                    "flags": item_flags,
                }
            )
            if item_flags:
                flags.append(
                    {"category": "TANGIBLE", "item": t["type"], "flags": item_flags}
                )
            total_book += t["current_value"]
            total_replacement += t["replacement_cost"]
        return {
            "items": rows,
            "total_current_value": round(total_book, 4),
            "total_projected_value_next_year": round(
                sum(r["projected_value_next_year"] for r in rows), 4
            ),
            "total_replacement_cost": round(total_replacement, 4),
            "flags": flags,
        }

    @staticmethod
    def audit_intangibles(items: list) -> dict:
        rows, flags = [], []
        total_raw, total_protected = 0.0, 0.0
        for i in items:
            mult = ResourceAuditEngine.PROTECTION_MULTIPLIERS[i["legal_protection"]]
            protected = i["estimated_value"] * mult
            item_flags = []
            if i["legal_protection"] in ("NONE", "LOW"):
                item_flags.append(
                    f"UNPROTECTED_VALUE_AT_RISK_{round(i['estimated_value'] * (1 - mult), 2)}"
                )
            rows.append(
                {
                    "type": i["type"],
                    "estimated_value": round(i["estimated_value"], 4),
                    "legal_protection": i["legal_protection"],
                    "protection_multiplier": mult,
                    "risk_adjusted_value": round(protected, 4),
                    "flags": item_flags,
                }
            )
            if item_flags:
                flags.append(
                    {"category": "INTANGIBLE", "item": i["type"], "flags": item_flags}
                )
            total_raw += i["estimated_value"]
            total_protected += protected
        return {
            "items": rows,
            "total_estimated_value": round(total_raw, 4),
            "total_risk_adjusted_value": round(total_protected, 4),
            "value_at_risk": round(total_raw - total_protected, 4),
            "flags": flags,
        }

    @staticmethod
    def audit_human(items: list) -> dict:
        rows, flags = [], []
        total_capacity, weighted_experience = 0.0, 0.0
        headcount_total = 0
        skill_holders = {}
        for h in items:
            capacity = h["headcount"] * h["experience_years"] * h["criticality"]
            skill_holders.setdefault(h["skills"], 0)
            skill_holders[h["skills"]] += h["headcount"]
            item_flags = []
            if (
                h["experience_years"]
                <= ResourceAuditEngine.UNDERUTILIZATION_EXPERIENCE_YRS
                and h["criticality"] >= 7
            ):
                item_flags.append("JUNIOR_TEAM_ON_CRITICAL_SKILL")
            if h["headcount"] == 1 and h["criticality"] >= 8:
                item_flags.append("KEY_PERSON_RISK")
            rows.append(
                {
                    "skills": h["skills"],
                    "headcount": h["headcount"],
                    "experience_years": h["experience_years"],
                    "criticality": h["criticality"],
                    "capacity_units": round(capacity, 2),
                    "flags": item_flags,
                }
            )
            if item_flags:
                flags.append(
                    {"category": "HUMAN", "item": h["skills"], "flags": item_flags}
                )
            total_capacity += capacity
            weighted_experience += h["experience_years"] * h["headcount"]
            headcount_total += h["headcount"]

        single_point_skills = [s for s, cnt in skill_holders.items() if cnt == 1]
        if single_point_skills:
            flags.append(
                {
                    "category": "HUMAN",
                    "item": ", ".join(single_point_skills),
                    "flags": ["SINGLE_HOLDER_SKILL_NO_REDUNDANCY"],
                }
            )

        return {
            "items": rows,
            "total_headcount": headcount_total,
            "avg_experience_years": round(weighted_experience / headcount_total, 2)
            if headcount_total
            else 0,
            "total_capacity_units": round(total_capacity, 2),
            "flags": flags,
        }

    @staticmethod
    def analyze(tangible: list, intangible: list, human: list) -> dict:
        tan = ResourceAuditEngine.audit_tangibles(tangible)
        intan = ResourceAuditEngine.audit_intangibles(intangible)
        hum = ResourceAuditEngine.audit_human(human)

        portfolio_value = round(
            tan["total_current_value"]
            + intan["total_risk_adjusted_value"]
            + hum["total_capacity_units"],
            4,
        )
        category_values = {
            "tangible": tan["total_current_value"],
            "intangible_risk_adjusted": intan["total_risk_adjusted_value"],
            "human_capacity_units": hum["total_capacity_units"],
        }
        gaps = [k for k, v in category_values.items() if v == 0]

        priorities = []
        for f in intan["flags"]:
            priorities.append(
                f"Legally protect '{f['item']}' immediately — unprotected intangible value."
            )
        for f in tan["flags"]:
            if "AGING_HIGH_REPLACEMENT_COST" in f["flags"]:
                priorities.append(
                    f"Plan phased replacement of '{f['item']}' — replacement cost far exceeds book value."
                )
        for f in hum["flags"]:
            if (
                "KEY_PERSON_RISK" in f["flags"]
                or "SINGLE_HOLDER_SKILL_NO_REDUNDANCY" in f["flags"]
            ):
                priorities.append(
                    f"Build redundancy for '{f['item']}' — knowledge concentration risk."
                )

        result = {
            "tangible_audit": tan,
            "intangible_audit": intan,
            "human_audit": hum,
            "portfolio": {
                "total_portfolio_value": portfolio_value,
                "category_values": category_values,
                "identified_gaps": gaps,
                "all_flags": tan["flags"] + intan["flags"] + hum["flags"],
            },
            "action_priorities": priorities,
        }
        key_findings = [
            f"Gap detected: no {g.replace('_', ' ')} recorded in the audit."
            for g in gaps
        ]
        if intan["value_at_risk"] > 0:
            key_findings.append(
                f"Intangible value at risk from weak legal protection: {intan['value_at_risk']:,.0f}."
            )
        interpretation = {
            "summary": (
                f"Portfolio value ≈ {portfolio_value:,.0f} (tangible {tan['total_current_value']:,.0f}, "
                f"intangible risk-adjusted {intan['total_risk_adjusted_value']:,.0f}, "
                f"human capacity {hum['total_capacity_units']:,.0f} units). "
                f"{len(result['portfolio']['all_flags'])} risk flag(s) raised."
            ),
            "key_findings": key_findings,
            "recommendations": priorities[:5]
            or ["No critical flags; refresh the audit annually and after M&A events."],
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 6. CAPABILITY MAPPING (Heat Map + Build/Buy/Ally)
# =============================================================================


class CapabilityMappingEngine:
    """Importance-vs-proficiency heat map with sourcing decisions."""

    HIGH = 6.0

    @staticmethod
    def quadrant(importance: float, current: float) -> str:
        hi = CapabilityMappingEngine.HIGH
        if importance >= hi and current >= hi:
            return "CORE_STRENGTH"
        if importance >= hi and current < hi:
            return "CRITICAL_GAP"
        if importance < hi and current >= hi:
            return "NON_CRITICAL_STRENGTH"
        return "LOW_PRIORITY"

    @staticmethod
    def sourcing(
        quadrant: str, gap: float, investment: float, median_investment: float
    ) -> tuple:
        if quadrant == "CORE_STRENGTH":
            return (
                "BUILD",
                "Maintain leadership through continuous internal investment.",
            )
        if quadrant == "LOW_PRIORITY":
            return "MAINTAIN", "Adequate for needs; minimal incremental spend."
        if quadrant == "NON_CRITICAL_STRENGTH":
            return (
                "ALLY_OR_OUTSOURCE",
                "Strength exceeds strategic need — monetize via partnership or outsource to cut cost.",
            )
        # CRITICAL_GAP
        if gap <= 2.0:
            return (
                "BUILD",
                "Small gap — internal development is fastest and lowest-risk route.",
            )
        if gap >= 5.0:
            return (
                "BUY",
                "Large gap — acquisition brings proven capability faster than organic build.",
            )
        if median_investment > 0 and investment <= median_investment:
            return (
                "BUILD",
                "Moderate gap with affordable investment — build internally.",
            )
        return (
            "ALLY",
            "Moderate-to-large gap with heavy investment — share risk via alliance/partnership.",
        )

    @staticmethod
    def heat_cell(level: float, importance: float) -> dict:
        """Map to a 5x5 grid cell (levels/importance bucketed 1-2-3-4-5+ ... 10 scale)."""

        def bucket(v: float) -> int:
            return min(5, max(1, math.ceil(v / 2)))

        return {
            "proficiency_bucket": bucket(level),
            "importance_bucket": bucket(importance),
        }

    @staticmethod
    def analyze(capabilities: list) -> dict:
        investments = [
            c["investment_required"]
            for c in capabilities
            if c["investment_required"] > 0
        ]
        median_inv = sorted(investments)[len(investments) // 2] if investments else 0.0

        rows = []
        for c in capabilities:
            gap = round(max(0.0, c["strategic_importance"] - c["current_level"]), 2)
            q = CapabilityMappingEngine.quadrant(
                c["strategic_importance"], c["current_level"]
            )
            rec, rationale = CapabilityMappingEngine.sourcing(
                q, gap, c["investment_required"], median_inv
            )
            row = {
                "name": c["name"],
                "current_level": c["current_level"],
                "strategic_importance": c["strategic_importance"],
                "gap": gap,
                "investment_required": c["investment_required"],
                "quadrant": q,
                "sourcing_recommendation": rec,
                "rationale": rationale,
                **CapabilityMappingEngine.heat_cell(
                    c["current_level"], c["strategic_importance"]
                ),
            }
            rows.append(row)

        quadrants = {}
        for r in rows:
            quadrants.setdefault(r["quadrant"], []).append(r["name"])

        critical = [r for r in rows if r["quadrant"] == "CRITICAL_GAP"]
        critical.sort(
            key=lambda r: (
                -(r["gap"] * r["strategic_importance"]),
                r["investment_required"],
            )
        )
        for i, r in enumerate(critical, 1):
            r["priority_rank"] = i

        total_investment_needed = sum(r["investment_required"] for r in critical)

        result = {
            "heat_map": [
                {
                    "name": r["name"],
                    "proficiency_bucket": r["proficiency_bucket"],
                    "importance_bucket": r["importance_bucket"],
                    "quadrant": r["quadrant"],
                }
                for r in rows
            ],
            "capabilities": rows,
            "quadrant_distribution": quadrants,
            "critical_gaps_ranked": [
                {
                    "rank": r["priority_rank"],
                    "name": r["name"],
                    "gap": r["gap"],
                    "sourcing": r["sourcing_recommendation"],
                    "investment_required": r["investment_required"],
                }
                for r in critical
            ],
            "total_investment_for_critical_gaps": round(total_investment_needed, 4),
        }
        if critical:
            sourcing_mix = ", ".join(
                f"'{r['name']}'→{r['sourcing_recommendation']}" for r in critical
            )
            summary = (
                f"{len(rows)} capabilities mapped: {len(quadrants.get('CORE_STRENGTH', []))} core strengths, "
                f"{len(critical)} critical gaps requiring {total_investment_needed:,.0f} investment. "
                f"Sourcing mix: {sourcing_mix}."
            )
        else:
            summary = f"{len(rows)} capabilities mapped; no critical gaps identified."
        interpretation = {
            "summary": summary,
            "key_findings": [
                *(
                    f"'{n}' is a core strength — defend it."
                    for n in quadrants.get("CORE_STRENGTH", [])
                ),
                *(
                    f"'{n}' over-invested relative to strategic need — ally/outsource candidate."
                    for n in quadrants.get("NON_CRITICAL_STRENGTH", [])
                ),
            ][:5],
            "recommendations": [
                *(
                    f"#{r['priority_rank']} close '{r['name']}' gap ({r['gap']} pts) via {r['sourcing_recommendation']}."
                    for r in critical[:5]
                ),
            ]
            or ["Maintain current capability portfolio; re-map when strategy shifts."],
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 7. KNOWLEDGE ASSETS ASSESSMENT (Intellectual Capital)
# =============================================================================


class KnowledgeAssetsEngine:
    """Human / Structural / Relational intellectual capital scoring."""

    HC_WEIGHT, SC_WEIGHT, RC_WEIGHT = 0.40, 0.30, 0.30
    INNOVATION_PER_EXPERT_REF = 2.0  # innovations per expert considered excellent
    PATENT_POINTS_PER_PATENT = 8.0
    PROCESS_POINTS_PER_PROCESS = 2.0
    DB_POINTS_PER_DATABASE = 5.0

    @staticmethod
    def human_capital_score(hc: dict) -> tuple:
        experts = hc["expertise_count"]
        innovation_intensity = hc["innovation_output"] / experts if experts > 0 else 0.0
        intensity_pts = min(
            100,
            innovation_intensity
            / KnowledgeAssetsEngine.INNOVATION_PER_EXPERT_REF
            * 100,
        )
        expertise_pts = hc["avg_expertise_level"] * 10  # 1-10 → 10-100
        retention_pts = 100 - hc["turnover_risk_pct"]  # low turnover = high score
        score = round(
            intensity_pts * 0.40 + expertise_pts * 0.35 + retention_pts * 0.25, 2
        )
        detail = {
            "innovation_intensity_per_expert": round(innovation_intensity, 3),
            "intensity_points": round(intensity_pts, 1),
            "expertise_points": round(expertise_pts, 1),
            "retention_points": round(retention_pts, 1),
        }
        return score, detail

    @staticmethod
    def structural_capital_score(sc: dict) -> tuple:
        pts = (
            min(60, sc["processes"] * KnowledgeAssetsEngine.PROCESS_POINTS_PER_PROCESS)
            + min(60, sc["patents"] * KnowledgeAssetsEngine.PATENT_POINTS_PER_PATENT)
            + min(40, sc["databases"] * KnowledgeAssetsEngine.DB_POINTS_PER_DATABASE)
        )
        maturity_mult = 0.5 + (sc["process_maturity"] / 10) * 0.5  # 0.5–1.0
        score = round(min(100, pts * maturity_mult), 2)
        detail = {
            "raw_inventory_points": round(pts, 1),
            "maturity_multiplier": round(maturity_mult, 3),
        }
        return score, detail

    @staticmethod
    def relational_capital_score(rc: dict) -> tuple:
        loyalty_pts = rc["customer_loyalty_pct"]  # 0-100 direct
        brand_pts = min(
            100, math.log10(rc["brand_value"] + 1) * 25
        )  # log-scaled brand value
        score = round(loyalty_pts * 0.60 + brand_pts * 0.40, 2)
        detail = {
            "loyalty_points": round(loyalty_pts, 1),
            "brand_points_log_scaled": round(brand_pts, 1),
        }
        return score, detail

    @staticmethod
    def valuation_tier(ic_index: float) -> str:
        if ic_index >= 80:
            return "KNOWLEDGE_LEADER"
        if ic_index >= 65:
            return "STRONG_IC"
        if ic_index >= 50:
            return "MODERATE_IC"
        if ic_index >= 35:
            return "DEVELOPING_IC"
        return "IC_DEFICIT"

    @staticmethod
    def analyze(
        human_capital: dict, structural_capital: dict, relational_capital: dict
    ) -> dict:
        hc_score, hc_detail = KnowledgeAssetsEngine.human_capital_score(human_capital)
        sc_score, sc_detail = KnowledgeAssetsEngine.structural_capital_score(
            structural_capital
        )
        rc_score, rc_detail = KnowledgeAssetsEngine.relational_capital_score(
            relational_capital
        )

        ic_index = round(
            hc_score * KnowledgeAssetsEngine.HC_WEIGHT
            + sc_score * KnowledgeAssetsEngine.SC_WEIGHT
            + rc_score * KnowledgeAssetsEngine.RC_WEIGHT,
            2,
        )
        sc_hc_ratio = round(sc_score / hc_score, 3) if hc_score > 0 else None

        pillar_scores = {
            "human": hc_score,
            "structural": sc_score,
            "relational": rc_score,
        }
        gaps = [
            {
                "pillar": p,
                "score": s,
                "severity": "CRITICAL"
                if s < 35
                else ("SIGNIFICANT" if s < 50 else "WATCH"),
            }
            for p, s in pillar_scores.items()
            if s < 50
        ]

        institutionalization = None
        if sc_hc_ratio is not None:
            if sc_hc_ratio >= 0.8:
                institutionalization = (
                    "INSTITUTIONALIZED — knowledge survives people leaving."
                )
            elif sc_hc_ratio >= 0.5:
                institutionalization = (
                    "PARTIALLY_CODED — capture more tacit knowledge into systems."
                )
            else:
                institutionalization = (
                    "PERSON_DEPENDENT — high flight risk; codify urgently."
                )

        indicative_valuation = round(
            relational_capital["brand_value"] * (ic_index / 100), 4
        )

        result = {
            "pillar_scores": pillar_scores,
            "pillar_details": {
                "human": hc_detail,
                "structural": sc_detail,
                "relational": rc_detail,
            },
            "ic_index": ic_index,
            "weights": {
                "human": KnowledgeAssetsEngine.HC_WEIGHT,
                "structural": KnowledgeAssetsEngine.SC_WEIGHT,
                "relational": KnowledgeAssetsEngine.RC_WEIGHT,
            },
            "sc_hc_ratio": sc_hc_ratio,
            "institutionalization_status": institutionalization,
            "valuation_tier": KnowledgeAssetsEngine.valuation_tier(ic_index),
            "indicative_brand_linked_valuation": indicative_valuation,
            "knowledge_gaps": gaps,
        }
        gap_actions = {
            "human": "launch expertise-development program and reduce turnover risk.",
            "structural": "codify processes, file patents, consolidate databases.",
            "relational": "invest in loyalty programs and brand-building initiatives.",
        }
        recommendations = [
            f"Close {g['pillar']}-capital gap: {gap_actions[g['pillar']]}" for g in gaps
        ] or [
            "Sustain IC position with annual re-assessment and knowledge-retention KPIs."
        ]
        key_findings = [
            f"{g['severity']} gap in {g['pillar']} capital (score {g['score']})."
            for g in gaps
        ]
        if institutionalization:
            key_findings.append(institutionalization)
        interpretation = {
            "summary": (
                f"Intellectual capital index {ic_index}/100 ({KnowledgeAssetsEngine.valuation_tier(ic_index)}). "
                f"Strongest pillar: '{max(pillar_scores, key=pillar_scores.get)}' "
                f"({max(pillar_scores.values())}); weakest: '{min(pillar_scores, key=pillar_scores.get)}' "
                f"({min(pillar_scores.values())})."
            ),
            "key_findings": key_findings,
            "recommendations": recommendations,
        }
        return {"result": result, "interpretation": interpretation}


# =============================================================================
# 8. OUTSOURCING ANALYSIS (Make/Buy/Ally Decision Matrix)
# =============================================================================


class OutsourcingEngine:
    """Risk-adjusted make/buy/ally decisioning with TCO."""

    RISK_PREMIUM_PCT: ClassVar[dict] = {"LOW": 0.05, "MEDIUM": 0.15, "HIGH": 0.30}
    MANAGEMENT_OVERHEAD_PCT: ClassVar[float] = (
        0.10  # vendor-management overhead on external cost
    )

    CORE_THRESHOLD: ClassVar[float] = 7.0
    COMMODITY_THRESHOLD: ClassVar[float] = 4.0

    @staticmethod
    def decide(
        strategic_importance: float,
        core_fit: float,
        savings_pct: float,
        risk_level: str,
    ) -> tuple:
        if (
            strategic_importance >= OutsourcingEngine.CORE_THRESHOLD
            and core_fit >= OutsourcingEngine.CORE_THRESHOLD
        ):
            return (
                "MAKE",
                "Activity is core and differentiating — keep in-house regardless of cost differential.",
            )

        if (
            strategic_importance <= OutsourcingEngine.COMMODITY_THRESHOLD
            and core_fit <= OutsourcingEngine.COMMODITY_THRESHOLD
        ):
            if savings_pct > 0:
                return (
                    "BUY",
                    "Non-core commodity activity with positive savings — outsource to a capable vendor.",
                )
            return (
                "MAKE",
                "Non-core but outsourcing does not save money — retain until economics improve.",
            )

        # Middle zone
        if risk_level == "HIGH":
            return (
                "ALLY",
                "Strategically sensitive middle-zone activity — share risk via alliance/JV rather than full buy.",
            )
        if savings_pct >= 25:
            return (
                "BUY",
                "Meaningful savings on non-differentiating work — structured outsourcing with SLAs.",
            )
        if core_fit >= 6:
            return (
                "ALLY",
                "Partial capability fit — partner to access skills while retaining internal kernel.",
            )
        return (
            "MAKE",
            "Cost savings do not justify loss of control in this middle zone.",
        )

    @staticmethod
    def tco(
        external_cost: float, transition_cost: float, years: int, risk_level: str
    ) -> dict:
        premium_pct = OutsourcingEngine.RISK_PREMIUM_PCT[risk_level]
        annual_premium = external_cost * premium_pct
        overhead = external_cost * OutsourcingEngine.MANAGEMENT_OVERHEAD_PCT
        multi_year_external = (external_cost + annual_premium + overhead) * years
        total = multi_year_external + transition_cost
        return {
            "annual_vendor_cost": round(external_cost, 4),
            "annual_risk_premium": round(annual_premium, 4),
            "annual_management_overhead": round(overhead, 4),
            "transition_cost_one_off": round(transition_cost, 4),
            "multi_year_tco": round(total, 4),
            "tco_per_year": round(total / years, 4) if years else 0.0,
        }

    @staticmethod
    def analyze(activities: list, contract_years: int = 3) -> dict:
        rows = []
        for a in activities:
            cc = a["cost_comparison"]
            internal, external = cc["internal_cost"], cc["external_cost"]
            savings = round(internal - external, 4)
            savings_pct = round(savings / internal * 100, 2) if internal > 0 else 0.0

            recommendation, rationale = OutsourcingEngine.decide(
                a["strategic_importance"],
                a["core_competency_fit"],
                savings_pct,
                a["risk_level"],
            )
            tco = OutsourcingEngine.tco(
                external, a["transition_cost"], contract_years, a["risk_level"]
            )
            risk_adj_external_annual = (
                tco["annual_vendor_cost"] + tco["annual_risk_premium"]
            )
            risk_adj_savings = round(internal - risk_adj_external_annual, 4)

            rows.append(
                {
                    "name": a["name"],
                    "strategic_importance": a["strategic_importance"],
                    "core_competency_fit": a["core_competency_fit"],
                    "internal_cost": internal,
                    "external_cost": external,
                    "nominal_savings": savings,
                    "nominal_savings_pct": savings_pct,
                    "risk_level": a["risk_level"],
                    "risk_adjusted_external_annual": round(risk_adj_external_annual, 4),
                    "risk_adjusted_savings_annual": risk_adj_savings,
                    "tco": tco,
                    "recommendation": recommendation,
                    "rationale": rationale,
                }
            )

        decisions = {}
        for r in rows:
            decisions.setdefault(r["recommendation"], []).append(r["name"])

        buy_rows = [r for r in rows if r["recommendation"] == "BUY"]
        total_potential_savings = sum(
            r["risk_adjusted_savings_annual"] for r in buy_rows
        )
        high_risk_buys = [
            r["name"]
            for r in rows
            if r["recommendation"] in ("BUY", "ALLY") and r["risk_level"] == "HIGH"
        ]

        result = {
            "decisions": rows,
            "decision_summary": {
                "counts": {k: len(v) for k, v in decisions.items()},
                "activities_by_decision": decisions,
                "contract_years": contract_years,
                "total_risk_adjusted_savings_annual_if_buy": round(
                    total_potential_savings, 4
                ),
                "high_risk_externalizations": high_risk_buys,
            },
        }
        make_core = [
            r
            for r in rows
            if r["recommendation"] == "MAKE" and r["core_competency_fit"] >= 8
        ][:2]
        ally_rows = [r for r in rows if r["recommendation"] == "ALLY"][:2]
        recommendations = [
            *(
                f"Execute BUY for '{r['name']}' with strict SLA and exit clauses "
                f"(TCO {r['tco']['multi_year_tco']:,.0f} over {contract_years} yrs)."
                for r in buy_rows[:3]
            ),
            *(
                f"Keep '{r['name']}' in-house — protect core differentiation."
                for r in make_core
            ),
            *(
                f"Structure ALLY governance for '{r['name']}' (joint steering committee, IP safeguards)."
                for r in ally_rows
            ),
        ][:5] or ["Review portfolio annually as cost and risk profiles shift."]
        interpretation = {
            "summary": (
                f"{len(rows)} activities assessed over {contract_years}-year horizon: "
                + ", ".join(f"{k}={len(v)}" for k, v in sorted(decisions.items()))
                + f". Risk-adjusted savings potential: {total_potential_savings:,.0f}/yr."
            ),
            "key_findings": [
                f"'{r['name']}' → {r['recommendation']}: {r['rationale']}"
                for r in rows[:5]
            ],
            "recommendations": recommendations,
        }
        return {"result": result, "interpretation": interpretation}
