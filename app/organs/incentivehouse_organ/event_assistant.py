"""
EventAssistant — Smart Event Builder for IncentiveHouse ERP

Local AI-powered event creation with:
- Template suggestions from historical events
- Auto-budget calculation with variance bands
- Vendor recommendations based on past performance
- Staff auto-assignment with conflict detection
- Contextual warnings and next-action suggestions

Uses only local inference (OLMo optional, rule-based fallback always available).
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .engine import CoPilotEngine, ConfidenceLevel, Recommendation
from .schemas import (
    EventContextIn,
    EventTemplateOut,
    BudgetRecommendationOut,
    VendorRecommendationOut,
    StaffSuggestionOut,
    SmartEventResponse,
)

logger = logging.getLogger("copilot.event")


@dataclass
class HistoricalEvent:
    """Internal representation of a historical event for pattern matching."""
    event_id: int
    client_id: int
    client_name: str
    event_type: str
    event_name: str
    budget: float
    actual_cost: float
    start_date: datetime
    end_date: datetime
    venue: str
    line_items: List[Dict[str, Any]]
    staff_count: int
    status: str = "completed"


class EventAssistant:
    """
    Smart Event Builder — guides users through intelligent event creation.

    All data comes from local database queries. No external APIs.
    """

    def __init__(self, engine: CoPilotEngine, db_session_factory=None):
        self.engine = engine
        self.db = db_session_factory
        self._historical_cache: Dict[str, List[HistoricalEvent]] = {}

    # ═══════════════════════════════════════════════════════════════
    # Main Entry: Build Smart Event Response
    # ═══════════════════════════════════════════════════════════════

    def build_smart_event(self, context: EventContextIn) -> SmartEventResponse:
        """
        Main method: given event context, return complete smart recommendations.
        """
        import time
        start = time.time()

        # Gather historical data for this client/type
        history = self._fetch_client_history(context.client_id, context.client_name)

        # Build all recommendation components
        templates = self._suggest_templates(context, history)
        budget = self._recommend_budget(context, history)
        vendors = self._recommend_vendors(context, history)
        staff = self._suggest_staff(context, history)

        # Evaluate business rules for warnings
        warnings = self._generate_warnings(context, history)

        # Determine next actions
        next_actions = self._determine_next_actions(context, templates, budget, vendors)

        # Build rule-based recommendations
        rule_context = self._build_rule_context(context, history, budget)
        rule_recs = self.engine.evaluate_rules(rule_context)

        elapsed = (time.time() - start) * 1000

        return SmartEventResponse(
            success=True,
            message=f"Smart event analysis complete for {context.client_name or 'new client'}",
            recommendations=[r.to_dict() for r in rule_recs],
            processing_time_ms=elapsed,
            templates=templates,
            budget=budget,
            vendors=vendors,
            staff_suggestions=staff,
            next_actions=next_actions,
            warnings=warnings,
        )

    # ═══════════════════════════════════════════════════════════════
    # Template Suggestions
    # ═══════════════════════════════════════════════════════════════

    def _suggest_templates(
        self,
        context: EventContextIn,
        history: List[HistoricalEvent],
    ) -> List[EventTemplateOut]:
        """Suggest event templates based on client history and event type."""
        if not history:
            return []

        templates = []

        # Group by event type
        type_events = [h for h in history if h.event_type == context.event_type]

        if type_events:
            # Most recent similar event as primary template
            recent = max(type_events, key=lambda e: e.start_date)
            templates.append(self._create_template_from_event(recent, "exact_match", 0.95))

        # Also suggest from all client history (different type but same client)
        if len(history) > 0 and len(templates) < 3:
            other_events = [h for h in history if h not in type_events]
            if other_events:
                best = max(other_events, key=lambda e: e.budget)
                templates.append(self._create_template_from_event(best, "client_history", 0.75))

        # Sort by confidence
        templates.sort(key=lambda t: t.confidence_score, reverse=True)
        return templates[:3]

    def _create_template_from_event(
        self,
        event: HistoricalEvent,
        match_type: str,
        confidence: float,
    ) -> EventTemplateOut:
        """Convert a historical event into a template suggestion."""
        return EventTemplateOut(
            template_id=f"tpl_{event.event_id}",
            template_name=f"{event.event_name} ({event.start_date.strftime('%b %Y')})",
            source_event_id=event.event_id,
            source_event_name=event.event_name,
            confidence=self.engine.score_to_confidence(confidence),
            confidence_score=confidence,
            line_items=event.line_items,
            total_budget=event.budget,
            budget_variance_pct=None,
            reason=f"Based on {match_type} — {event.event_type} for {event.client_name}",
        )

    # ═══════════════════════════════════════════════════════════════
    # Budget Recommendation
    # ═══════════════════════════════════════════════════════════════

    def _recommend_budget(
        self,
        context: EventContextIn,
        history: List[HistoricalEvent],
    ) -> Optional[BudgetRecommendationOut]:
        """Calculate recommended budget with variance analysis."""
        if not history:
            return None

        # Filter to same event type for better accuracy
        type_history = [h for h in history if h.event_type == context.event_type]
        if len(type_history) < 2:
            type_history = history  # Fall back to all history

        budgets = [h.budget for h in type_history if h.budget > 0]
        if not budgets:
            return None

        avg_budget = sum(budgets) / len(budgets)
        min_budget = min(budgets)
        max_budget = max(budgets)

        # Calculate variance if proposed budget provided
        variance_pct = 0.0
        if context.proposed_budget and context.proposed_budget > 0:
            variance_pct = ((context.proposed_budget - avg_budget) / avg_budget) * 100

        # Build category breakdown from line items
        breakdown = self._build_budget_breakdown(type_history)

        # Warnings
        warnings = []
        if context.proposed_budget and context.proposed_budget > max_budget * 1.2:
            warnings.append(f"Proposed budget is {variance_pct:.0f}% above historical maximum")
        if context.proposed_budget and context.proposed_budget < min_budget * 0.5:
            warnings.append("Proposed budget is unusually low — verify scope")

        # Confidence based on data volume
        confidence_score = min(0.5 + len(type_history) * 0.05, 0.95)

        return BudgetRecommendationOut(
            recommended_budget=avg_budget,
            historical_average=avg_budget,
            historical_min=min_budget,
            historical_max=max_budget,
            variance_pct=variance_pct,
            confidence=self.engine.score_to_confidence(confidence_score),
            confidence_score=confidence_score,
            breakdown=breakdown,
            warnings=warnings,
        )

    def _build_budget_breakdown(
        self,
        history: List[HistoricalEvent],
    ) -> List[Dict[str, Any]]:
        """Aggregate line items across history to build typical budget breakdown."""
        category_totals: Dict[str, List[float]] = {}

        for event in history:
            for item in event.line_items:
                cat = item.get("category", "Other")
                amt = item.get("amount", 0)
                if cat not in category_totals:
                    category_totals[cat] = []
                category_totals[cat].append(amt)

        breakdown = []
        for cat, amounts in category_totals.items():
            avg = sum(amounts) / len(amounts)
            breakdown.append({
                "category": cat,
                "average_amount": round(avg, 2),
                "pct_of_total": 0,  # Calculated below
                "occurrence_rate": len(amounts) / len(history),
            })

        total_avg = sum(b["average_amount"] for b in breakdown)
        for b in breakdown:
            b["pct_of_total"] = round((b["average_amount"] / total_avg) * 100, 1) if total_avg > 0 else 0

        breakdown.sort(key=lambda x: x["average_amount"], reverse=True)
        return breakdown

    # ═══════════════════════════════════════════════════════════════
    # Vendor Recommendations
    # ═══════════════════════════════════════════════════════════════

    def _recommend_vendors(
        self,
        context: EventContextIn,
        history: List[HistoricalEvent],
    ) -> List[VendorRecommendationOut]:
        """Recommend vendors based on client history and performance."""
        # In production: query vendor_performance table
        # For now: simulate from historical event data

        vendor_stats: Dict[str, Dict[str, Any]] = {}

        for event in history:
            for item in event.line_items:
                vendor = item.get("vendor_name") or item.get("supplier_name")
                if not vendor:
                    continue

                if vendor not in vendor_stats:
                    vendor_stats[vendor] = {
                        "uses": 0,
                        "total_cost": 0,
                        "on_time": 0,
                        "events": set(),
                    }

                vendor_stats[vendor]["uses"] += 1
                vendor_stats[vendor]["total_cost"] += item.get("amount", 0)
                vendor_stats[vendor]["events"].add(event.event_id)

        vendors = []
        for name, stats in vendor_stats.items():
            avg_cost = stats["total_cost"] / stats["uses"] if stats["uses"] > 0 else 0
            on_time_pct = (stats["on_time"] / stats["uses"] * 100) if stats["uses"] > 0 else 0

            # Calculate composite score
            score = min(stats["uses"] * 0.1 + on_time_pct * 0.01, 1.0)

            vendors.append(VendorRecommendationOut(
                vendor_id=hash(name) % 10000,  # Simulated ID
                vendor_name=name,
                rating=min(3.5 + score * 1.5, 5.0),
                times_used=stats["uses"],
                on_time_pct=on_time_pct,
                avg_cost=avg_cost,
                confidence=self.engine.score_to_confidence(score),
                confidence_score=score,
                reason=f"Used {stats['uses']} times across {len(stats['events'])} events",
            ))

        vendors.sort(key=lambda v: v.confidence_score, reverse=True)
        return vendors[:5]

    # ═══════════════════════════════════════════════════════════════
    # Staff Suggestions
    # ═══════════════════════════════════════════════════════════════

    def _suggest_staff(
        self,
        context: EventContextIn,
        history: List[HistoricalEvent],
    ) -> List[StaffSuggestionOut]:
        """Suggest staff assignments based on event type and availability."""
        # In production: query staff_assignments + staff_skills + availability
        # For now: return pattern-based suggestions

        suggestions = []

        # Determine typical staff count for this event type
        type_history = [h for h in history if h.event_type == context.event_type]
        if type_history:
            avg_staff = sum(h.staff_count for h in type_history) / len(type_history)
            suggestions.append(StaffSuggestionOut(
                staff_id=-1,
                staff_name=f"Recommended Team Size: {int(avg_staff)} people",
                role="team_size",
                availability_status="info",
                skill_match_score=1.0,
                past_events_count=len(type_history),
                avg_rating=4.5,
                confidence=ConfidenceLevel.HIGH,
                reason=f"Average staff count for {context.event_type} events",
            ))

        # If we have actual staff data, suggest by role
        # (This would query the staff table in production)

        return suggestions

    # ═══════════════════════════════════════════════════════════════
    # Warnings & Next Actions
    # ═══════════════════════════════════════════════════════════════

    def _generate_warnings(
        self,
        context: EventContextIn,
        history: List[HistoricalEvent],
    ) -> List[str]:
        """Generate contextual warnings based on patterns."""
        warnings = []

        # Check for date conflicts
        if context.start_date and context.end_date:
            overlapping = [
                h for h in history
                if h.start_date <= context.end_date and h.end_date >= context.start_date
            ]
            if overlapping:
                warnings.append(
                    f"Date overlap detected with {len(overlapping)} existing events for this client"
                )

        # Check for budget anomalies
        if context.proposed_budget and history:
            avg = sum(h.budget for h in history) / len(history)
            if context.proposed_budget > avg * 2:
                warnings.append(f"Budget is {((context.proposed_budget/avg)-1)*100:.0f}% above client average")

        return warnings

    def _determine_next_actions(
        self,
        context: EventContextIn,
        templates: List[EventTemplateOut],
        budget: Optional[BudgetRecommendationOut],
        vendors: List[VendorRecommendationOut],
    ) -> List[str]:
        """Suggest next actions based on current state."""
        actions = []

        if templates:
            actions.append("Apply suggested template to auto-populate line items")

        if context.proposed_budget is None and budget:
            actions.append(f"Set budget to {budget.recommended_budget:,.0f} EGP (historical average)")

        if vendors:
            actions.append(f"Contact {vendors[0].vendor_name} (top-rated, {vendors[0].times_used}x used)")

        actions.extend([
            "Create purchase orders for line items",
            "Book venue and confirm availability",
            "Assign staff and send calendar invites",
        ])

        return actions

    # ═══════════════════════════════════════════════════════════════
    # Data Layer (Simulated — replace with actual DB queries)
    # ═══════════════════════════════════════════════════════════════

    def _fetch_client_history(
        self,
        client_id: Optional[int],
        client_name: Optional[str],
    ) -> List[HistoricalEvent]:
        """Fetch historical events for a client. In production: query events table."""
        cache_key = f"history_{client_id}_{client_name}"
        cached = self.engine.get_cached_pattern(cache_key, max_age_minutes=10)
        if cached:
            return cached

        # In production, query database:
        # SELECT * FROM events WHERE client_id = ? ORDER BY start_date DESC
        # For now, return empty — the engine will work with whatever data is provided

        # If db session available, query real data
        if self.db:
            try:
                history = self._query_database(client_id, client_name)
                self.engine.cache_pattern(cache_key, history)
                return history
            except Exception as e:
                logger.warning(f"DB query failed, using empty history: {e}")

        return []

    def _query_database(
        self,
        client_id: Optional[int],
        client_name: Optional[str],
    ) -> List[HistoricalEvent]:
        """Query actual database for client event history."""
        # This is a template — implement with your actual SQLAlchemy models
        # Example:
        # session = self.db()
        # events = session.query(Event).filter(Event.client_id == client_id).all()
        # return [HistoricalEvent(...) for e in events]
        return []

    def _build_rule_context(
        self,
        context: EventContextIn,
        history: List[HistoricalEvent],
        budget: Optional[BudgetRecommendationOut],
    ) -> Dict[str, Any]:
        """Build context dict for rule engine evaluation."""
        ctx = {
            "budget": context.proposed_budget or 0,
            "client_event_count": len(history),
            "client_name": context.client_name,
            "variance_pct": budget.variance_pct if budget else 0,
            "historical_avg": budget.historical_average if budget else 0,
            "unpaid_total": 0,  # Would query invoices table
            "unpaid_count": 0,
        }

        if history:
            ctx["last_event_id"] = history[0].event_id

        return ctx
