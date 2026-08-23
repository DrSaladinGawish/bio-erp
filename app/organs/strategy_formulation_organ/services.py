"""
Strategy Formulation Organ — Business Logic Engines
BIO-ERP v5.3.0 — strategy_formulation_organ

12 stateless engines with real strategy analysis logic:
BCG Matrix, Ansoff Matrix, Blue Ocean, Porter's Generic Strategies, TOWS,
Competitive Advantage, Core Competency, Strategic Intent, Value Innovation,
Disruptive Innovation, Platform Strategy, Ecosystem Strategy.
"""


# =============================================================================
# 1. BCG MATRIX (Growth-Share Matrix)
# =============================================================================


class BCGEngine:
    """1. BCG Matrix — Stars / Cash Cows / Question Marks / Dogs."""

    HIGH_GROWTH_THRESHOLD_PCT = 10.0
    SHARE_LEADER_THRESHOLD = 1.0

    QUADRANT_ACTIONS = {
        "STAR": "INVEST_TO_GROW",
        "CASH_COW": "HARVEST_AND_DEFEND",
        "QUESTION_MARK": "SELECTIVE_INVEST_OR_DIVEST",
        "DOG": "DIVEST_OR_REPOSITION",
    }

    @staticmethod
    def classify_unit(relative_market_share: float, market_growth_rate_pct: float) -> str:
        high_share = relative_market_share >= BCGEngine.SHARE_LEADER_THRESHOLD
        high_growth = market_growth_rate_pct >= BCGEngine.HIGH_GROWTH_THRESHOLD_PCT
        if high_share and high_growth:
            return "STAR"
        if high_share and not high_growth:
            return "CASH_COW"
        if not high_share and high_growth:
            return "QUESTION_MARK"
        return "DOG"

    @staticmethod
    def revenue_concentration(units: list) -> dict:
        total_revenue = sum(u["revenue"] for u in units) or 1.0
        shares = [u["revenue"] / total_revenue for u in units]
        hhi = round(sum(s * s for s in shares) * 10000, 1)
        if hhi >= 5000:
            concentration = "HIGH — portfolio dependent on few units"
        elif hhi >= 2500:
            concentration = "MODERATE — balanced dependence"
        else:
            concentration = "LOW — well diversified"
        return {
            "total_revenue": round(total_revenue, 2),
            "hhi_index": hhi,
            "concentration_level": concentration,
        }

    @staticmethod
    def resource_allocation(quadrants: dict, units: list) -> list:
        """Heuristic investment budget split across units by quadrant economics."""
        allocations = []
        qms = sorted(
            [u for u in units if u["quadrant"] == "QUESTION_MARK"],
            key=lambda x: x["market_growth_rate_pct"],
            reverse=True,
        )
        for u in units:
            q = u["quadrant"]
            if q == "STAR":
                pct = 35.0
                rationale = "Defend leadership in growth market; fund expansion"
            elif q == "CASH_COW":
                pct = 20.0
                rationale = "Maintain position; milk cash to fund Stars/QMs"
            elif q == "QUESTION_MARK":
                rank = qms.index(u) + 1 if u in qms else len(qms)
                pct = max(0.0, 15.0 - (rank - 1) * 5.0)
                rationale = (
                    "Highest-growth QM — invest to build share"
                    if pct > 0
                    else "Weakest QM — divest or minimize spend"
                )
            else:
                pct = 5.0
                rationale = "Minimize holding cost; plan exit or niche repositioning"
            allocations.append({
                "unit_name": u["name"],
                "quadrant": q,
                "recommended_budget_pct": round(pct, 1),
                "recommended_action": BCGEngine.QUADRANT_ACTIONS[q],
                "rationale": rationale,
            })
        total_pct = sum(a["recommended_budget_pct"] for a in allocations) or 1.0
        for a in allocations:
            a["normalized_budget_pct"] = round(a["recommended_budget_pct"] / total_pct * 100, 1)
        return allocations

    @staticmethod
    def analyze(business_units: list) -> dict:
        total_revenue = sum(u["revenue"] for u in business_units) or 1.0
        classified = []
        quadrants = {"STAR": [], "CASH_COW": [], "QUESTION_MARK": [], "DOG": []}
        for u in business_units:
            quadrant = BCGEngine.classify_unit(
                u["relative_market_share"], u["market_growth_rate_pct"]
            )
            entry = {
                **u,
                "quadrant": quadrant,
                "revenue_share_pct": round(u["revenue"] / total_revenue * 100, 2),
            }
            classified.append(entry)
            quadrants[quadrant].append(entry)

        concentration = BCGEngine.revenue_concentration(business_units)
        allocation = BCGEngine.resource_allocation(quadrants, classified)

        quadrant_summary = {}
        for q, items in quadrants.items():
            quadrant_summary[q] = {
                "count": len(items),
                "units": [i["name"] for i in items],
                "revenue_share_pct": round(
                    sum(i["revenue_share_pct"] for i in items), 2
                ),
            }

        star_rev = quadrant_summary["STAR"]["revenue_share_pct"]
        cow_rev = quadrant_summary["CASH_COW"]["revenue_share_pct"]
        dog_rev = quadrant_summary["DOG"]["revenue_share_pct"]

        if star_rev + cow_rev >= 70:
            interpretation = (
                f"Healthy portfolio shape — {star_rev + cow_rev:.0f}% of revenue comes from "
                f"Stars and Cash Cows. Fund Star growth from Cow cash flows; prune the "
                f"{dog_rev:.0f}% Dog revenue over time."
            )
        elif quadrant_summary["QUESTION_MARK"]["count"] > len(business_units) / 2:
            interpretation = (
                "Portfolio skewed toward Question Marks — heavy future cash demands with "
                "uncertain payoffs. Prioritize ruthlessly: invest only where share gains "
                "are achievable within 2-3 planning periods."
            )
        elif dog_rev >= 40:
            interpretation = (
                f"Weak portfolio — {dog_rev:.0f}% of revenue sits in Dogs. Restructure: "
                "divest or reposition low-share/low-growth units and redeploy capital "
                "toward growth options."
            )
        else:
            interpretation = (
                "Mixed portfolio — rebalance by converting selected Question Marks into "
                "Stars and harvesting Cash Cows to fund the transition."
            )

        return {
            "business_units": classified,
            "quadrant_summary": quadrant_summary,
            "revenue_concentration": concentration,
            "resource_allocation": allocation,
            "interpretation": interpretation,
        }


# =============================================================================
# 2. ANSOFF MATRIX (Product-Market Growth Vector)
# =============================================================================


