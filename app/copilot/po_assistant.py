"""
Intelligent PO Generator — Co-Pilot Module B.
Auto-generates POs from events, scores suppliers, enforces budget guardrails.
"""

import json
from typing import List, Dict, Optional, Any
from .engine import CoPilotEngine
from .schemas import (
    POGenerateRequest, POGenerateResponse,
    Suggestion, ConfidenceLevel,
)

SUPPLIER_DB = [
    {"name": "Elite Catering Co.", "category": "catering", "score": 98,
     "avg_rating": 4.8, "on_time_pct": 97, "avg_delay_days": 0.5,
     "preferred": True, "pending_deliveries": 2},
    {"name": "AV Pro Solutions", "category": "av", "score": 92,
     "avg_rating": 4.5, "on_time_pct": 94, "avg_delay_days": 1.0,
     "preferred": True, "pending_deliveries": 0},
    {"name": "Grand Decor Studio", "category": "decor", "score": 88,
     "avg_rating": 4.3, "on_time_pct": 91, "avg_delay_days": 1.5,
     "preferred": False, "pending_deliveries": 1},
    {"name": "Budget Supplies Co.", "category": "general", "score": 72,
     "avg_rating": 3.8, "on_time_pct": 85, "avg_delay_days": 3.0,
     "preferred": False, "pending_deliveries": 0},
    {"name": "Premium Events Ltd.", "category": "general", "score": 95,
     "avg_rating": 4.9, "on_time_pct": 99, "avg_delay_days": 0.2,
     "preferred": True, "pending_deliveries": 3},
]


class POAssistant:
    """
    Intelligent PO generation and supplier optimization.
    """

    def __init__(self, engine: CoPilotEngine):
        self.engine = engine

    def generate(self, request: POGenerateRequest) -> POGenerateResponse:
        suggestions = []
        duplicate_warnings = []

        supplier = self._find_supplier(request.supplier_name or "")
        budget_status = "ok"
        total = 0.0
        remaining_after = request.budget_remaining

        if request.line_items:
            for item in request.line_items:
                total += item.get("total", item.get("quantity", 1) * item.get("rate", 0))

        if request.budget_remaining is not None:
            if total > request.budget_remaining:
                budget_status = "over_budget"
                remaining_after = 0
                suggestions.append(Suggestion(
                    id="budget_exceeded", type="error",
                    title="PO exceeds remaining budget",
                    description=f"Total ${total:,.2f} exceeds remaining ${request.budget_remaining:,.2f}",
                    confidence=self.engine.confidence(0.98),
                ))
            else:
                remaining_after = request.budget_remaining - total
                if remaining_after < request.budget_remaining * 0.1:
                    budget_status = "warning"
                    suggestions.append(Suggestion(
                        id="budget_low", type="warning",
                        title=f"Only ${remaining_after:,.2f} remaining after this PO",
                        description="Less than 10% of remaining budget will be left.",
                        confidence=self.engine.confidence(0.90),
                    ))

        if supplier:
            if supplier.get("pending_deliveries", 0) > 2:
                suggestions.append(Suggestion(
                    id="supplier_backlog", type="warning",
                    title=f"Supplier has {supplier['pending_deliveries']} pending deliveries",
                    description="Consider rush fee or alternative supplier.",
                    action="override",
                    confidence=self.engine.confidence(0.85),
                ))

        po_lines = self._build_po_lines(request)

        supplier_score = supplier["score"] if supplier else None

        return POGenerateResponse(
            po_lines=po_lines,
            total_amount=total,
            budget_status=budget_status,
            budget_remaining_after=remaining_after,
            supplier_score=supplier_score,
            duplicate_warnings=duplicate_warnings,
            suggestions=suggestions,
            confidence=self.engine.confidence(0.88),
        )

    def optimize_supplier(self, line_items: List[Dict], preferred_only: bool = False) -> List[Dict]:
        candidates = [s for s in SUPPLIER_DB if not preferred_only or s.get("preferred")]
        results = []
        for item in line_items:
            category = item.get("category", "general")
            scored = []
            for s in candidates:
                if s["category"] == category or category == "general":
                    score = s["score"]
                    if s.get("preferred"):
                        score += 5
                    if s.get("pending_deliveries", 0) > 3:
                        score -= 10
                    scored.append({"supplier": s["name"], "score": score, "rating": s["avg_rating"]})
            scored.sort(key=lambda x: -x["score"])
            if scored:
                results.append({"item": item.get("name", "Unknown"), "best_supplier": scored[0]})
        return results

    def _find_supplier(self, name: str) -> Optional[Dict]:
        if not name:
            return SUPPLIER_DB[0] if SUPPLIER_DB else None
        for s in SUPPLIER_DB:
            if name.lower() in s["name"].lower():
                return s
        return SUPPLIER_DB[0] if SUPPLIER_DB else None

    def _build_po_lines(self, request: POGenerateRequest) -> List[Dict]:
        if request.line_items:
            return [
                {"name": li.get("name", "Item"), "quantity": li.get("quantity", 1),
                 "unit": li.get("unit", "each"), "rate": li.get("rate", 0),
                 "total": li.get("total", li.get("quantity", 1) * li.get("rate", 0)),
                 "category": li.get("category", "general")}
                for li in request.line_items
            ]
        return [{"name": "Professional Services", "quantity": 1, "unit": "event",
                 "rate": 0, "total": 0, "category": "general"}]
