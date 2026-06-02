"""
Event-OR Bridge
===============
Extracts Event (project/job) data from BIO-ERP's production database (READ-ONLY),
converts it to OR-ERP model inputs, runs analyses, and returns results.

All outputs go to disposable JSON files in the analysis sandbox.
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.organs.or_organ.or_erp_module import (
    ORERPModule,
    DecisionState, DecisionAlternative, DecisionAnalysisEngine,
    LPObjective, LPConstraint,
    InventoryItem,
    TransportNode, TransportRoute,
    TOCResource,
    BreakEvenPoint,
    TransportationEngine
)

logger = logging.getLogger(__name__)


def _sanitize(obj):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    return obj


class EventORBridge:
    """
    Reads Event data from BIO-ERP, runs OR analyses, saves to JSON sandbox.
    NEVER writes to production database.
    """

    def __init__(self, db: AsyncSession, event_id: Optional[int] = None, sandbox_dir: str = "./analysis_sandbox"):
        self.db = db
        self.event_id = event_id
        self.sandbox_dir = Path(sandbox_dir)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.or_module = ORERPModule()

    # ------------------------------------------------------------------
    # DATA EXTRACTION (READ-ONLY from BIO-ERP)
    # ------------------------------------------------------------------

    async def _get_event(self) -> Optional[Dict[str, Any]]:
        """Fetch Event record from production DB (READ-ONLY)."""
        from app.models.event import Event
        result = await self.db.execute(select(Event).where(Event.id == self.event_id))
        event = result.scalar_one_or_none()
        if not event:
            logger.warning("Event %s not found", self.event_id)
            return None
        return {
            "id": event.id,
            "name_en": event.name_en,
            "name_ar": event.name_ar,
            "event_type": event.event_type,
            "status": event.status,
            "start_date": str(event.start_date or ""),
            "end_date": str(event.end_date or ""),
            "duration_days": event.duration_days,
            "total_budget": event.total_budget,
            "total_cost": event.total_cost,
            "total_revenue": event.total_revenue,
            "gross_profit": event.gross_profit,
        }

    async def _get_budget_lines(self) -> List[Dict[str, Any]]:
        """Fetch budget lines for the event."""
        from app.models.event import EventBudgetLine
        result = await self.db.execute(
            select(EventBudgetLine).where(EventBudgetLine.event_id == self.event_id)
        )
        return [
            {
                "id": bl.id,
                "description": bl.description,
                "quantity": bl.quantity,
                "unit_cost": bl.unit_cost,
                "total_cost": bl.total_cost,
                "selling_price": bl.selling_price,
                "section": bl.section or "GENERAL",
            }
            for bl in result.scalars().all()
        ]

    async def _get_line_items(self) -> List[Dict[str, Any]]:
        """Fetch line items for the event."""
        from app.models.event import EventLineItem
        result = await self.db.execute(
            select(EventLineItem).where(EventLineItem.event_id == self.event_id)
        )
        return [
            {
                "id": li.id,
                "description": li.description,
                "section": li.section,
                "quantity": li.quantity,
                "uom": li.uom,
                "unit_cost": li.unit_cost,
                "total_cost": li.total_cost,
                "selling_price": li.selling_price,
            }
            for li in result.scalars().all()
        ]

    async def _get_inventory(self) -> List[Dict[str, Any]]:
        """Fetch raw material inventory levels."""
        from app.models.manufacturing import RawMaterial
        try:
            result = await self.db.execute(select(RawMaterial))
            return [
                {
                    "sku": rm.sku,
                    "name": rm.name,
                    "stock_qty": rm.stock_qty,
                    "reorder_point": rm.reorder_point,
                    "unit_cost": rm.unit_cost,
                }
                for rm in result.scalars().all()
            ]
        except Exception:
            logger.warning("RawMaterial table not available — skipping inventory")
            return []

    # ------------------------------------------------------------------
    # OR ANALYSES
    # ------------------------------------------------------------------

    def _run_lp(self, event: Dict, budget_lines: List[Dict]) -> Dict:
        """
        Linear Programming: Optimal resource allocation / production mix.
        Uses budget line quantities as demand constraints.
        """
        if not budget_lines:
            return {"status": "skipped", "reason": "No budget lines"}

        coefficients = [bl.get("selling_price", 0) - bl.get("unit_cost", 0) for bl in budget_lines]
        if not any(c > 0 for c in coefficients):
            coefficients = [1.0] * len(budget_lines)

        rhs_list = [bl.get("quantity", 1) for bl in budget_lines]
        constraints = [
            {"coefficients": [1.0 if i == idx else 0.0 for i in range(len(budget_lines))],
             "rhs": float(rhs), "operator": "<="}
            for idx, rhs in enumerate(rhs_list)
        ]

        obj = {"coefficients": coefficients, "sense": "maximize"}
        result = self.or_module.solve_linear_program(obj, constraints)

        return _sanitize({
            "status": "completed" if result.get("success") else "failed",
            "objective_value": result.get("objective_value"),
            "solution": result.get("solution"),
            "shadow_prices": result.get("shadow_prices"),
            "timestamp": datetime.now().isoformat(),
        })

    def _run_eoq(self, budget_lines: List[Dict], inventory: List[Dict]) -> Dict:
        """
        EOQ Analysis: Check if materials need reordering.
        Uses budget line quantities as demand, compares against inventory.
        """
        recommendations = []
        inv_by_name = {i["sku"].lower(): i for i in inventory}

        for bl in budget_lines:
            item_name = bl.get("description", "").lower()
            match = inv_by_name.get(item_name)
            qty_needed = bl.get("quantity", 0)

            if match:
                stock = match.get("stock_qty", 0)
                reorder = match.get("reorder_point", 0)
                if stock < qty_needed:
                    shortfall = qty_needed - stock
                    recommendations.append({
                        "sku": match["sku"],
                        "name": match["name"],
                        "needed": qty_needed,
                        "in_stock": stock,
                        "shortfall": shortfall,
                        "action": "ORDER_IMMEDIATELY",
                    })
                elif stock < reorder:
                    recommendations.append({
                        "sku": match["sku"],
                        "name": match["name"],
                        "needed": qty_needed,
                        "in_stock": stock,
                        "action": "REORDER_SOON",
                    })
            else:
                recommendations.append({
                    "sku": item_name,
                    "name": bl.get("description", ""),
                    "needed": qty_needed,
                    "in_stock": 0,
                    "action": "NO_INVENTORY_DATA",
                })

        return _sanitize({
            "status": "completed" if recommendations else "skipped",
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        })

    def _run_pert(self, event: Dict, line_items: List[Dict]) -> Dict:
        """
        PERT/CPM: Estimate project duration based on line items as activities.
        Sections become activity groups.
        """
        section_durations = {}
        for li in line_items:
            section = li.get("section", "GENERAL")
            qty = li.get("quantity", 1)
            duration = max(1, qty // 2)
            section_durations[section] = max(section_durations.get(section, 0), duration)

        if not section_durations:
            return {"status": "skipped", "reason": "No line items"}

        activities = []
        prev_id = None
        for idx, (section, dur) in enumerate(sorted(section_durations.items())):
            act_id = f"ACT_{idx+1}"
            act = {"id": act_id, "name": section, "duration": dur}
            if prev_id:
                act["predecessors"] = [prev_id]
            activities.append(act)
            prev_id = act_id

        result = self.or_module.analyze_network(activities)
        return _sanitize({
            "status": "completed",
            "critical_path": result.get("result", {}).get("critical_path", []),
            "total_duration": result.get("result", {}).get("total_duration"),
            "activities": activities,
            "timestamp": datetime.now().isoformat(),
        })

    def _run_cvp(self, event: Dict) -> Dict:
        """
        CVP: Break-even and profit analysis for the event.
        """
        revenue = event.get("total_revenue", 0)
        cost = event.get("total_cost", 0)
        duration = event.get("duration_days", 1)
        fixed_costs = cost * 0.6
        variable_cost = (cost * 0.4) / max(duration, 1)
        selling_price = revenue / max(duration, 1) if duration else 0

        if selling_price <= variable_cost:
            return {
                "status": "completed",
                "breakeven_units": "N/A (price <= variable cost)",
                "profit": revenue - cost,
                "margin": ((revenue - cost) / revenue * 100) if revenue else 0,
                "timestamp": datetime.now().isoformat(),
            }

        result = self.or_module.analyze_cost_profit(fixed_costs, variable_cost, selling_price, target_profit=0)
        profit_amount = revenue - cost
        margin_pct = (profit_amount / revenue * 100) if revenue else 0

        return _sanitize({
            "status": "completed",
            "breakeven_units": result.get("basic_analysis", {}).get("break_even_units"),
            "breakeven_revenue": result.get("basic_analysis", {}).get("break_even_revenue"),
            "profit": profit_amount,
            "margin_pct": margin_pct,
            "recommendation": "Excellent margin" if margin_pct > 20
            else "Good margin" if margin_pct > 10
            else "Low margin — review pricing" if margin_pct > 0
            else "Loss — restructure event",
            "timestamp": datetime.now().isoformat(),
        })

    # ------------------------------------------------------------------
    # GENERATE RECOMMENDATIONS
    # ------------------------------------------------------------------

    def _generate_recommendations(self, lp: Dict, eoq: Dict, pert: Dict, cvp: Dict) -> List[Dict]:
        recs = []

        if lp.get("status") == "failed":
            recs.append({"type": "warning", "message": "Resources may be insufficient — consider outsourcing"})

        if eoq.get("status") == "completed":
            for r in eoq.get("recommendations", []):
                if r.get("action") == "ORDER_IMMEDIATELY":
                    recs.append({
                        "type": "critical",
                        "message": f"Order {r['name']} immediately — shortfall of {r['shortfall']} units",
                    })
                elif r.get("action") == "REORDER_SOON":
                    recs.append({
                        "type": "info",
                        "message": f"{r['name']} stock is low — consider reordering soon",
                    })

        if pert.get("status") == "completed":
            dur = pert.get("total_duration")
            if dur and dur > 30:
                recs.append({"type": "warning", "message": f"Project duration {dur}d is long — review critical path"})

        if cvp.get("status") == "completed":
            margin = cvp.get("margin_pct", 0)
            if margin < 0:
                recs.append({"type": "critical", "message": "Event is projected to lose money — restructure pricing"})
            elif margin < 10:
                recs.append({"type": "warning", "message": f"Margin {margin:.1f}% is thin — review costs"})
            else:
                recs.append({"type": "success", "message": f"Healthy margin at {margin:.1f}%"})

        return recs

    # ------------------------------------------------------------------
    # RUN ALL
    # ------------------------------------------------------------------

    async def run_all(self) -> Dict[str, Any]:
        """Run all OR analyses for this event and save results to sandbox."""
        event = await self._get_event()
        if not event:
            return {"error": f"Event {self.event_id} not found"}

        budget_lines = await self._get_budget_lines()
        line_items = await self._get_line_items()
        inventory = await self._get_inventory()

        lp = self._run_lp(event, budget_lines)
        eoq = self._run_eoq(budget_lines, inventory)
        pert = self._run_pert(event, line_items)
        cvp = self._run_cvp(event)
        recommendations = self._generate_recommendations(lp, eoq, pert, cvp)

        result = _sanitize({
            "event_id": self.event_id,
            "event_name": event.get("name_en"),
            "status": event.get("status"),
            "analyzed_at": datetime.now().isoformat(),
            "mode": "READ_ONLY",
            "analyses": {
                "linear_programming": lp,
                "eoq_inventory": eoq,
                "pert_schedule": pert,
                "cvp_profitability": cvp,
            },
            "recommendations": recommendations,
            "overall_feasible": all(
                r.get("type") != "critical"
                for r in recommendations
            ),
        })

        file_path = self.sandbox_dir / f"event_{self.event_id}_or_analysis.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info("Analysis saved: %s", file_path)
        return result

    # ------------------------------------------------------------------
    # STANDALONE ANALYSES
    # ------------------------------------------------------------------

    def analyze_stock_alert(self, sku: str, current_qty: float, reorder_point: float) -> Dict:
        """
        Standalone stock alert analysis — triggered when inventory is low.
        Calculates EOQ reorder quantity and urgency.
        """
        shortfall = max(0, reorder_point - current_qty)
        eoq_item = InventoryItem(
            sku=sku,
            name=sku,
            annual_demand=shortfall * 12,
            ordering_cost=50.0,
            holding_cost_per_unit=5.0,
            unit_cost=10.0,
            lead_time_days=7,
        )
        result = self.or_module.optimize_inventory([eoq_item.__dict__], "eoq_basic")

        result_data = _sanitize({
            "sku": sku,
            "current_qty": current_qty,
            "reorder_point": reorder_point,
            "shortfall": shortfall,
            "urgency": "IMMEDIATE" if shortfall > current_qty * 0.5 else "NORMAL",
            "eoq": result,
            "timestamp": datetime.now().isoformat(),
        })

        file_path = self.sandbox_dir / f"stock_{sku}_alert.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return result_data

    async def analyze_invoice_impact(self, invoice_id: int, invoice_type: str) -> Dict:
        """
        Analyze the impact of a posted invoice on profitability (CVP).
        """
        if invoice_type == "customer":
            from app.models.finance import CustomerInvoice
            result = await self.db.execute(
                select(CustomerInvoice).where(CustomerInvoice.id == invoice_id)
            )
            inv = result.scalar_one_or_none()
            if not inv:
                return {"error": f"CustomerInvoice {invoice_id} not found"}
            revenue = inv.total_amount or 0
            cost = inv.total_cost or 0
        elif invoice_type == "vendor":
            from app.models.finance import VendorInvoice
            result = await self.db.execute(
                select(VendorInvoice).where(VendorInvoice.id == invoice_id)
            )
            inv = result.scalar_one_or_none()
            if not inv:
                return {"error": f"VendorInvoice {invoice_id} not found"}
            revenue = 0
            cost = inv.total_amount or 0
        else:
            return {"error": f"Unknown invoice type: {invoice_type}"}

        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue else 0

        result_data = _sanitize({
            "invoice_id": invoice_id,
            "invoice_type": invoice_type,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "margin_pct": margin,
            "rating": "Good" if margin > 20 else "Fair" if margin > 0 else "Loss",
            "timestamp": datetime.now().isoformat(),
        })

        file_path = self.sandbox_dir / f"invoice_{invoice_id}_impact.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return result_data