class AnsoffEngine:
    """2. Ansoff Matrix — Penetration / Product Dev / Market Dev / Diversification."""

    RISK_LEVELS = {
        "MARKET_PENETRATION": ("LOW", 1.0),
        "PRODUCT_DEVELOPMENT": ("MEDIUM", 2.0),
        "MARKET_DEVELOPMENT": ("MEDIUM", 2.0),
        "DIVERSIFICATION": ("HIGH", 3.0),
    }
    REVENUE_IMPACT_PCT = {
        "MARKET_PENETRATION": (2.0, 8.0),
        "PRODUCT_DEVELOPMENT": (8.0, 18.0),
        "MARKET_DEVELOPMENT": (10.0, 20.0),
        "DIVERSIFICATION": (15.0, 40.0),
    }

    @staticmethod
    def _feasibility(current_state: dict, markets: list, products: list) -> dict:
        share = current_state["market_share_pct"]
        maturity = current_state["product_maturity"]
        avg_market_growth = (
            sum(m["growth_rate_pct"] for m in markets) / len(markets) if markets else 0.0
        )
        has_new_products = any(p["is_new_to_company"] for p in products)
        has_new_markets = any(m["is_new_to_company"] for m in markets)

        penetration = min(10.0, (50 - share) / 4 + max(0, avg_market_growth) / 3)
        product_dev = maturity * 0.6 + (share / 100) * 10 * 0.4
        market_dev = (11 - maturity) * 0.6 + (share / 100) * 10 * 0.4
        diversification = 4.0 + (share / 100) * 3 - max(0, avg_market_growth) / 5
        if has_new_products:
            product_dev += 1.0
        if has_new_markets:
            market_dev += 1.0

        return {
            "MARKET_PENETRATION": max(1.0, min(10.0, penetration)),
            "PRODUCT_DEVELOPMENT": max(1.0, min(10.0, product_dev)),
            "MARKET_DEVELOPMENT": max(1.0, min(10.0, market_dev)),
            "DIVERSIFICATION": max(1.0, min(10.0, diversification)),
        }

    @staticmethod
    def analyze(products: list, markets: list, current_state: dict) -> dict:
        feasibility = AnsoffEngine._feasibility(current_state, markets, products)

        strategies = []
        for name, score in feasibility.items():
            risk_label, risk_multiplier = AnsoffEngine.RISK_LEVELS[name]
            lo, hi = AnsoffEngine.REVENUE_IMPACT_PCT[name]
            expected_impact = round((lo + hi) / 2 * (score / 10), 2)
            strategies.append({
                "strategy": name,
                "feasibility_score": round(score, 2),
                "risk_level": risk_label,
                "risk_multiplier": risk_multiplier,
                "expected_revenue_impact_pct_range": [lo, hi],
                "expected_revenue_impact_pct": expected_impact,
            })

        ranked = sorted(strategies, key=lambda s: s["feasibility_score"], reverse=True)
        recommended = ranked[0]

        if recommended["strategy"] == "MARKET_PENETRATION":
            detail = (
                f"With {current_state['market_share_pct']:.0f}% share there is headroom in "
                "existing markets. Push pricing, promotion, and distribution intensity "
                "before funding riskier vectors."
            )
        elif recommended["strategy"] == "PRODUCT_DEVELOPMENT":
            detail = (
                "Existing products are mature while current-market position is strong — "
                "launch next-generation offerings to your installed base."
            )
        elif recommended["strategy"] == "MARKET_DEVELOPMENT":
            detail = (
                "Products still have life in unserved segments/geographies — extend reach "
                "before investing in new product lines."
            )
        else:
            detail = (
                "Current product-market space is saturated — diversification offers the "
                "largest upside but demands rigorous capability and risk assessment."
            )

        interpretation = (
            f"Recommended growth vector: {recommended['strategy']} "
            f"(feasibility {recommended['feasibility_score']}/10, "
            f"{recommended['risk_level']} risk, ~{recommended['expected_revenue_impact_pct']}% "
            f"expected revenue impact). {detail}"
        )

        return {
            "strategies": strategies,
            "ranking": [s["strategy"] for s in ranked],
            "recommended_strategy": recommended["strategy"],
            "risk_level": recommended["risk_level"],
            "expected_revenue_impact_pct": recommended["expected_revenue_impact_pct"],
            "feasibility_scores": feasibility,
            "interpretation": interpretation,
        }


# =============================================================================
# 3. BLUE OCEAN STRATEGY (ERRC Grid + Value Curve)
# =============================================================================


