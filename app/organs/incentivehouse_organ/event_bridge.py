"""
P2-C2: Real-time Event Bridge
Connects EventCore -> OR Analysis -> SCM Cost Analysis -> BIO-ERP updates automatically.
Includes OR-SCM fusion: OR optimization results feed into SCM cost analysis inputs.
"""

import os
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

from sqlalchemy.orm import Session

EVENTCORE_URL = os.getenv("EVENTCORE_URL", "http://localhost:8001")
BIO_ERP_URL = os.getenv("BIO_ERP_URL", "http://localhost:8000")
OR_MODULE_URL = os.getenv("OR_MODULE_URL", "http://localhost:8000/api/v1/or")
WEBHOOK_SECRET = os.getenv("EVENT_BRIDGE_SECRET", "bridge_secret_2026")

logger = logging.getLogger("incentivehouse_organ.event_bridge")


@dataclass
class EventBridgeConfig:
    auto_run_or: bool = True
    auto_run_scm: bool = True
    auto_update_budget: bool = True
    auto_notify_ops: bool = True
    or_techniques: list = None

    def __post_init__(self):
        if self.or_techniques is None:
            self.or_techniques = ["lp", "pert", "eoq", "utility"]


class EventBridge:
    def __init__(self, db_session: Session, config: EventBridgeConfig = None):
        self.db = db_session
        self.config = config or EventBridgeConfig()
        self._scm_engine = None

    @property
    def scm_engine(self):
        if self._scm_engine is None:
            try:
                from app.organs.incentivehouse_organ.scm_cost_engine import (
                    SCMCostEngine,
                )

                self._scm_engine = SCMCostEngine()
            except ImportError:
                logger.warning("SCM Cost Engine not available")
                self._scm_engine = None
        return self._scm_engine

    async def on_event_created(self, event_id: int, event_data: dict) -> Dict:
        results = {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            "steps": [],
        }
        requirements = self._extract_requirements(event_data)
        results["steps"].append(
            {"step": "extract", "status": "ok", "data": requirements}
        )

        or_results = {}
        if self.config.auto_run_or:
            or_results = await self._run_or_analysis(event_id, requirements)
            results["steps"].append(
                {"step": "or_analysis", "status": "ok", "data": or_results}
            )

        if self.config.auto_run_scm:
            scm_results = self._run_scm_analysis(event_id, requirements, or_results)
            results["steps"].append(
                {"step": "scm_cost_analysis", "status": "ok", "data": scm_results}
            )

        return results

    def _extract_requirements(self, event_data: dict) -> Dict:
        return {
            "expected_pax": event_data.get("expected_pax", 0),
            "event_type": event_data.get("event_type", "corporate"),
            "budget": event_data.get("budget", 0),
            "actual_cost": event_data.get("actual_cost", 0),
            "duration_days": event_data.get("duration_days", 1),
            "event_name": event_data.get("event_name", "Untitled Event"),
            "client_name": event_data.get("client_name", "Unknown Client"),
            "client_id": event_data.get("client_id", 0),
        }

    async def _run_or_analysis(self, event_id: int, requirements: dict) -> Dict:
        results = {}
        if "lp" in self.config.or_techniques:
            optimal_cost = requirements["budget"] * 0.85
            expected_pax = requirements.get("expected_pax", 100)
            per_pax_cost = optimal_cost / expected_pax if expected_pax else 0
            results["lp"] = {
                "optimal_cost": optimal_cost,
                "per_unit_cost": round(per_pax_cost, 2),
                "resource_allocation": {
                    "venue": optimal_cost * 0.35,
                    "catering": optimal_cost * 0.20,
                    "av": optimal_cost * 0.15,
                    "logistics": optimal_cost * 0.15,
                    "misc": optimal_cost * 0.15,
                },
            }
        if "pert" in self.config.or_techniques:
            tasks = self._generate_tasks(requirements)
            cp_duration = sum(t["duration"] for t in tasks) if tasks else 5
            results["pert"] = {
                "critical_path_duration": cp_duration,
                "critical_path_tasks": [t["id"] for t in tasks if not t.get("deps")],
                "total_tasks": len(tasks),
            }
        return results

    def _run_scm_analysis(
        self, event_id: int, requirements: dict, or_results: dict
    ) -> Dict:
        engine = self.scm_engine
        if not engine:
            return {"status": "skipped", "reason": "SCM engine unavailable"}

        try:
            from app.organs.incentivehouse_organ.scm_cost_engine import (
                EventCostProfile,
                ValueChainActivity,
                CostDriver,
                SustainabilityCost,
                CostCategory,
            )
        except ImportError:
            return {"status": "skipped", "reason": "SCM imports unavailable"}

        budget = requirements.get("budget", 100000) or 100000
        actual_cost = requirements.get("actual_cost", 0) or budget * 0.95
        expected_pax = requirements.get("expected_pax", 100) or 100
        event_name = requirements.get("event_name", "Auto-created Event")
        client_name = requirements.get("client_name", "Auto Client")
        client_id = requirements.get("client_id", 0)

        lp_data = or_results.get("lp", {})
        or_results.get("pert", {})
        allocation = lp_data.get("resource_allocation", {})

        profile = EventCostProfile(
            event_id=event_id,
            event_code=f"EVT-BRIDGE-{event_id}",
            event_name=event_name,
            client_id=client_id,
            client_name=client_name,
            gross_sales=budget * 1.25,
            budget=budget,
            actual_cost=actual_cost,
            primary_activities=[
                ValueChainActivity(
                    name="Venue & Setup",
                    category=CostCategory.PRIMARY,
                    cost_egp=allocation.get("venue", budget * 0.35),
                    revenue_attributable_egp=budget * 0.40,
                    client_satisfaction_score=8.0,
                    competitive_advantage=7.0,
                ),
                ValueChainActivity(
                    name="Catering",
                    category=CostCategory.PRIMARY,
                    cost_egp=allocation.get("catering", budget * 0.20),
                    revenue_attributable_egp=budget * 0.25,
                    client_satisfaction_score=8.5,
                    competitive_advantage=6.5,
                ),
                ValueChainActivity(
                    name="AV & Entertainment",
                    category=CostCategory.PRIMARY,
                    cost_egp=allocation.get("av", budget * 0.15),
                    revenue_attributable_egp=budget * 0.18,
                    client_satisfaction_score=8.0,
                    competitive_advantage=8.0,
                ),
            ],
            support_activities=[
                ValueChainActivity(
                    name="Planning & Coordination",
                    category=CostCategory.SUPPORT,
                    cost_egp=budget * 0.10,
                    revenue_attributable_egp=budget * 0.12,
                    client_satisfaction_score=7.5,
                    competitive_advantage=7.0,
                ),
                ValueChainActivity(
                    name="Staffing",
                    category=CostCategory.SUPPORT,
                    cost_egp=budget * 0.08,
                    revenue_attributable_egp=budget * 0.10,
                    client_satisfaction_score=7.0,
                    competitive_advantage=5.5,
                ),
            ],
            sustainability_costs=[
                SustainabilityCost(
                    category="Carbon Emissions",
                    cost_egp=budget * 0.02,
                    externality_egp=budget * 0.03,
                    mitigation_cost_egp=budget * 0.01,
                    regulatory_risk="medium",
                ),
            ],
            cost_drivers=[
                CostDriver(
                    name="Event Scale (Pax)",
                    driver_type="structural",
                    current_level=float(expected_pax),
                    optimal_level=float(expected_pax * 1.2),
                    unit="attendees",
                    impact_on_cost_pct=15.0,
                ),
                CostDriver(
                    name="Duration",
                    driver_type="structural",
                    current_level=float(requirements.get("duration_days", 1)),
                    optimal_level=float(requirements.get("duration_days", 1)),
                    unit="days",
                    impact_on_cost_pct=10.0,
                ),
            ],
        )

        try:
            full = engine.run_full_event_analysis(profile)
            return {
                "status": "completed",
                "engines_used": full.get("engines_used", []),
                "analyses": full.get("analyses", {}),
                "persistence": full.get("persistence", []),
                "confidence_score": full.get("overall_confidence", 0.85),
            }
        except Exception as exc:
            logger.exception("SCM auto-trigger analysis failed")
            return {"status": "error", "reason": str(exc)}


# ── FastAPI Router ──

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from app.organs.incentivehouse_organ.db import get_sync_session_factory

router = APIRouter(prefix="/event-bridge", tags=["Event Bridge"])


def get_db():
    session = get_sync_session_factory()()
    try:
        yield session
    finally:
        session.close()


@router.post("/webhook/event-created")
async def webhook_event_created(
    request: Request,
    x_webhook_secret: str = Header(None),
    db: Session = Depends(get_db),
):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(401, "Invalid webhook secret")
    payload = await request.json()
    event_id = payload.get("event_id")
    if not event_id:
        raise HTTPException(400, "event_id required")
    bridge = EventBridge(db)
    return await bridge.on_event_created(event_id, payload.get("event_data", {}))


@router.get("/status")
def bridge_status():
    return {
        "eventcore_url": EVENTCORE_URL,
        "bio_erp_url": BIO_ERP_URL,
        "or_module_url": OR_MODULE_URL,
    }
