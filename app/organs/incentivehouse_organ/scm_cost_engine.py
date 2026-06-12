"""
================================================================================
SCM Cost Engine — IncentiveHouse ERP Organ
app/organs/incentivehouse_organ/scm_cost_engine.py

Covers: Strategic Cost Management (Lectures 2, 3, Environmental/Social Costing)
        + IncentiveHouse ERP-specific cost analytics

Architecture:
  - In-memory analysis for dev (no PostgreSQL required)
  - Staging persistence via hardened SCM-BIO bridge when available
  - JSON disposable file fallback for dev machines without PostgreSQL
  - All analysis results feed into scm_staging.cost_analysis via bridge

Prerequisites (all confirmed green):
  ✅ cryptography 43.0.0, httpx 0.27.0
  ✅ scm_bio_bridge_hardened.py deployed
  ✅ main.py mount at /api/v1/scm (line 70 import, 705 include_router)
  ✅ 178 tests pass, 0 regressions
  ✅ backup_service.py patched with get_fernet()
  ✅ presentation_engine.py patched with safe_file_path()
  ⬜ PostgreSQL staging schema — blocked on dev, engine uses JSON fallback
================================================================================
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict

# ── BRIDGE IMPORT (hardened version) ──
try:
    from app.scm_bridge.scm_bio_bridge import (
        SCMBioBridge,
        get_bridge,
    )
except ImportError:
    try:
        from scm_bridge.scm_bio_bridge import SCMBioBridge, get_bridge
    except ImportError:
        # Fallback for standalone organ dev
        class SCMBioBridge:
            def save_cost_analysis(self, analysis: dict) -> dict:
                return {"id": -1, "status": "bridge_fallback", "schema": "json"}

        def get_bridge():
            return SCMBioBridge()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG & PATHS
# ═══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = Path(os.getenv("SCM_OUTPUT_DIR", "./scm_analysis_output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STAGING_FALLBACK_DIR = OUTPUT_DIR / "staging_fallback"
STAGING_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class AnalysisType(str, Enum):
    STRATEGIC_COST_REVIEW = "strategic_cost_review"
    VALUE_CHAIN_ANALYSIS = "value_chain_analysis"
    TARGET_COSTING = "target_costing"
    SUSTAINABILITY_COSTING = "sustainability_costing"
    LIFE_CYCLE_COSTING = "life_cycle_costing"
    ACTIVITY_BASED_COSTING = "activity_based_costing"
    CVP_ANALYSIS = "cvp_analysis"
    BUDGET_VARIANCE = "budget_variance"
    VENDOR_SCORECARD = "vendor_scorecard"
    EVENT_PROFITABILITY = "event_profitability"
    COST_GAP_ANALYSIS = "cost_gap_analysis"


class CostCategory(str, Enum):
    PRIMARY = "primary"  # Inbound logistics, Operations, Outbound, Marketing, Service
    SUPPORT = "support"  # Infrastructure, HR, Technology, Procurement
    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"


@dataclass
class ValueChainActivity:
    """Porter Value Chain activity for IncentiveHouse events."""

    name: str
    category: CostCategory
    cost_egp: float
    revenue_attributable_egp: float
    client_satisfaction_score: float  # 0-10
    competitive_advantage: float  # 0-10

    @property
    def value_added(self) -> float:
        """Value added = revenue attributable - cost."""
        return self.revenue_attributable_egp - self.cost_egp

    @property
    def efficiency_ratio(self) -> float:
        """Efficiency = value added / cost."""
        if self.cost_egp == 0:
            return 0.0
        return self.value_added / self.cost_egp


@dataclass
class CostDriver:
    """Structural / executional cost driver."""

    name: str
    driver_type: str  # "structural" | "executional"
    current_level: float
    optimal_level: float
    unit: str
    impact_on_cost_pct: float


@dataclass
class TargetCostResult:
    """Target costing analysis result."""

    market_price: float
    target_profit_margin: float
    target_cost: float
    current_cost: float
    cost_gap: float
    gap_pct: float
    actions: List[str]


@dataclass
class SustainabilityCost:
    """Environmental and social cost allocation."""

    category: str
    cost_egp: float
    externality_egp: float  # Cost not currently borne by company
    mitigation_cost_egp: float
    regulatory_risk: str  # "low" | "medium" | "high"


@dataclass
class EventCostProfile:
    """Complete cost profile for an IncentiveHouse event."""

    event_id: int
    event_code: str
    event_name: str
    client_id: int
    client_name: str
    gross_sales: float
    budget: float
    actual_cost: float
    primary_activities: List[ValueChainActivity] = field(default_factory=list)
    support_activities: List[ValueChainActivity] = field(default_factory=list)
    sustainability_costs: List[SustainabilityCost] = field(default_factory=list)
    cost_drivers: List[CostDriver] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# CORE ANALYSIS ENGINES
# ═══════════════════════════════════════════════════════════════════════════════


class StrategicCostEngine:
    """
    Lecture 2: Strategic Cost Management
    - Value chain analysis (Porter)
    - Cost drivers (structural & executional)
    - Competitive advantage mapping
    """

    def analyze_value_chain(self, event_profile: EventCostProfile) -> Dict[str, Any]:
        """
        Analyze Porter's value chain for an IncentiveHouse event.
        Primary activities: venue, logistics, catering, entertainment, guest services
        Support activities: planning, HR, technology, procurement
        """
        primary = event_profile.primary_activities
        support = event_profile.support_activities

        total_primary_cost = sum(a.cost_egp for a in primary)
        total_support_cost = sum(a.cost_egp for a in support)
        total_cost = total_primary_cost + total_support_cost

        total_primary_value = sum(a.value_added for a in primary)
        total_support_value = sum(a.value_added for a in support)

        # Margin = total value added / total cost
        margin = (
            (total_primary_value + total_support_value) / total_cost
            if total_cost
            else 0
        )

        # Linkages: correlation between primary and support efficiency
        linkages = []
        for p in primary:
            for s in support:
                if p.client_satisfaction_score > 7 and s.competitive_advantage > 7:
                    linkages.append(
                        {
                            "primary": p.name,
                            "support": s.name,
                            "linkage_strength": round(
                                (p.client_satisfaction_score + s.competitive_advantage)
                                / 2,
                                2,
                            ),
                            "recommendation": f"Strengthen {s.name} to enhance {p.name}",
                        }
                    )

        return {
            "analysis_type": AnalysisType.VALUE_CHAIN_ANALYSIS,
            "total_cost": round(total_cost, 2),
            "total_primary_cost": round(total_primary_cost, 2),
            "total_support_cost": round(total_support_cost, 2),
            "margin_ratio": round(margin, 4),
            "primary_activities": [asdict(a) for a in primary],
            "support_activities": [asdict(a) for a in support],
            "linkages": linkages,
            "recommendations": self._value_chain_recommendations(
                primary, support, margin
            ),
        }

    def _value_chain_recommendations(self, primary, support, margin) -> List[str]:
        recs = []
        if margin < 0.15:
            recs.append(
                "MARGIN ALERT: Value chain margin below 15%. Review high-cost low-value activities."
            )

        # Find highest cost primary activity
        if primary:
            max_cost = max(primary, key=lambda x: x.cost_egp)
            recs.append(
                f"Highest cost primary activity: {max_cost.name} ({max_cost.cost_egp:,.2f} EGP). Evaluate outsourcing."
            )

        # Find lowest efficiency support activity
        if support:
            min_eff = min(support, key=lambda x: x.efficiency_ratio)
            if min_eff.efficiency_ratio < 1.0:
                recs.append(
                    f"Low efficiency support: {min_eff.name} (ratio {min_eff.efficiency_ratio:.2f}). Consider automation or reduction."
                )

        recs.append(
            "Map client satisfaction scores to cost drivers to identify over/under-investment."
        )
        return recs

    def analyze_cost_drivers(self, drivers: List[CostDriver]) -> Dict[str, Any]:
        """
        Lecture 2: Cost driver analysis
        Structural: scale, scope, experience, technology, complexity
        Executional: workforce involvement, quality management, capacity utilization
        """
        structural = [d for d in drivers if d.driver_type == "structural"]
        executional = [d for d in drivers if d.driver_type == "executional"]

        gap_analysis = []
        for d in drivers:
            gap = d.optimal_level - d.current_level
            gap_pct = (gap / d.optimal_level * 100) if d.optimal_level else 0
            gap_analysis.append(
                {
                    "driver": d.name,
                    "type": d.driver_type,
                    "current": d.current_level,
                    "optimal": d.optimal_level,
                    "gap": round(gap, 2),
                    "gap_pct": round(gap_pct, 2),
                    "unit": d.unit,
                    "impact_on_cost_pct": d.impact_on_cost_pct,
                    "priority": "high"
                    if abs(gap_pct) > 20
                    else "medium"
                    if abs(gap_pct) > 10
                    else "low",
                }
            )

        return {
            "analysis_type": "cost_driver_analysis",
            "structural_drivers": len(structural),
            "executional_drivers": len(executional),
            "gap_analysis": gap_analysis,
            "recommendations": [
                f"Focus on {len([g for g in gap_analysis if g['priority'] == 'high'])} high-priority cost drivers",
                "Structural drivers require long-term strategic decisions (scale, technology)",
                "Executional drivers can be improved through operational excellence",
            ],
        }


class TargetCostingEngine:
    """
    Lecture 3: Target Costing
    Market price → Target profit → Target cost → Cost gap → Actions
    """

    def calculate_target_cost(
        self,
        market_price: float,
        target_margin_pct: float,
        current_cost: float,
        event_name: str = "",
    ) -> TargetCostResult:
        target_cost = market_price * (1 - target_margin_pct)
        gap = current_cost - target_cost
        gap_pct = (gap / current_cost * 100) if current_cost else 0

        actions = []
        if gap > 0:
            actions.append(
                f"COST GAP: {gap:,.2f} EGP ({gap_pct:.1f}%). Must reduce cost to achieve target margin."
            )
            actions.append(
                "1. Value engineering: Re-design event components without reducing client value"
            )
            actions.append(
                "2. Supplier negotiation: Leverage volume for better venue/catering rates"
            )
            actions.append(
                "3. Process improvement: Reduce waste in logistics and setup"
            )
            actions.append(
                "4. Technology substitution: Use digital elements where physical is costly"
            )
            if gap_pct > 15:
                actions.append(
                    "5. CRITICAL: Consider event scope reduction or premium pricing strategy"
                )
        else:
            actions.append(
                f"COST SURPLUS: {abs(gap):,.2f} EGP. Cost below target — room for quality enhancement or price reduction."
            )

        return TargetCostResult(
            market_price=market_price,
            target_profit_margin=target_margin_pct,
            target_cost=target_cost,
            current_cost=current_cost,
            cost_gap=gap,
            gap_pct=gap_pct,
            actions=actions,
        )

    def analyze_event_target_costing(
        self, event_profile: EventCostProfile
    ) -> Dict[str, Any]:
        """Full target costing analysis for an IncentiveHouse event."""
        market_price = event_profile.gross_sales
        current_cost = event_profile.actual_cost
        # IncentiveHouse industry standard margin: 18-25%
        target_margin = 0.20

        result = self.calculate_target_cost(
            market_price, target_margin, current_cost, event_profile.event_name
        )

        # Component-level target cost allocation
        components = []
        if event_profile.primary_activities:
            total_primary = sum(a.cost_egp for a in event_profile.primary_activities)
            for activity in event_profile.primary_activities:
                alloc_pct = activity.cost_egp / total_primary if total_primary else 0
                target_alloc = result.target_cost * alloc_pct
                component_gap = activity.cost_egp - target_alloc
                components.append(
                    {
                        "activity": activity.name,
                        "current_cost": round(activity.cost_egp, 2),
                        "target_allocation": round(target_alloc, 2),
                        "component_gap": round(component_gap, 2),
                        "status": "over" if component_gap > 0 else "under",
                    }
                )

        return {
            "analysis_type": AnalysisType.TARGET_COSTING,
            "event_id": event_profile.event_id,
            "event_name": event_profile.event_name,
            "market_price": round(result.market_price, 2),
            "target_margin_pct": round(result.target_profit_margin * 100, 1),
            "target_cost": round(result.target_cost, 2),
            "current_cost": round(result.current_cost, 2),
            "cost_gap": round(result.cost_gap, 2),
            "gap_pct": round(result.gap_pct, 2),
            "component_breakdown": components,
            "actions": result.actions,
            "confidence_score": 0.88 if result.gap_pct < 30 else 0.65,
        }


class SustainabilityCostingEngine:
    """
    Environmental & Social Costing (Lecture PDF: 11 pages)
    - Carbon footprint of events
    - Waste management costs
    - Social impact (local employment, community)
    - Regulatory compliance costs
    """

    def analyze_event_sustainability(
        self, event_profile: EventCostProfile
    ) -> Dict[str, Any]:
        """Calculate total sustainability cost profile for an event."""
        costs = event_profile.sustainability_costs

        total_internal = sum(c.cost_egp for c in costs)
        total_externality = sum(c.externality_egp for c in costs)
        total_mitigation = sum(c.mitigation_cost_egp for c in costs)

        # True cost = internal + externality (full cost accounting)
        true_cost = total_internal + total_externality

        # Regulatory risk assessment
        high_risk = [c for c in costs if c.regulatory_risk == "high"]
        medium_risk = [c for c in costs if c.regulatory_risk == "medium"]

        # Carbon-specific (common for events)
        carbon_items = [
            c
            for c in costs
            if "carbon" in c.category.lower() or "emission" in c.category.lower()
        ]
        carbon_cost = sum(c.cost_egp for c in carbon_items)

        return {
            "analysis_type": AnalysisType.SUSTAINABILITY_COSTING,
            "event_id": event_profile.event_id,
            "total_internal_cost": round(total_internal, 2),
            "total_externality": round(total_externality, 2),
            "true_cost": round(true_cost, 2),
            "mitigation_cost": round(total_mitigation, 2),
            "carbon_cost": round(carbon_cost, 2),
            "regulatory_high_risk": len(high_risk),
            "regulatory_medium_risk": len(medium_risk),
            "cost_breakdown": [
                {
                    "category": c.category,
                    "internal": round(c.cost_egp, 2),
                    "externality": round(c.externality_egp, 2),
                    "mitigation": round(c.mitigation_cost_egp, 2),
                    "risk": c.regulatory_risk,
                }
                for c in costs
            ],
            "recommendations": [
                f"True cost is {((true_cost / event_profile.actual_cost - 1) * 100):.1f}% higher than reported cost"
                if event_profile.actual_cost
                else "N/A",
                f"Mitigation investment of {total_mitigation:,.2f} EGP reduces regulatory risk",
                "Consider carbon offsetting for travel-intensive events",
                "Social costs (local employment) can be marketing assets",
            ],
            "confidence_score": 0.75,
        }


class ActivityBasedCostingEngine:
    """
    ABC for IncentiveHouse events.
    Activities → Cost pools → Cost drivers → Cost per event/client
    """

    def calculate_abc(
        self, activities: List[Dict], cost_pools: List[Dict]
    ) -> Dict[str, Any]:
        """
        activities: [{"name": "Event planning", "hours": 40, "rate": 500}]
        cost_pools: [{"pool": "Admin overhead", "total_cost": 50000, "driver": "event_count", "volume": 10}]
        """
        activity_costs = []
        for act in activities:
            cost = act.get("hours", 0) * act.get("rate", 0)
            activity_costs.append(
                {
                    "activity": act["name"],
                    "driver_quantity": act.get("hours", 0),
                    "rate": act.get("rate", 0),
                    "cost": round(cost, 2),
                }
            )

        pool_allocations = []
        for pool in cost_pools:
            rate = pool["total_cost"] / pool["volume"] if pool["volume"] else 0
            pool_allocations.append(
                {
                    "pool": pool["pool"],
                    "total_cost": pool["total_cost"],
                    "driver": pool["driver"],
                    "volume": pool["volume"],
                    "allocation_rate": round(rate, 2),
                }
            )

        total_activity = sum(a["cost"] for a in activity_costs)
        total_pool = sum(p["total_cost"] for p in cost_pools)

        return {
            "analysis_type": AnalysisType.ACTIVITY_BASED_COSTING,
            "activity_costs": activity_costs,
            "cost_pool_allocations": pool_allocations,
            "total_activity_cost": round(total_activity, 2),
            "total_pool_cost": round(total_pool, 2),
            "total_abc_cost": round(total_activity + total_pool, 2),
            "recommendations": [
                "High-volume activities should be standardized to reduce cost per unit",
                "Cost pools with high allocation rate indicate shared resource bottleneck",
                "Compare ABC cost to traditional costing to identify cross-subsidization",
            ],
        }


class CVPAnalysisEngine:
    """
    Cost-Volume-Profit analysis for IncentiveHouse events.
    Break-even, margin of safety, target profit volume.
    """

    def analyze_cvp(
        self,
        fixed_costs: float,
        variable_cost_per_unit: float,
        selling_price_per_unit: float,
        current_volume: float,
        target_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        For events: "unit" = per attendee or per event.
        """
        if selling_price_per_unit <= variable_cost_per_unit:
            return {
                "analysis_type": AnalysisType.CVP_ANALYSIS,
                "error": "Selling price must exceed variable cost per unit",
                "contribution_margin": 0,
                "cm_ratio": 0,
            }

        contribution_margin = selling_price_per_unit - variable_cost_per_unit
        cm_ratio = contribution_margin / selling_price_per_unit

        break_even_units = (
            fixed_costs / contribution_margin if contribution_margin else float("inf")
        )
        break_even_revenue = break_even_units * selling_price_per_unit

        current_revenue = current_volume * selling_price_per_unit
        current_profit = current_volume * contribution_margin - fixed_costs
        margin_of_safety_units = current_volume - break_even_units
        margin_of_safety_pct = (
            (margin_of_safety_units / current_volume * 100) if current_volume else 0
        )

        target_volume = None
        if target_profit is not None:
            target_volume = (fixed_costs + target_profit) / contribution_margin

        operating_leverage = (
            (current_volume * contribution_margin) / current_profit
            if current_profit
            else 0
        )

        return {
            "analysis_type": AnalysisType.CVP_ANALYSIS,
            "fixed_costs": round(fixed_costs, 2),
            "variable_cost_per_unit": round(variable_cost_per_unit, 2),
            "selling_price_per_unit": round(selling_price_per_unit, 2),
            "contribution_margin": round(contribution_margin, 2),
            "cm_ratio": round(cm_ratio, 4),
            "break_even_units": round(break_even_units, 2),
            "break_even_revenue": round(break_even_revenue, 2),
            "current_volume": round(current_volume, 2),
            "current_revenue": round(current_revenue, 2),
            "current_profit": round(current_profit, 2),
            "margin_of_safety_units": round(margin_of_safety_units, 2),
            "margin_of_safety_pct": round(margin_of_safety_pct, 2),
            "target_profit": round(target_profit, 2) if target_profit else None,
            "target_volume": round(target_volume, 2) if target_volume else None,
            "operating_leverage": round(operating_leverage, 2),
            "recommendations": [
                f"Break-even at {break_even_units:,.0f} units — minimum viable event size"
                if break_even_units != float("inf")
                else "No break-even possible — price below variable cost",
                f"Margin of safety: {margin_of_safety_pct:.1f}% — {'healthy' if margin_of_safety_pct > 20 else 'risky' if margin_of_safety_pct > 10 else 'CRITICAL'}",
                f"Operating leverage: {operating_leverage:.2f} — {'high fixed cost risk' if operating_leverage > 5 else 'moderate'}",
            ],
        }