class BlueOceanEngine:
    """3. Blue Ocean Strategy — Eliminate-Reduce-Raise-Create grid."""

    @staticmethod
    def classify_factors(factors: list, competitor_map: dict) -> list:
        classified = []
        for f in factors:
            name = f["name"]
            level = f["current_level"]
            importance = f["importance_to_customer"]
            comp_level = competitor_map.get(name)

            if comp_level is None:
                action = "CREATE"
                new_level = min(10.0, importance * 0.9)
                reason = "Factor absent from competing offerings — new source of buyer value"
            elif importance <= 3 and level >= comp_level:
                action = "ELIMINATE"
                new_level = 0.0
                reason = "Over-served factor customers do not value — strip it out"
            elif importance <= 6 and level > comp_level + 1:
                action = "REDUCE"
                new_level = round(max(comp_level, level * 0.6), 2)
                reason = "Over-delivery relative to importance — standardize to industry-good"
            elif importance >= 7 and level < comp_level:
                action = "RAISE"
                new_level = round(min(10.0, comp_level + 1.5), 2)
                reason = "Under-delivering on what buyers care most about — leapfrog rivals"
            else:
                action = "MAINTAIN"
                new_level = level
                reason = "Adequate delivery at competitive parity — hold for now"
            classified.append({
                **f,
                "competitor_level": comp_level,
                "errc_action": action,
                "new_curve_level": new_level,
                "reason": reason,
            })
        return classified

    @staticmethod
    def analyze(factors: list, competitor_factors: list) -> dict:
        competitor_map = {c["name"]: c["level"] for c in competitor_factors}
        classified = BlueOceanEngine.classify_factors(factors, competitor_map)

        errc = {
            "eliminate": [f["name"] for f in classified if f["errc_action"] == "ELIMINATE"],
            "reduce": [f["name"] for f in classified if f["errc_action"] == "REDUCE"],
            "raise": [f["name"] for f in classified if f["errc_action"] == "RAISE"],
            "create": [f["name"] for f in classified if f["errc_action"] == "CREATE"],
        }

        old_value = sum(f["current_level"] * f["importance_to_customer"] for f in factors)
        new_value = sum(f["new_curve_level"] * f["importance_to_customer"] for f in classified)
        max_value = sum(10 * f["importance_to_customer"] for f in factors) or 1.0
        value_index_before = round(old_value / max_value * 100, 1)
        value_index_after = round(new_value / max_value * 100, 1)

        comp_value = sum(
            competitor_map.get(f["name"], f["current_level"]) * f["importance_to_customer"]
            for f in factors
        )
        comp_value_index = round(comp_value / max_value * 100, 1)

        differentiation_gap = round(value_index_after - comp_value_index, 1)
        attractiveness = round(
            max(0.0, min(10.0,
                (value_index_after - value_index_before) / 8
                + differentiation_gap / 10
                + len(errc["create"]) * 0.8
            )),
            2,
        )

        n_moves = sum(len(v) for v in errc.values())
        if attractiveness >= 7:
            tone = "Strong blue ocean potential — the new value curve diverges sharply from the industry."
        elif attractiveness >= 4:
            tone = "Moderate blue ocean potential — meaningful divergence on select factors."
        else:
            tone = "Weak divergence — refine ERRC moves before committing investment."

        interpretation = (
            f"ERRC grid: eliminate {len(errc['eliminate'])}, reduce {len(errc['reduce'])}, "
            f"raise {len(errc['raise'])}, create {len(errc['create'])} of {n_moves} factors reviewed. "
            f"Buyer value index moves {value_index_before} → {value_index_after} vs competitor "
            f"{comp_value_index}. Strategic attractiveness {attractiveness}/10. {tone}"
        )

        return {
            "errc_grid": errc,
            "factor_analysis": classified,
            "value_curve": {
                "before": {f["name"]: f["current_level"] for f in factors},
                "after": {f["name"]: f["new_curve_level"] for f in classified},
                "competitor": {f["name"]: competitor_map.get(f["name"], 0.0) for f in factors},
            },
            "buyer_value_index": {
                "before": value_index_before,
                "after": value_index_after,
                "competitor_benchmark": comp_value_index,
            },
            "differentiation_gap": differentiation_gap,
            "strategic_attractiveness_score": attractiveness,
            "interpretation": interpretation,
        }


# =============================================================================
# 4. PORTER'S GENERIC STRATEGIES
# =============================================================================


class PorterGenericEngine:
    """4. Porter's Generic Strategies — Cost / Differentiation / Focus."""

    STUCK_IN_MIDDLE = "STUCK_IN_THE_MIDDLE"

    @staticmethod
    def recommend(cost_position: float, diff_strength: float, narrow_scope: bool) -> dict:
        both_strong = cost_position >= 7 and diff_strength >= 7
        neither_strong = cost_position < 5 and diff_strength < 5

        if both_strong:
            strategy = "BEST_COST_PROVIDER"
            advantage_type = "BEST_COST"
        elif neither_strong:
            strategy = PorterGenericEngine.STUCK_IN_MIDDLE
            advantage_type = "NONE"
        elif cost_position >= diff_strength:
            strategy = "FOCUSED_COST_LEADERSHIP" if narrow_scope else "COST_LEADERSHIP"
            advantage_type = "COST"
        else:
            strategy = "FOCUSED_DIFFERENTIATION" if narrow_scope else "DIFFERENTIATION"
            advantage_type = "DIFFERENTIATION"
        return {"strategy": strategy, "advantage_type": advantage_type}

    @staticmethod
    def sustainability_score(cost_position: float, diff_strengths: list, narrow_scope: bool) -> float:
        avg_diff = sum(d["strength"] for d in diff_strengths) / len(diff_strengths)
        spread = max(d["strength"] for d in diff_strengths) - min(d["strength"] for d in diff_strengths)
        consistency_bonus = max(0.0, 2.0 - spread)
        base = max(cost_position, avg_diff)
        focus_premium = 0.5 if narrow_scope else 0.0
        return round(max(0.0, min(10.0, base * 0.85 + consistency_bonus + focus_premium)), 2)

    @staticmethod
    def analyze(cost_position: float, differentiation_strengths: list,
                market_scope: str, competitive_scope: str) -> dict:
        avg_diff = sum(d["strength"] for d in differentiation_strengths) / len(differentiation_strengths)
        narrow_scope = market_scope.upper() == "NARROW" or competitive_scope.upper() == "NARROW"

        rec = PorterGenericEngine.recommend(cost_position, avg_diff, narrow_scope)
        sustainability = PorterGenericEngine.sustainability_score(
            cost_position, differentiation_strengths, narrow_scope
        )

        top_differentiators = sorted(
            differentiation_strengths, key=lambda d: d["strength"], reverse=True
        )[:3]

        if rec["strategy"] == PorterGenericEngine.STUCK_IN_MIDDLE:
            interpretation = (
                "Warning — Porter's 'stuck in the middle': neither cost nor differentiation "
                "advantage is strong enough to defend margins. Commit decisively to one "
                "generic strategy and reallocate resources accordingly."
            )
        elif rec["strategy"] == "BEST_COST_PROVIDER":
            interpretation = (
                "Hybrid best-cost position detected (strong on both dimensions). Sustainable "
                "only with superior capabilities (e.g., flexible ops or scale learning); "
                "monitor for margin erosion against pure players."
            )
        else:
            lever = "cost position" if rec["advantage_type"] == "COST" else "differentiation"
            interpretation = (
                f"Recommended generic strategy: {rec['strategy']} built on a {'narrow' if narrow_scope else 'broad'} "
                f"scope. Primary lever is {lever} ({max(cost_position, avg_diff):.1f}/10). "
                f"Sustainability score {sustainability}/10 — "
                + ("durable if imitability stays low." if sustainability >= 7 else "vulnerable; deepen moats.")
            )

        return {
            "cost_position": cost_position,
            "average_differentiation_strength": round(avg_diff, 2),
            "top_differentiators": [
                {"name": d["name"], "strength": d["strength"]} for d in top_differentiators
            ],
            "market_scope": market_scope.upper(),
            "competitive_scope": competitive_scope.upper(),
            "recommended_strategy": rec["strategy"],
            "competitive_advantage_type": rec["advantage_type"],
            "sustainability_score": sustainability,
            "interpretation": interpretation,
        }


# =============================================================================
# 5. TOWS STRATEGY (SWOT-to-Strategy Bridge)
# =============================================================================


