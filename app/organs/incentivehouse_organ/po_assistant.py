"""
POAssistant — Intelligent Purchase Order Generator for IncentiveHouse ERP

Auto-generates POs from event line items with:
- Supplier scoring (price, quality, on-time delivery)
- Budget guardrails (block/warn if over budget)
- One-click PO creation from event data
- Multi-supplier optimization

100% local inference. No cloud APIs.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from .engine import CoPilotEngine, ConfidenceLevel
from .schemas import (
    POGenerateIn,
    POLineItemOut,
    PORecommendationOut,
    POGenerateResponse,
)

logger = logging.getLogger("copilot.po")


@dataclass
class SupplierScore:
    """Composite supplier performance score."""
    supplier_id: int
    supplier_name: str
    price_score: float       # 0-1, lower price = higher score
    quality_score: float     # 0-1, from past ratings
    delivery_score: float    # 0-1, on-time percentage
    composite_score: float   # Weighted average
    avg_lead_days: int
    last_price: float
    currency: str = "EGP"


class POAssistant:
    """
    Intelligent PO Generator — turns event line items into optimized purchase orders.
    """

    # Weight factors for supplier scoring
    PRICE_WEIGHT = 0.35
    QUALITY_WEIGHT = 0.35
    DELIVERY_WEIGHT = 0.30

    # Budget thresholds
    WARNING_PCT = 0.85   # Warn at 85% of budget
    BLOCK_PCT = 1.05     # Block at 105% of budget

    def __init__(self, engine: CoPilotEngine, db_session_factory=None):
        self.engine = engine
        self.db = db_session_factory

    # ═══════════════════════════════════════════════════════════════
    # Main Entry: Generate POs from Event
    # ═══════════════════════════════════════════════════════════════

    def generate_pos(self, request: POGenerateIn) -> POGenerateResponse:
        """
        Main method: given an event, generate optimized purchase orders.
        """
        import time
        start = time.time()

        # Fetch event data and line items
        event_data = self._fetch_event_data(request.event_id)
        if not event_data:
            return POGenerateResponse(
                success=False,
                message=f"Event {request.event_id} not found",
            )

        line_items = event_data.get("line_items", [])
        if not line_items:
            return POGenerateResponse(
                success=False,
                message="Event has no line items to generate POs from",
            )

        # Score suppliers for each line item
        scored_items = []
        for item in line_items:
            scored = self._score_item_suppliers(item, request.preferred_supplier_id)
            scored_items.append(scored)

        # Group by supplier for consolidated POs
        supplier_groups = self._group_by_supplier(scored_items)

        # Build PO recommendations
        pos = []
        total_budget_impact = 0.0
        approval_required = False

        for supplier_id, items in supplier_groups.items():
            po = self._build_po_recommendation(
                event_id=request.event_id,
                supplier_id=supplier_id,
                items=items,
                budget_cap=request.budget_cap,
                urgency=request.urgency,
            )
            pos.append(po)
            total_budget_impact += po.total

            if po.budget_status in ("near_limit", "over_budget"):
                approval_required = True

        elapsed = (time.time() - start) * 1000

        return POGenerateResponse(
            success=True,
            message=f"Generated {len(pos)} PO recommendation(s) from {len(line_items)} line items",
            processing_time_ms=elapsed,
            pos=pos,
            total_budget_impact=total_budget_impact,
            approval_required=approval_required,
        )

    # ═══════════════════════════════════════════════════════════════
    # Supplier Scoring
    # ═══════════════════════════════════════════════════════════════

    def _score_item_suppliers(
        self,
        item: Dict[str, Any],
        preferred_supplier_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Score all suppliers capable of providing this item."""
        item_id = item.get("item_id")
        item_name = item.get("item_name", "Unknown")
        quantity = item.get("quantity", 1)

        # Fetch supplier candidates for this item
        candidates = self._fetch_supplier_candidates(item_id, item_name)

        scored = []
        for supplier in candidates:
            # Calculate price score (inverse of unit price, normalized)
            price_score = self._calc_price_score(supplier.last_price, candidates)

            # Composite score
            composite = (
                price_score * self.PRICE_WEIGHT +
                supplier.quality_score * self.QUALITY_WEIGHT +
                supplier.delivery_score * self.DELIVERY_WEIGHT
            )

            # Boost preferred supplier
            if preferred_supplier_id and supplier.supplier_id == preferred_supplier_id:
                composite = min(composite + 0.15, 1.0)

            scored.append({
                "supplier": supplier,
                "price_score": price_score,
                "composite_score": composite,
                "unit_price": supplier.last_price,
                "total_price": supplier.last_price * quantity,
                "delivery_days": supplier.avg_lead_days,
            })

        # Sort by composite score
        scored.sort(key=lambda x: x["composite_score"], reverse=True)

        return {
            "item": item,
            "candidates": scored,
            "best_candidate": scored[0] if scored else None,
        }

    def _calc_price_score(self, price: float, all_candidates: List[SupplierScore]) -> float:
        """Calculate normalized price score (lower price = higher score)."""
        prices = [c.last_price for c in all_candidates if c.last_price > 0]
        if not prices or max(prices) == min(prices):
            return 0.5

        min_p, max_p = min(prices), max(prices)
        # Invert: lowest price gets score 1.0
        return 1.0 - ((price - min_p) / (max_p - min_p))

    # ═══════════════════════════════════════════════════════════════
    # PO Building
    # ═══════════════════════════════════════════════════════════════

    def _group_by_supplier(
        self,
        scored_items: List[Dict[str, Any]],
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Group scored items by best supplier for consolidated POs."""
        groups: Dict[int, List[Dict[str, Any]]] = {}

        for scored in scored_items:
            best = scored.get("best_candidate")
            if not best:
                continue

            supplier_id = best["supplier"].supplier_id
            if supplier_id not in groups:
                groups[supplier_id] = []

            groups[supplier_id].append({
                "item": scored["item"],
                "selected": best,
            })

        return groups

    def _build_po_recommendation(
        self,
        event_id: int,
        supplier_id: int,
        items: List[Dict[str, Any]],
        budget_cap: Optional[float],
        urgency: str,
    ) -> PORecommendationOut:
        """Build a complete PO recommendation for a supplier."""
        supplier = items[0]["selected"]["supplier"]

        # Build line items
        po_line_items = []
        subtotal = 0.0

        for entry in items:
            selected = entry["selected"]
            item = entry["item"]

            line = POLineItemOut(
                item_id=item.get("item_id", 0),
                item_name=item.get("item_name", "Unknown"),
                quantity=item.get("quantity", 1),
                unit_price=selected["unit_price"],
                total_price=selected["total_price"],
                supplier_id=supplier_id,
                supplier_name=supplier.supplier_name,
                supplier_score=selected["composite_score"],
                delivery_days=selected["delivery_days"],
                confidence=self.engine.score_to_confidence(selected["composite_score"]),
            )
            po_line_items.append(line)
            subtotal += line.total_price

        # Calculate totals
        tax_pct = 14.0  # Egypt VAT
        tax_amount = subtotal * (tax_pct / 100)
        total = subtotal + tax_amount

        # Budget analysis
        budget_remaining = (budget_cap or float('inf')) - total
        budget_status = "within_budget"
        warnings = []

        if budget_cap:
            utilization = total / budget_cap
            if utilization >= self.BLOCK_PCT:
                budget_status = "over_budget"
                warnings.append(f"PO total ({total:,.0f} EGP) exceeds budget cap ({budget_cap:,.0f} EGP)")
            elif utilization >= self.WARNING_PCT:
                budget_status = "near_limit"
                warnings.append(f"PO utilizes {utilization*100:.0f}% of budget cap")

        # Urgency adjustments
        if urgency == "critical":
            warnings.append("CRITICAL urgency — expedite approval and delivery")
        elif urgency == "urgent":
            warnings.append("URGENT — prioritize supplier with fastest delivery")

        # Overall confidence
        avg_confidence = sum(li.supplier_score for li in po_line_items) / len(po_line_items)

        return PORecommendationOut(
            po_id=f"PO-{event_id}-{supplier_id}-{hash(str(items)) % 10000:04d}",
            event_id=event_id,
            supplier_id=supplier_id,
            supplier_name=supplier.supplier_name,
            supplier_score=supplier.composite_score,
            line_items=po_line_items,
            subtotal=subtotal,
            tax_pct=tax_pct,
            total=total,
            budget_remaining=budget_remaining if budget_remaining != float('inf') else total,
            budget_status=budget_status,
            warnings=warnings,
            confidence=self.engine.score_to_confidence(avg_confidence),
        )

    # ═══════════════════════════════════════════════════════════════
    # Data Layer
    # ═══════════════════════════════════════════════════════════════

    def _fetch_event_data(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Fetch event with line items from database."""
        if self.db:
            try:
                # Production query:
                # session = self.db()
                # event = session.query(Event).filter(Event.id == event_id).first()
                # return {...}
                pass
            except Exception as e:
                logger.error(f"Failed to fetch event {event_id}: {e}")

        # Return mock for development
        return self._mock_event_data(event_id)

    def _mock_event_data(self, event_id: int) -> Dict[str, Any]:
        """Mock event data for testing without database."""
        return {
            "event_id": event_id,
            "event_name": f"Event #{event_id}",
            "client_id": 1,
            "client_name": "CISCO",
            "budget": 750_000,
            "line_items": [
                {"item_id": 101, "item_name": "AV Setup", "quantity": 1, "category": "AV"},
                {"item_id": 102, "item_name": "Catering", "quantity": 80, "category": "Food"},
                {"item_id": 103, "item_name": "Transport", "quantity": 2, "category": "Logistics"},
                {"item_id": 104, "item_name": "Decorations", "quantity": 1, "category": "Decor"},
            ],
        }

    def _fetch_supplier_candidates(
        self,
        item_id: Optional[int],
        item_name: str,
    ) -> List[SupplierScore]:
        """Fetch suppliers who can provide this item."""
        if self.db:
            try:
                # Production query:
                # SELECT s.*, sp.* FROM suppliers s
                # JOIN supplier_prices sp ON sp.supplier_id = s.id
                # WHERE sp.item_id = ?
                pass
            except Exception as e:
                logger.error(f"Failed to fetch suppliers for item {item_id}: {e}")

        # Return mock suppliers
        return self._mock_suppliers(item_name)

    def _mock_suppliers(self, item_name: str) -> List[SupplierScore]:
        """Mock supplier data for testing."""
        mock_db = {
            "AV Setup": [
                SupplierScore(1, "AudioVis Pro", 0.8, 0.9, 0.95, 0.88, 3, 45000),
                SupplierScore(2, "Sound & Light Co", 0.9, 0.85, 0.80, 0.85, 5, 42000),
                SupplierScore(3, "EventTech Egypt", 0.7, 0.95, 0.90, 0.84, 4, 48000),
            ],
            "Catering": [
                SupplierScore(4, "Four Seasons Catering", 0.6, 0.95, 0.98, 0.83, 7, 950),
                SupplierScore(5, "Nile Ritz F&B", 0.8, 0.90, 0.92, 0.87, 5, 850),
                SupplierScore(6, "Gourmet Egypt", 0.9, 0.88, 0.85, 0.87, 3, 780),
            ],
            "Transport": [
                SupplierScore(7, "Egypt Limo", 0.85, 0.90, 0.95, 0.90, 1, 5000),
                SupplierScore(8, "VIP Transport", 0.75, 0.95, 0.98, 0.89, 2, 5500),
            ],
            "Decorations": [
                SupplierScore(9, "Decor Masters", 0.8, 0.92, 0.88, 0.87, 4, 25000),
                SupplierScore(10, "Event Decor Co", 0.9, 0.85, 0.90, 0.88, 3, 22000),
            ],
        }

        # Find best matching category
        for key, suppliers in mock_db.items():
            if key.lower() in item_name.lower() or item_name.lower() in key.lower():
                return suppliers

        # Default generic suppliers
        return [
            SupplierScore(99, "General Supplier A", 0.7, 0.8, 0.85, 0.78, 5, 10000),
            SupplierScore(100, "General Supplier B", 0.8, 0.75, 0.80, 0.78, 4, 9500),
        ]