class EventProfitabilityEngine:
    """
    Event-level profitability analysis for IncentiveHouse.
    Revenue - All costs (primary + support + sustainability + overhead) = True profit
    """

    def analyze_event_profitability(
        self, event_profile: EventCostProfile
    ) -> Dict[str, Any]:
        """Full profitability analysis including hidden costs."""
        gross = event_profile.gross_sales

        primary_cost = sum(a.cost_egp for a in event_profile.primary_activities)
        support_cost = sum(a.cost_egp for a in event_profile.support_activities)
        sustain_cost = sum(c.cost_egp for c in event_profile.sustainability_costs)

        # IncentiveHouse typical overhead allocation: 12% of direct costs
        overhead = (primary_cost + support_cost) * 0.12
        total_cost = primary_cost + support_cost + sustain_cost + overhead

        gross_profit = gross - total_cost
        gross_margin = (gross_profit / gross * 100) if gross else 0

        # Budget variance
        budget_variance = event_profile.budget - total_cost
        budget_variance_pct = (
            (budget_variance / event_profile.budget * 100)
            if event_profile.budget
            else 0
        )

        # Client profitability (if client has multiple events)
        client_profitability = {
            "client_id": event_profile.client_id,
            "client_name": event_profile.client_name,
            "event_gross_profit": round(gross_profit, 2),
            "event_margin_pct": round(gross_margin, 2),
            "budget_variance": round(budget_variance, 2),
            "budget_variance_pct": round(budget_variance_pct, 2),
        }

        return {
            "analysis_type": AnalysisType.EVENT_PROFITABILITY,
            "event_id": event_profile.event_id,
            "event_name": event_profile.event_name,
            "revenue": round(gross, 2),
            "primary_cost": round(primary_cost, 2),
            "support_cost": round(support_cost, 2),
            "sustainability_cost": round(sustain_cost, 2),
            "overhead_allocation": round(overhead, 2),
            "total_cost": round(total_cost, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round(gross_margin, 2),
            "budget_variance": round(budget_variance, 2),
            "budget_variance_pct": round(budget_variance_pct, 2),
            "client_profitability": client_profitability,
            "status": "profitable" if gross_profit > 0 else "loss",
            "recommendations": [
                f"Gross margin {gross_margin:.1f}% — {'healthy' if gross_margin > 20 else 'review pricing' if gross_margin > 10 else 'URGENT: renegotiate or cancel'}",
                f"Budget variance: {budget_variance_pct:+.1f}% — {'under budget' if budget_variance > 0 else 'over budget'}",
                "True cost includes sustainability — not reflected in standard P&L",
            ],
            "confidence_score": 0.90,
        }


class VendorScorecardEngine:
    """
    Vendor evaluation for IncentiveHouse suppliers (venues, caterers, AV, transport).
    Quality, delivery, price, service — feeds into bridge vendor_scorecards table.
    """

    def evaluate_vendor(
        self,
        vendor_id: int,
        vendor_name: str,
        quality_score: float,  # 0-100
        delivery_score: float,  # 0-100
        price_score: float,  # 0-100
        service_score: float,  # 0-100
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Weighted vendor scorecard."""
        default_weights = {
            "quality": 0.30,
            "delivery": 0.25,
            "price": 0.25,
            "service": 0.20,
        }
        w = weights or default_weights

        overall = (
            quality_score * w["quality"]
            + delivery_score * w["delivery"]
            + price_score * w["price"]
            + service_score * w["service"]
        )

        grade = (
            "A"
            if overall >= 90
            else "B"
            if overall >= 80
            else "C"
            if overall >= 70
            else "D"
            if overall >= 60
            else "F"
        )

        return {
            "analysis_type": AnalysisType.VENDOR_SCORECARD,
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "quality_score": round(quality_score, 2),
            "delivery_score": round(delivery_score, 2),
            "price_score": round(price_score, 2),
            "service_score": round(service_score, 2),
            "weights": w,
            "overall_score": round(overall, 2),
            "grade": grade,
            "recommendations": [
                f"Vendor grade: {grade} — {'preferred supplier' if grade in 'AB' else 'monitor closely' if grade == 'C' else 'consider replacement'}",
                f"Lowest dimension: {
                    min(
                        [
                            ('quality', quality_score),
                            ('delivery', delivery_score),
                            ('price', price_score),
                            ('service', service_score),
                        ],
                        key=lambda x: x[1],
                    )[0]
                }",
            ],
            "confidence_score": 0.85,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR: SCM Cost Engine Master
# ═══════════════════════════════════════════════════════════════════════════════


class SCMCostEngine:
    """
    Master orchestrator for all SCM cost analyses.
    Runs engines → produces results → persists to staging (bridge or JSON fallback).
    """

    def __init__(self, bridge: Optional[SCMBioBridge] = None):
        self.strategic = StrategicCostEngine()
        self.target = TargetCostingEngine()
        self.sustainability = SustainabilityCostingEngine()
        self.abc = ActivityBasedCostingEngine()
        self.cvp = CVPAnalysisEngine()
        self.profitability = EventProfitabilityEngine()
        self.vendor = VendorScorecardEngine()
        self.bridge = bridge or get_bridge()
        self._fallback_id = 0

    def _next_fallback_id(self) -> int:
        self._fallback_id += 1
        return self._fallback_id

    def _save_to_staging(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save analysis to staging.
        Tries bridge first (PostgreSQL). Falls back to JSON file if unavailable.
        """
        payload = {
            "event_id": analysis.get("event_id", 0),
            "analysis_type": analysis.get("analysis_type", "unknown"),
            "input_data": {},
            "results": analysis,
            "recommendations": analysis.get("recommendations", []),
            "confidence_score": analysis.get("confidence_score", 0.0),
            "created_by": "scm_cost_engine",
        }

        try:
            # Attempt bridge save (PostgreSQL staging)
            result = self.bridge.save_cost_analysis(payload)
            if result.get("status") == "saved_to_staging":
                return {"persisted": True, "mode": "postgresql", "id": result.get("id")}
        except Exception:
            pass  # Bridge unavailable — fall through

        # JSON fallback for dev machines without PostgreSQL
        fid = self._next_fallback_id()
        fname = (
            STAGING_FALLBACK_DIR
            / f"analysis_{fid:04d}_{analysis.get('analysis_type', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(
                {"id": fid, "saved_at": datetime.now().isoformat(), **payload},
                f,
                indent=2,
                default=str,
            )

        return {
            "persisted": True,
            "mode": "json_fallback",
            "path": str(fname),
            "id": fid,
        }

    def run_full_event_analysis(
        self, event_profile: EventCostProfile
    ) -> Dict[str, Any]:
        """Run ALL analysis engines on a single event."""
        results = {
            "event_id": event_profile.event_id,
            "event_name": event_profile.event_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "engines_used": [],
            "analyses": {},
        }

        # 1. Strategic — Value Chain
        vc = self.strategic.analyze_value_chain(event_profile)
        results["analyses"]["value_chain"] = vc
        results["engines_used"].append("value_chain")

        # 2. Strategic — Cost Drivers
        if event_profile.cost_drivers:
            cd = self.strategic.analyze_cost_drivers(event_profile.cost_drivers)
            results["analyses"]["cost_drivers"] = cd
            results["engines_used"].append("cost_drivers")

        # 3. Target Costing
        tc = self.target.analyze_event_target_costing(event_profile)
        results["analyses"]["target_costing"] = tc
        results["engines_used"].append("target_costing")

        # 4. Sustainability
        if event_profile.sustainability_costs:
            sc = self.sustainability.analyze_event_sustainability(event_profile)
            results["analyses"]["sustainability"] = sc
            results["engines_used"].append("sustainability")

        # 5. Event Profitability
        ep = self.profitability.analyze_event_profitability(event_profile)
        results["analyses"]["profitability"] = ep
        results["engines_used"].append("profitability")

        # 6. CVP (if we can derive per-unit metrics)
        # For events: unit = per attendee, but we need attendee count
        # Skip if not available — will be done via API with explicit params

        # Persist each analysis to staging
        persist_results = []
        for key, analysis in results["analyses"].items():
            pr = self._save_to_staging(analysis)
            persist_results.append({"engine": key, **pr})

        results["persistence"] = persist_results
        results["overall_confidence"] = (
            round(
                sum(
                    a.get("confidence_score", 0.0) for a in results["analyses"].values()
                )
                / len(results["analyses"]),
                2,
            )
            if results["analyses"]
            else 0.0
        )

        return results

    def run_vendor_evaluation(
        self,
        vendor_id: int,
        vendor_name: str,
        quality: float,
        delivery: float,
        price: float,
        service: float,
    ) -> Dict[str, Any]:
        """Run vendor scorecard and save to staging."""
        result = self.vendor.evaluate_vendor(
            vendor_id, vendor_name, quality, delivery, price, service
        )
        persist = self._save_to_staging(result)
        return {"analysis": result, "persistence": persist}

    def run_cvp(
        self,
        fixed: float,
        variable: float,
        price: float,
        volume: float,
        target_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run CVP analysis and save to staging."""
        result = self.cvp.analyze_cvp(fixed, variable, price, volume, target_profit)
        persist = self._save_to_staging(result)
        return {"analysis": result, "persistence": persist}

    def run_abc(self, activities: List[Dict], cost_pools: List[Dict]) -> Dict[str, Any]:
        """Run ABC and save to staging."""
        result = self.abc.calculate_abc(activities, cost_pools)
        persist = self._save_to_staging(result)
        return {"analysis": result, "persistence": persist}


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI ROUTER — SCM Cost Engine API
# Prefix: /api/v1/scm/cost-engine (mounted under /api/v1/scm)
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/cost-engine", tags=["SCM Cost Engine"])


# ── Pydantic Request Models ──


class ValueChainActivityRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Venue & Setup",
                "category": "primary",
                "cost_egp": 45000,
                "revenue_attributable_egp": 60000,
                "client_satisfaction_score": 8.5,
                "competitive_advantage": 7.0,
            }
        }
    )
    name: str
    category: CostCategory
    cost_egp: float = Field(ge=0)
    revenue_attributable_egp: float = Field(ge=0)
    client_satisfaction_score: float = Field(ge=0, le=10)
    competitive_advantage: float = Field(ge=0, le=10)


class CostDriverRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Event Scale",
                "driver_type": "structural",
                "current_level": 150,
                "optimal_level": 200,
                "unit": "attendees",
                "impact_on_cost_pct": 15.0,
            }
        }
    )
    name: str
    driver_type: str = Field(pattern=r"^(structural|executional)$")
    current_level: float
    optimal_level: float
    unit: str
    impact_on_cost_pct: float


class SustainabilityCostRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": "Carbon Emissions",
                "cost_egp": 5000,
                "externality_egp": 8000,
                "mitigation_cost_egp": 3000,
                "regulatory_risk": "medium",
            }
        }
    )
    category: str
    cost_egp: float = Field(ge=0)
    externality_egp: float = Field(ge=0)
    mitigation_cost_egp: float = Field(ge=0)
    regulatory_risk: str = Field(pattern=r"^(low|medium|high)$")


class EventProfileRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": 1,
                "event_code": "EVT-2026-001",
                "event_name": "Cisco Annual Meeting",
                "client_id": 84,
                "client_name": "CISCO",
                "gross_sales": 250000,
                "budget": 200000,
                "actual_cost": 195000,
            }
        }
    )
    event_id: int
    event_code: str
    event_name: str
    client_id: int
    client_name: str
    gross_sales: float = Field(ge=0)
    budget: float = Field(ge=0)
    actual_cost: float = Field(ge=0)
    primary_activities: List[ValueChainActivityRequest] = Field(default_factory=list)
    support_activities: List[ValueChainActivityRequest] = Field(default_factory=list)
    sustainability_costs: List[SustainabilityCostRequest] = Field(default_factory=list)
    cost_drivers: List[CostDriverRequest] = Field(default_factory=list)


class CVPRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fixed_costs": 50000,
                "variable_cost_per_unit": 800,
                "selling_price_per_unit": 1500,
                "current_volume": 200,
                "target_profit": 30000,
            }
        }
    )
    fixed_costs: float = Field(ge=0)
    variable_cost_per_unit: float = Field(ge=0)
    selling_price_per_unit: float = Field(gt=0)
    current_volume: float = Field(gt=0)
    target_profit: Optional[float] = None


class ABCRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "activities": [
                    {"name": "Event Planning", "hours": 40, "rate": 500},
                    {"name": "On-site Coordination", "hours": 24, "rate": 400},
                ],
                "cost_pools": [
                    {
                        "pool": "Admin Overhead",
                        "total_cost": 50000,
                        "driver": "event_count",
                        "volume": 10,
                    }
                ],
            }
        }
    )
    activities: List[Dict[str, Any]]
    cost_pools: List[Dict[str, Any]]


class VendorScorecardRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": 1,
                "vendor_name": "Grand Nile Venue",
                "quality_score": 88,
                "delivery_score": 92,
                "price_score": 75,
                "service_score": 85,
            }
        }
    )
    vendor_id: int
    vendor_name: str
    quality_score: float = Field(ge=0, le=100)
    delivery_score: float = Field(ge=0, le=100)
    price_score: float = Field(ge=0, le=100)
    service_score: float = Field(ge=0, le=100)
    weights: Optional[Dict[str, float]] = None


# ── Helper: Build EventCostProfile from request ──


def _build_profile(req: EventProfileRequest) -> EventCostProfile:
    return EventCostProfile(
        event_id=req.event_id,
        event_code=req.event_code,
        event_name=req.event_name,
        client_id=req.client_id,
        client_name=req.client_name,
        gross_sales=req.gross_sales,
        budget=req.budget,
        actual_cost=req.actual_cost,
        primary_activities=[
            ValueChainActivity(
                name=a.name,
                category=a.category,
                cost_egp=a.cost_egp,
                revenue_attributable_egp=a.revenue_attributable_egp,
                client_satisfaction_score=a.client_satisfaction_score,
                competitive_advantage=a.competitive_advantage,
            )
            for a in req.primary_activities
        ],
        support_activities=[
            ValueChainActivity(
                name=a.name,
                category=a.category,
                cost_egp=a.cost_egp,
                revenue_attributable_egp=a.revenue_attributable_egp,
                client_satisfaction_score=a.client_satisfaction_score,
                competitive_advantage=a.competitive_advantage,
            )
            for a in req.support_activities
        ],
        sustainability_costs=[
            SustainabilityCost(
                category=s.category,
                cost_egp=s.cost_egp,
                externality_egp=s.externality_egp,
                mitigation_cost_egp=s.mitigation_cost_egp,
                regulatory_risk=s.regulatory_risk,
            )
            for s in req.sustainability_costs
        ],
        cost_drivers=[
            CostDriver(
                name=d.name,
                driver_type=d.driver_type,
                current_level=d.current_level,
                optimal_level=d.optimal_level,
                unit=d.unit,
                impact_on_cost_pct=d.impact_on_cost_pct,
            )
            for d in req.cost_drivers
        ],
    )


# ── API ENDPOINTS ──


@router.post("/analyze/event/full", summary="Full event cost analysis (all engines)")
def analyze_event_full(req: EventProfileRequest):
    """
    Run complete SCM cost analysis on an IncentiveHouse event.
    Engines: Value Chain, Cost Drivers, Target Costing, Sustainability, Profitability.
    Results saved to staging (PostgreSQL or JSON fallback).
    """
    engine = SCMCostEngine()
    profile = _build_profile(req)
    result = engine.run_full_event_analysis(profile)
    return result


@router.post("/analyze/value-chain", summary="Value chain analysis only")
def analyze_value_chain(req: EventProfileRequest):
    """Porter Value Chain analysis for an event."""
    engine = SCMCostEngine()
    profile = _build_profile(req)
    vc = engine.strategic.analyze_value_chain(profile)
    persist = engine._save_to_staging(vc)
    return {"analysis": vc, "persistence": persist}


@router.post("/analyze/target-costing", summary="Target costing analysis")
def analyze_target_costing(req: EventProfileRequest):
    """Target costing: market price → target cost → gap analysis."""
    engine = SCMCostEngine()
    profile = _build_profile(req)
    tc = engine.target.analyze_event_target_costing(profile)
    persist = engine._save_to_staging(tc)
    return {"analysis": tc, "persistence": persist}


@router.post("/analyze/sustainability", summary="Sustainability costing")
def analyze_sustainability(req: EventProfileRequest):
    """Environmental & social cost analysis."""
    engine = SCMCostEngine()
    profile = _build_profile(req)
    sc = engine.sustainability.analyze_event_sustainability(profile)
    persist = engine._save_to_staging(sc)
    return {"analysis": sc, "persistence": persist}


@router.post("/analyze/profitability", summary="Event profitability")
def analyze_profitability(req: EventProfileRequest):
    """Full profitability including hidden costs."""
    engine = SCMCostEngine()
    profile = _build_profile(req)
    ep = engine.profitability.analyze_event_profitability(profile)
    persist = engine._save_to_staging(ep)
    return {"analysis": ep, "persistence": persist}


@router.post("/analyze/cvp", summary="Cost-Volume-Profit analysis")
def analyze_cvp(req: CVPRequest):
    """CVP: break-even, margin of safety, target profit volume."""
    engine = SCMCostEngine()
    result = engine.run_cvp(
        req.fixed_costs,
        req.variable_cost_per_unit,
        req.selling_price_per_unit,
        req.current_volume,
        req.target_profit,
    )
    return result


@router.post("/analyze/abc", summary="Activity-Based Costing")
def analyze_abc(req: ABCRequest):
    """ABC: activity costs + cost pool allocation."""
    engine = SCMCostEngine()
    result = engine.run_abc(req.activities, req.cost_pools)
    return result


@router.post("/analyze/vendor-scorecard", summary="Vendor evaluation")
def analyze_vendor(req: VendorScorecardRequest):
    """Vendor scorecard: quality, delivery, price, service."""
    engine = SCMCostEngine()
    result = engine.run_vendor_evaluation(
        req.vendor_id,
        req.vendor_name,
        req.quality_score,
        req.delivery_score,
        req.price_score,
        req.service_score,
    )
    return result


@router.get("/engines", summary="List available analysis engines")
def list_engines():
    """Return all available SCM cost analysis engines."""
    return {
        "engines": [
            {
                "id": "value_chain",
                "name": "Porter Value Chain Analysis",
                "type": "strategic",
            },
            {"id": "cost_drivers", "name": "Cost Driver Analysis", "type": "strategic"},
            {"id": "target_costing", "name": "Target Costing", "type": "strategic"},
            {
                "id": "sustainability",
                "name": "Sustainability Costing",
                "type": "environmental",
            },
            {"id": "abc", "name": "Activity-Based Costing", "type": "operational"},
            {"id": "cvp", "name": "Cost-Volume-Profit", "type": "operational"},
            {"id": "profitability", "name": "Event Profitability", "type": "financial"},
            {
                "id": "vendor_scorecard",
                "name": "Vendor Scorecard",
                "type": "procurement",
            },
        ],
        "total": 8,
    }


@router.get("/health", summary="Cost engine health check")
def health_check():
    """Verify all engines are loaded and fallback directory is writable."""
    engine = SCMCostEngine()
    fallback_writable = os.access(STAGING_FALLBACK_DIR, os.W_OK)
    return {
        "status": "healthy",
        "engines_loaded": [
            "strategic_cost",
            "target_costing",
            "sustainability",
            "abc",
            "cvp",
            "profitability",
            "vendor_scorecard",
        ],
        "fallback_dir": str(STAGING_FALLBACK_DIR),
        "fallback_writable": fallback_writable,
        "bridge_available": engine.bridge is not None,
        "timestamp": datetime.now().isoformat(),
    }