class TOWSEngine:
    """5. TOWS Matrix — SO/WO/ST/WT strategy generation and prioritization."""

    MAX_PAIRINGS_PER_CELL = 4

    @staticmethod
    def _pairings(internal: list, external: list, template, cell: str) -> list:
        internal_sorted = sorted(internal, key=lambda x: x["score"], reverse=True)
        external_sorted = sorted(external, key=lambda x: x["score"], reverse=True)
        results = []
        for i in internal_sorted:
            for e in external_sorted:
                if len(results) >= TOWSEngine.MAX_PAIRINGS_PER_CELL:
                    break
                priority = round((i["score"] + e["score"]) / 2, 2)
                results.append({
                    "cell": cell,
                    "strategy": template.format(i=i["item_name"], e=e["item_name"]),
                    "internal_item": i["item_name"],
                    "external_item": e["item_name"],
                    "priority_score": priority,
                })
            if len(results) >= TOWSEngine.MAX_PAIRINGS_PER_CELL:
                break
        return results

    @staticmethod
    def analyze(strengths: list, weaknesses: list, opportunities: list, threats: list) -> dict:
        def avg(items):
            return round(sum(i["score"] for i in items) / len(items), 2) if items else 0.0

        s_avg, w_avg = avg(strengths), avg(weaknesses)
        o_avg, t_avg = avg(opportunities), avg(threats)
        internal = round(s_avg - w_avg, 2)
        external = round(o_avg - t_avg, 2)

        so = TOWSEngine._pairings(
            strengths, opportunities,
            "Leverage {i} to capture {e}", "SO",
        ) if strengths and opportunities else []
        wo = TOWSEngine._pairings(
            weaknesses, opportunities,
            "Overcome {i} to exploit {e}", "WO",
        ) if weaknesses and opportunities else []
        st = TOWSEngine._pairings(
            strengths, threats,
            "Use {i} to defend against {e}", "ST",
        ) if strengths and threats else []
        wt = TOWSEngine._pairings(
            weaknesses, threats,
            "Mitigate {i} to avoid exposure to {e}", "WT",
        ) if weaknesses and threats else []

        all_strategies = sorted(
            so + wo + st + wt, key=lambda s: s["priority_score"], reverse=True
        )
        for rank, s in enumerate(all_strategies, start=1):
            s["rank"] = rank

        if internal >= 0 and external >= 0:
            posture, posture_desc = "AGGRESSIVE", "Maximize strengths against opportunities (SO-led)"
        elif internal < 0 and external >= 0:
            posture, posture_desc = "TURNAROUND", "Fix weaknesses to unlock opportunities (WO-led)"
        elif internal >= 0 and external < 0:
            posture, posture_desc = "DEFENSIVE", "Deploy strengths to blunt threats (ST-led)"
        else:
            posture, posture_desc = "SURVIVAL", "Minimize weaknesses and dodge threats (WT-led)"

        interpretation = (
            f"Strategic posture: {posture} — {posture_desc}. Internal balance {internal:+.1f} "
            f"(S {s_avg} vs W {w_avg}), external balance {external:+.1f} (O {o_avg} vs T {t_avg}). "
            f"{len(all_strategies)} candidate strategies generated; top priority: "
            + (all_strategies[0]["strategy"] if all_strategies else "insufficient inputs")
            + "."
        )

        return {
            "quadrant_averages": {
                "strengths": s_avg, "weaknesses": w_avg,
                "opportunities": o_avg, "threats": t_avg,
            },
            "internal_balance": internal,
            "external_balance": external,
            "strategic_posture": posture,
            "posture_description": posture_desc,
            "SO": so,
            "WO": wo,
            "ST": st,
            "WT": wt,
            "prioritized_strategies": all_strategies[:10],
            "interpretation": interpretation,
        }


# =============================================================================
# 6. COMPETITIVE ADVANTAGE (Sustainability Assessment)
# =============================================================================


class CompetitiveAdvantageEngine:
    """6. Competitive Advantage — durability and imitation-barrier scoring."""

    TYPE_INVESTMENTS = {
        "COST": ["Process automation", "Scale economies", "Supplier lock-ins"],
        "DIFFERENTIATION": ["Brand building", "R&D pipeline", "Customer experience design"],
        "NETWORK_EFFECTS": ["User-base subsidies", "Developer ecosystem", "Standards adoption"],
        "SWITCHING_COSTS": ["Integration depth", "Data portability friction", "Loyalty programs"],
        "BRAND": ["Consistent positioning", "Trust certifications", "Thought leadership"],
        "REGULATORY": ["Compliance excellence", "License expansion", "Policy relationships"],
        "TALENT": ["Retention programs", "Knowledge management", "Succession depth"],
    }

    @staticmethod
    def advantage_score(rarity: float, durability: float, imitability_score: float) -> float:
        barrier = 11.0 - imitability_score
        return round(0.30 * rarity + 0.40 * durability + 0.30 * barrier, 2)

    @staticmethod
    def sustainability_years(durability: float, imitability_score: float) -> float:
        years = durability * 1.8 - imitability_score * 0.7
        return round(max(0.5, years), 1)

    @staticmethod
    def analyze(advantages: list) -> dict:
        scored = []
        for a in advantages:
            score = CompetitiveAdvantageEngine.advantage_score(
                a["rarity"], a["durability"], a["imitability_score"]
            )
            years = CompetitiveAdvantageEngine.sustainability_years(
                a["durability"], a["imitability_score"]
            )
            investments = CompetitiveAdvantageEngine.TYPE_INVESTMENTS.get(
                a.get("type", "DIFFERENTIATION").upper(),
                CompetitiveAdvantageEngine.TYPE_INVESTMENTS["DIFFERENTIATION"],
            )
            scored.append({
                **a,
                "advantage_score": score,
                "sustainability_years_estimate": years,
                "is_sustainable": score >= 6.5 and years >= 3.0,
                "recommended_investments": investments,
            })

        scored.sort(key=lambda x: x["advantage_score"], reverse=True)
        strongest = scored[0] if scored else None
        sustainable_count = sum(1 for s in scored if s["is_sustainable"])
        avg_score = round(sum(s["advantage_score"] for s in scored) / len(scored), 2) if scored else 0.0

        if strongest and strongest["advantage_score"] >= 7.5:
            interpretation = (
                f"'{strongest['name']}' is the anchor advantage ({strongest['advantage_score']}/10, "
                f"~{strongest['sustainability_years_estimate']} years of protection). Concentrate "
                f"investment here; {sustainable_count}/{len(scored)} advantages meet the "
                "sustainability bar."
            )
        elif avg_score >= 5.5:
            interpretation = (
                f"Moderate advantage portfolio (avg {avg_score}/10). No single decisive moat — "
                "deepen the top-ranked advantage rather than spreading investment thinly."
            )
        else:
            interpretation = (
                f"Fragile advantage position (avg {avg_score}/10) — advantages are easily "
                "imitated or short-lived. Prioritize structural barriers (network effects, "
                "switching costs, regulatory positions) over incremental strengths."
            )

        return {
            "advantages": scored,
            "strongest_advantage": strongest["name"] if strongest else None,
            "average_advantage_score": avg_score,
            "sustainable_count": sustainable_count,
            "portfolio_defensibility": (
                "STRONG" if avg_score >= 7 else "MODERATE" if avg_score >= 5 else "WEAK"
            ),
            "interpretation": interpretation,
        }


# =============================================================================
# 7. CORE COMPETENCY (Prahalad & Hamel)
# =============================================================================


class CoreCompetencyEngine:
    """7. Core Competency — three-test scoring and competence ladder."""

    WEIGHTS = {
        "market_relevance": 0.30,
        "customer_value": 0.30,
        "competitor_rarity": 0.25,
        "uniqueness": 0.15,
    }

    @staticmethod
    def passes_three_tests(c: dict) -> dict:
        return {
            "market_access_test": c["market_relevance"] >= 6,
            "customer_value_test": c["customer_value"] >= 6,
            "imitation_barrier_test": c["competitor_rarity"] >= 6 and c["uniqueness"] >= 5,
        }

    @staticmethod
    def ladder_position(core_score: float, tests: dict) -> str:
        tests_passed = sum(tests.values())
        if core_score >= 7.5 and tests_passed == 3:
            return "CORE"
        if core_score >= 6.0 and tests_passed >= 2:
            return "DISTINCTIVE"
        if core_score >= 4.0:
            return "BASIC"
        return "PERIPHERAL"

    @staticmethod
    def investment_priority(core_score: float, ladder: str) -> str:
        if ladder == "CORE":
            return "PROTECT_AND_EXTEND"
        if ladder == "DISTINCTIVE":
            return "BUILD_UP" if core_score >= 6.5 else "SELECTIVE_BUILD"
        if ladder == "BASIC":
            return "MAINTAIN"
        return "OUTSOURCE_OR_HARVEST"

    @staticmethod
    def analyze(competencies: list) -> dict:
        w = CoreCompetencyEngine.WEIGHTS
        scored = []
        for c in competencies:
            core_score = round(
                c["market_relevance"] * w["market_relevance"]
                + c["customer_value"] * w["customer_value"]
                + c["competitor_rarity"] * w["competitor_rarity"]
                + c["uniqueness"] * w["uniqueness"],
                2,
            )
            tests = CoreCompetencyEngine.passes_three_tests(c)
            ladder = CoreCompetencyEngine.ladder_position(core_score, tests)
            scored.append({
                **c,
                "core_score": core_score,
                "three_tests": tests,
                "tests_passed": sum(tests.values()),
                "ladder_position": ladder,
                "investment_priority": CoreCompetencyEngine.investment_priority(core_score, ladder),
            })

        scored.sort(key=lambda x: x["core_score"], reverse=True)
        for rank, s in enumerate(scored, start=1):
            s["rank"] = rank

        core_count = sum(1 for s in scored if s["ladder_position"] == "CORE")

        if core_count >= 1:
            top = scored[0]
            interpretation = (
                f"{core_count} true core competency(ies) identified. '{top['name']}' leads "
                f"(score {top['core_score']}/10, passes {top['tests_passed']}/3 Prahalad-Hamel "
                "tests). Focus investment on protecting and extending it into adjacent markets."
            )
        else:
            interpretation = (
                "No competency passes all three core tests — the organization holds "
                "distinctive or basic skills only. Either concentrate resources to forge a "
                "genuine core competency or reposition strategy around existing strengths."
            )

        return {
            "competencies": scored,
            "ranking": [s["name"] for s in scored],
            "core_count": core_count,
            "ladder_distribution": {
                pos: sum(1 for s in scored if s["ladder_position"] == pos)
                for pos in ("CORE", "DISTINCTIVE", "BASIC", "PERIPHERAL")
            },
            "interpretation": interpretation,
        }


# =============================================================================
# 8. STRATEGIC INTENT (Stretch Goals & Alignment)
# =============================================================================


class StrategicIntentEngine:
    """8. Strategic Intent — Hamel & Prahalad stretch-goal alignment."""

    @staticmethod
    def completeness(vision: str, mission: str, objectives: list) -> float:
        vision_score = min(10.0, len(vision.strip()) / 12) if vision.strip() else 0.0
        mission_score = min(10.0, len(mission.strip()) / 12) if mission.strip() else 0.0
        objectives_score = min(10.0, len(objectives) * 2.0)
        return round((vision_score + mission_score + objectives_score) / 3, 2)

    @staticmethod
    def ambition(gap_to_ambition_pct: float, current_performance: float) -> float:
        gap_component = min(10.0, gap_to_ambition_pct / 5)
        perf_component = max(0.0, 10.0 - abs(60 - current_performance) / 6)
        return round((gap_component * 0.6 + perf_component * 0.4), 2)

    @staticmethod
    def stretch_goals(gap_to_ambition_pct: float, current_performance: float) -> list:
        if gap_to_ambition_pct <= 0:
            return []
        stages = [(0.5, "Horizon 1"), (0.75, "Horizon 2"), (1.0, "Horizon 3")]
        goals = []
        for fraction, horizon in stages:
            target_perf = min(100.0, current_performance + gap_to_ambition_pct * fraction)
            goals.append({
                "horizon": horizon,
                "target_performance_index": round(target_perf, 1),
                "gap_closure_pct": int(fraction * 100),
                "description": (
                    f"Close {fraction * 100:.0f}% of the ambition gap "
                    f"(performance index → {target_perf:.0f})"
                ),
            })
        return goals

    @staticmethod
    def alignment_gaps(objectives: list) -> list:
        gaps = []
        overall_progress = []
        computed = []
        for o in objectives:
            progress = (o["current_value"] / o["target_value"] * 100) if o["target_value"] else 0.0
            computed.append({**o, "progress_pct": round(min(progress, 150.0), 1)})
            overall_progress.append(min(progress, 100.0))
        avg_progress = sum(overall_progress) / len(overall_progress) if overall_progress else 0.0
        for c in computed:
            deviation = round(c["progress_pct"] - avg_progress, 1)
            if deviation <= -15:
                status = "LAGGING"
            elif deviation >= 15:
                status = "LEADING"
            else:
                status = "ON_TRACK"
            gaps.append({
                "objective": c["description"],
                "progress_pct": c["progress_pct"],
                "deviation_from_average": deviation,
                "alignment_status": status,
            })
        gaps.sort(key=lambda g: g["deviation_from_average"])
        return gaps

    @staticmethod
    def analyze(vision: str, mission: str, objectives: list,
                current_performance: float, gap_to_ambition_pct: float) -> dict:
        completeness = StrategicIntentEngine.completeness(vision, mission, objectives)
        ambition = StrategicIntentEngine.ambition(gap_to_ambition_pct, current_performance)
        goals = StrategicIntentEngine.stretch_goals(gap_to_ambition_pct, current_performance)
        gaps = StrategicIntentEngine.alignment_gaps(objectives)

        lagging = sum(1 for g in gaps if g["alignment_status"] == "LAGGING")
        alignment_score = round(10 - lagging * 1.5, 2) if gaps else 7.5
        alignment_score = max(0.0, min(10.0, alignment_score))

        intent_score = round(
            completeness * 0.40 + ambition * 0.30 + alignment_score * 0.30, 2
        )

        if intent_score >= 7.5:
            interpretation = (
                f"Strong strategic intent ({intent_score}/10) — clear direction, ambitious "
                "stretch targets, and broadly aligned objectives. Guard against complacency "
                "by re-baselining ambition upward as gaps close."
            )
        elif intent_score >= 5.0:
            interpretation = (
                f"Developing strategic intent ({intent_score}/10). "
                + (f"{lagging} objective(s) lag the average pace and need intervention. " if lagging else "")
                + "Sharpen the vision statement and cascade stretch goals to operating units."
            )
        else:
            interpretation = (
                f"Weak strategic intent ({intent_score}/10) — vision/mission articulation, "
                "ambition level, or objective alignment is deficient. Leadership must first "
                "define an emotionally compelling ambition before cascading targets."
            )

        return {
            "intent_score": intent_score,
            "components": {
                "direction_completeness": completeness,
                "ambition_level": ambition,
                "alignment_score": alignment_score,
            },
            "stretch_goals": goals,
            "alignment_gaps": gaps,
            "lagging_objectives": lagging,
            "interpretation": interpretation,
        }


# =============================================================================
# 9. VALUE INNOVATION (Blue Ocean × Cost Bridge)
# =============================================================================


class ValueInnovationEngine:
    """9. Value Innovation — cost-value frontier analysis."""

    @staticmethod
    def element_opportunity(our_cost: float, our_value: float,
                            bench_cost: float, bench_value: float) -> tuple:
        if bench_cost <= 0:
            bench_cost = 0.01
        cost_ratio = our_cost / bench_cost
        value_gap = our_value - bench_value

        if value_gap >= 1.0 and cost_ratio <= 1.05:
            return "SUSTAIN_LEAD", value_gap, cost_ratio
        if value_gap >= 1.0:
            return "DIFFERENTIATE_PREMIUM", value_gap, cost_ratio
        if value_gap <= -1.0 and cost_ratio >= 1.1:
            return "VALUE_INNOVATE_NOW", value_gap, cost_ratio
        if cost_ratio >= 1.15:
            return "CUT_COST", value_gap, cost_ratio
        if value_gap <= -1.0:
            return "RAISE_VALUE", value_gap, cost_ratio
        return "MAINTAIN", value_gap, cost_ratio

    @staticmethod
    def analyze(value_elements: list, competitor_benchmark: list) -> dict:
        bench_map = {b["name"]: b for b in competitor_benchmark}
        analyzed = []
        total_our_cost = sum(e["current_cost"] for e in value_elements) or 1.0
        total_bench_cost = sum(bench_map.get(e["name"], {}).get("cost", e["current_cost"])
                               for e in value_elements) or 1.0

        for e in value_elements:
            b = bench_map.get(e["name"], {"cost": e["current_cost"], "perceived_value": e["customer_perceived_value"]})
            opportunity, value_gap, cost_ratio = ValueInnovationEngine.element_opportunity(
                e["current_cost"], e["customer_perceived_value"],
                b["cost"], b["perceived_value"],
            )
            innovation_score = round(
                max(-10.0, min(10.0, value_gap * 1.2 - (cost_ratio - 1) * 5)), 2
            )
            analyzed.append({
                **e,
                "benchmark_cost": b["cost"],
                "benchmark_perceived_value": b["perceived_value"],
                "value_gap": round(value_gap, 2),
                "cost_ratio_vs_benchmark": round(cost_ratio, 3),
                "opportunity": opportunity,
                "innovation_score": innovation_score,
            })

        value_lift = sum(a["value_gap"] for a in analyzed)
        cost_delta_pct = round((total_our_cost - total_bench_cost) / total_bench_cost * 100, 1)

        if value_lift > 0 and cost_delta_pct < 0:
            frontier = "VALUE_INNOVATION"
            frontier_desc = "Higher buyer value at lower cost — classic value innovation achieved"
        elif value_lift > 0 and cost_delta_pct >= 0:
            frontier = "DIFFERENTIATION_PREMIUM"
            frontier_desc = "Higher buyer value but at higher cost — margin depends on willingness to pay"
        elif value_lift <= 0 and cost_delta_pct < 0:
            frontier = "COST_INNOVATION"
            frontier_desc = "Lower cost without value gain — vulnerable to differentiation attacks"
        else:
            frontier = "STAGNANT"
            frontier_desc = "No frontier movement — value lags while costs rise"

        innovation_score = round(max(0.0, min(10.0, 5.0 + value_lift * 0.8 - cost_delta_pct / 10)), 2)

        innovate_now = [a["name"] for a in analyzed if a["opportunity"] == "VALUE_INNOVATE_NOW"]
        cut_cost = [a["name"] for a in analyzed if a["opportunity"] == "CUT_COST"]

        interpretation = (
            f"Cost-value frontier position: {frontier} — {frontier_desc.lower()}. "
            f"Aggregate value lift {value_lift:+.1f} pts, cost delta {cost_delta_pct:+.1f}% vs benchmark. "
            + (f"Priority value-innovation targets: {', '.join(innovate_now)}. " if innovate_now else "")
            + (f"Cost-reduction candidates: {', '.join(cut_cost)}. " if cut_cost else "")
            + f"Overall innovation score {innovation_score}/10."
        )

        return {
            "elements": analyzed,
            "aggregate_value_lift": round(value_lift, 2),
            "cost_delta_pct_vs_benchmark": cost_delta_pct,
            "frontier_position": frontier,
            "frontier_description": frontier_desc,
            "innovation_score": innovation_score,
            "interpretation": interpretation,
        }


# =============================================================================
# 10. DISRUPTIVE INNOVATION (Christensen)
# =============================================================================


class DisruptiveInnovationEngine:
    """10. Disruptive Innovation — low-end vs new-market disruption signals."""

    @staticmethod
    def segment_potential(seg: dict) -> dict:
        dissatisfaction = 10.0 - seg["current_satisfaction"]
        trajectory = seg["technology_trajectory"]
        size_norm = min(10.0, seg["size"] / 100)
        growth_norm = max(0.0, min(10.0, 5.0 + seg["growth_rate_pct"] / 4))
        diss_norm = dissatisfaction
        traj_norm = max(0.0, min(10.0, trajectory * 3))

        potential = round(
            0.30 * diss_norm + 0.25 * growth_norm + 0.25 * traj_norm + 0.20 * size_norm, 2
        )

        if seg["current_satisfaction"] <= 4 and seg["growth_rate_pct"] >= 15 and seg["size"] < 300:
            classification = "NEW_MARKET_DISRUPTION"
        elif seg["current_satisfaction"] <= 5 and seg["technology_trajectory"] >= 1.5:
            classification = "LOW_END_DISRUPTION"
        elif seg["current_satisfaction"] >= 7 and trajectory < 1.5:
            classification = "SUSTAINING"
        else:
            classification = "HYBRID_SIGNAL"

        if potential >= 7:
            timing = "ENTER_NOW"
        elif potential >= 5:
            timing = "NEAR_TERM_1_2Y"
        else:
            timing = "WATCH"

        return {
            **seg,
            "undershoot_signal": round(dissatisfaction, 2),
            "trajectory_momentum": round(traj_norm, 2),
            "disruption_potential": potential,
            "classification": classification,
            "timing_recommendation": timing,
        }

    @staticmethod
    def analyze(segments: list) -> dict:
        analyzed = [DisruptiveInnovationEngine.segment_potential(s) for s in segments]
        analyzed.sort(key=lambda x: x["disruption_potential"], reverse=True)
        top = analyzed[0] if analyzed else None

        disruptive = [a for a in analyzed if "DISRUPTION" in a["classification"]]
        sustaining = [a for a in analyzed if a["classification"] == "SUSTAINING"]

        if top and top["disruption_potential"] >= 7:
            interpretation = (
                f"Highest disruption potential in '{top['name']}' "
                f"({top['disruption_potential']}/10, {top['classification']}). "
                + ("Enter now with a 'good-enough' solution that improves along the trajectory "
                   "before incumbents respond." if top["timing_recommendation"] == "ENTER_NOW"
                   else "Prepare entry within 1-2 years; build foothold capabilities first.")
            )
        elif disruptive:
            interpretation = (
                f"{len(disruptive)} segment(s) show disruption signals but below attack "
                "threshold. Monitor undershoot indicators (satisfaction, trajectory) quarterly "
                "and keep a lightweight entry option warm."
            )
        else:
            interpretation = (
                "All segments read as sustaining-innovation territory — incumbents satisfy "
                "mainstream customers. Compete on sustaining trajectories or hunt for "
                "non-consumers outside the mapped segments."
            )

        return {
            "segments": analyzed,
            "highest_potential_segment": top["name"] if top else None,
            "disruptive_segments": [a["name"] for a in disruptive],
            "sustaining_segments": [a["name"] for a in sustaining],
            "overall_disruption_threat": (
                "HIGH" if top and top["disruption_potential"] >= 7
                else "MODERATE" if top and top["disruption_potential"] >= 5
                else "LOW"
            ),
            "interpretation": interpretation,
        }


# =============================================================================
# 11. PLATFORM STRATEGY
# =============================================================================


class PlatformStrategyEngine:
    """11. Platform Strategy — network effects and winner-take-all dynamics."""

    WTA_TYPE_MULTIPLIER = {"PRODUCT": 1.0, "SERVICE": 0.95, "DATA": 1.1}

    TYPE_INVESTMENTS = {
        "PRODUCT": ["Open APIs & SDK quality", "Developer revenue share", "App review SLAs"],
        "SERVICE": ["Supply liquidity subsidies", "Matching algorithm R&D", "Trust & safety systems"],
        "DATA": ["Data partnerships", "Privacy governance", "ML tooling & feature store"],
    }

    @staticmethod
    def ecosystem_strength(partners: list) -> float:
        if not partners:
            return 0.0
        avg_strength = sum(p["strength"] for p in partners) / len(partners)
        breadth = min(1.5, 1.0 + len(partners) * 0.05)
        return round(avg_strength * breadth, 2)

    @staticmethod
    def attractiveness(ne: dict, switching_costs: float, eco_strength: float) -> float:
        score = (
            ne["cross_side_strength"] * 0.35
            + ne["same_side_strength"] * 0.25
            + switching_costs * 0.20
            + eco_strength * 0.20
        )
        return round(max(0.0, min(10.0, score)), 2)

    @staticmethod
    def wta_probability(attractiveness: float, platform_type: str) -> float:
        import math
        multiplier = PlatformStrategyEngine.WTA_TYPE_MULTIPLIER.get(platform_type.upper(), 1.0)
        logit = 0.9 * (attractiveness - 5.5) * multiplier
        prob = 1.0 / (1.0 + math.exp(-logit))
        return round(prob, 3)

    @staticmethod
    def chicken_egg_risk(ne: dict, partners: list) -> dict:
        strong_effects = ne["cross_side_strength"] >= 7
        thin_ecosystem = len(partners) < 3
        if strong_effects and thin_ecosystem:
            level, note = "HIGH", "Strong network effects promised but ecosystem is thin — solve the cold-start on the harder side first"
        elif thin_ecosystem:
            level, note = "MEDIUM", "Limited partners — seed one side with subsidies or single-player-useful tools"
        else:
            level, note = "LOW", "Ecosystem mass sufficient to bootstrap cross-side dynamics"
        return {"level": level, "note": note}

    @staticmethod
    def analyze(platform_type: str, network_effects: dict,
                switching_costs: float, ecosystem_partners: list) -> dict:
        eco_strength = PlatformStrategyEngine.ecosystem_strength(ecosystem_partners)
        attract = PlatformStrategyEngine.attractiveness(network_effects, switching_costs, eco_strength)
        wta = PlatformStrategyEngine.wta_probability(attract, platform_type)
        cold_start = PlatformStrategyEngine.chicken_egg_risk(network_effects, ecosystem_partners)
        investments = PlatformStrategyEngine.TYPE_INVESTMENTS.get(
            platform_type.upper(), PlatformStrategyEngine.TYPE_INVESTMENTS["PRODUCT"]
        )

        if attract >= 7 and wta >= 0.6:
            posture = "WINNER_TAKE_MOST — sprint for scale; speed matters more than near-term monetization"
        elif attract >= 5:
            posture = "CONTESTED_MARKET — differentiate on curation, trust, or vertical depth"
        else:
            posture = "WEAK_PLATFORM_ECONOMICS — reconsider platform wrap; a superior product may beat a mediocre platform"

        interpretation = (
            f"{platform_type.upper()} platform attractiveness {attract}/10 with "
            f"{wta * 100:.0f}% winner-take-all probability. Cold-start risk: {cold_start['level']} "
            f"— {cold_start['note']}. Recommended investments: {', '.join(investments)}. Posture: {posture}."
        )

        return {
            "platform_type": platform_type.upper(),
            "ecosystem_strength": eco_strength,
            "attractiveness_score": attract,
            "wta_probability": wta,
            "chicken_egg_risk": cold_start,
            "recommended_investments": investments,
            "strategic_posture": posture,
            "interpretation": interpretation,
        }


# =============================================================================
# 12. ECOSYSTEM STRATEGY
# =============================================================================


class EcosystemStrategyEngine:
    """12. Ecosystem Strategy — health, dependency, and resilience mapping."""

    KEY_DEPENDENCY_THRESHOLD = 7.0
    WEAK_RELATIONSHIP_THRESHOLD = 5.0

    @staticmethod
    def health_contribution(actor: dict) -> float:
        return round(actor["value_creation"] * 0.5 + actor["relationship_strength"] * 0.5, 2)

    @staticmethod
    def dependency_concentration(actors: list) -> float:
        total_dep = sum(a["dependency_level"] for a in actors) or 1.0
        shares = [a["dependency_level"] / total_dep for a in actors]
        return round(sum(s * s for s in shares) * 10000, 1)

    @staticmethod
    def resilience(actors: list) -> dict:
        roles = [a["role"].upper() for a in actors]
        unique_roles = set(roles)
        role_diversity = round(len(unique_roles) / len(actors), 2) if actors else 0.0
        redundant_roles = sum(1 for r in unique_roles if roles.count(r) > 1)
        concentration = EcosystemStrategyEngine.dependency_concentration(actors)

        diversity_ok = role_diversity >= 0.5
        redundancy_ok = redundant_roles >= 2
        concentration_ok = concentration < 2500

        score = sum([diversity_ok, redundancy_ok, concentration_ok]) / 3 * 10
        if score >= 7:
            level = "RESILIENT"
        elif score >= 4:
            level = "FRAGILE"
        else:
            level = "BRITTLE"
        return {
            "resilience_score": round(score, 2),
            "resilience_level": level,
            "role_diversity": role_diversity,
            "roles_with_redundancy": redundant_roles,
            "dependency_hhi": concentration,
        }

    @staticmethod
    def recommended_moves(key_deps: list, resilience_info: dict, keystone_present: bool) -> list:
        moves = []
        if key_deps:
            names = ", ".join(k["name"] for k in key_deps[:3])
            moves.append(f"Dual-source or contractually secure critical dependencies: {names}")
        if resilience_info["roles_with_redundancy"] < 2:
            moves.append("Add backup complementors in single-sourced roles to build redundancy")
        if resilience_info["dependency_hhi"] >= 2500:
            moves.append("Reduce dependency concentration — diversify the partner portfolio")
        if not keystone_present:
            moves.append("Consider stepping into the keystone role — no actor currently orchestrates value creation")
        else:
            moves.append("Deepen keystone alignment via shared roadmaps and co-investment")
        if not moves:
            moves.append("Ecosystem is healthy — expand by onboarding complementary actors")
        return moves

    @staticmethod
    def analyze(actors: list) -> dict:
        enriched = []
        key_deps = []
        for a in actors:
            hc = EcosystemStrategyEngine.health_contribution(a)
            is_key = (
                a["dependency_level"] >= EcosystemStrategyEngine.KEY_DEPENDENCY_THRESHOLD
                and a["relationship_strength"] <= EcosystemStrategyEngine.WEAK_RELATIONSHIP_THRESHOLD
            )
            entry = {**a, "health_contribution": hc, "is_key_dependency": is_key}
            enriched.append(entry)
            if is_key:
                key_deps.append(entry)

        avg_health = round(sum(e["health_contribution"] for e in enriched) / len(enriched), 2) if enriched else 0.0
        penalty = len(key_deps) * 0.4
        health_score = round(max(0.0, min(10.0, avg_health - penalty)), 2)

        resilience_info = EcosystemStrategyEngine.resilience(actors)
        keystone_present = any(a["role"].upper() == "KEYSTONE" for a in actors)
        moves = EcosystemStrategyEngine.recommended_moves(key_deps, resilience_info, keystone_present)

        if health_score >= 7 and resilience_info["resilience_level"] == "RESILIENT":
            interpretation = (
                f"Healthy ecosystem (health {health_score}/10, {resilience_info['resilience_level'].lower()} "
                "structure). Leverage this position to attract additional complementors and "
                "shape standards in your favor."
            )
        elif key_deps:
            worst = sorted(key_deps, key=lambda k: k["relationship_strength"])[0]
            interpretation = (
                f"Ecosystem carries concentrated risk: '{worst['name']}' combines high dependency "
                f"({worst['dependency_level']}/10) with weak ties ({worst['relationship_strength']}/10). "
                f"Health score {health_score}/10. Act on the recommended moves before a shock event."
            )
        else:
            interpretation = (
                f"Mediocre ecosystem health ({health_score}/10) with "
                f"{resilience_info['resilience_level'].lower()} structure. Invest in relationship "
                "depth and role redundancy to raise collective value creation."
            )

        return {
            "actors": enriched,
            "key_dependencies": [
                {"name": k["name"], "dependency_level": k["dependency_level"],
                 "relationship_strength": k["relationship_strength"]}
                for k in key_deps
            ],
            "keystone_present": keystone_present,
            "health_score": health_score,
            "average_health_contribution": avg_health,
            "resilience": resilience_info,
            "recommended_ecosystem_moves": moves,
            "interpretation": interpretation,
        }
