"""
test_scm_cost_engine.py — Automated tests for SCM Cost Engine
Run: pytest test_scm_cost_engine.py -v
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the router
from app.organs.incentivehouse_organ.scm_cost_engine import router as cost_engine_router

app = FastAPI()
app.include_router(cost_engine_router)
client = TestClient(app)


# ── HEALTH CHECK ──


def test_health_check():
    r = client.get("/cost-engine/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert len(data["engines_loaded"]) == 7
    assert data["fallback_writable"] is True


def test_list_engines():
    r = client.get("/cost-engine/engines")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 8
    assert any(e["id"] == "value_chain" for e in data["engines"])
    assert any(e["id"] == "target_costing" for e in data["engines"])
    assert any(e["id"] == "sustainability" for e in data["engines"])


# ── FULL EVENT ANALYSIS ──

FULL_EVENT_PAYLOAD = {
    "event_id": 1,
    "event_code": "EVT-2026-001",
    "event_name": "Cisco Annual Meeting",
    "client_id": 84,
    "client_name": "CISCO",
    "gross_sales": 250000,
    "budget": 200000,
    "actual_cost": 195000,
    "primary_activities": [
        {
            "name": "Venue & Setup",
            "category": "primary",
            "cost_egp": 45000,
            "revenue_attributable_egp": 60000,
            "client_satisfaction_score": 8.5,
            "competitive_advantage": 7.0,
        },
        {
            "name": "Catering",
            "category": "primary",
            "cost_egp": 35000,
            "revenue_attributable_egp": 40000,
            "client_satisfaction_score": 9.0,
            "competitive_advantage": 6.5,
        },
        {
            "name": "AV & Entertainment",
            "category": "primary",
            "cost_egp": 25000,
            "revenue_attributable_egp": 35000,
            "client_satisfaction_score": 8.0,
            "competitive_advantage": 8.5,
        },
        {
            "name": "Transport & Logistics",
            "category": "primary",
            "cost_egp": 20000,
            "revenue_attributable_egp": 25000,
            "client_satisfaction_score": 7.5,
            "competitive_advantage": 6.0,
        },
        {
            "name": "Guest Services",
            "category": "primary",
            "cost_egp": 15000,
            "revenue_attributable_egp": 20000,
            "client_satisfaction_score": 9.5,
            "competitive_advantage": 7.5,
        },
    ],
    "support_activities": [
        {
            "name": "Event Planning",
            "category": "support",
            "cost_egp": 20000,
            "revenue_attributable_egp": 30000,
            "client_satisfaction_score": 8.0,
            "competitive_advantage": 7.0,
        },
        {
            "name": "HR & Staffing",
            "category": "support",
            "cost_egp": 15000,
            "revenue_attributable_egp": 18000,
            "client_satisfaction_score": 7.0,
            "competitive_advantage": 5.5,
        },
        {
            "name": "Technology Platform",
            "category": "support",
            "cost_egp": 10000,
            "revenue_attributable_egp": 25000,
            "client_satisfaction_score": 8.5,
            "competitive_advantage": 9.0,
        },
        {
            "name": "Procurement",
            "category": "support",
            "cost_egp": 8000,
            "revenue_attributable_egp": 12000,
            "client_satisfaction_score": 7.5,
            "competitive_advantage": 6.0,
        },
    ],
    "sustainability_costs": [
        {
            "category": "Carbon Emissions",
            "cost_egp": 5000,
            "externality_egp": 8000,
            "mitigation_cost_egp": 3000,
            "regulatory_risk": "medium",
        },
        {
            "category": "Waste Management",
            "cost_egp": 3000,
            "externality_egp": 2000,
            "mitigation_cost_egp": 1500,
            "regulatory_risk": "low",
        },
        {
            "category": "Social Impact",
            "cost_egp": 2000,
            "externality_egp": 0,
            "mitigation_cost_egp": 500,
            "regulatory_risk": "low",
        },
    ],
    "cost_drivers": [
        {
            "name": "Event Scale",
            "driver_type": "structural",
            "current_level": 150,
            "optimal_level": 200,
            "unit": "attendees",
            "impact_on_cost_pct": 15.0,
        },
        {
            "name": "Workforce Skill",
            "driver_type": "executional",
            "current_level": 75,
            "optimal_level": 90,
            "unit": "training_hours",
            "impact_on_cost_pct": 8.0,
        },
    ],
}


def test_full_event_analysis():
    r = client.post("/cost-engine/analyze/event/full", json=FULL_EVENT_PAYLOAD)
    assert r.status_code == 200, f"Error: {r.text}"
    data = r.json()

    assert data["event_id"] == 1
    assert data["event_name"] == "Cisco Annual Meeting"
    assert "analyses" in data
    assert "value_chain" in data["analyses"]
    assert "target_costing" in data["analyses"]
    assert "sustainability" in data["analyses"]
    assert "profitability" in data["analyses"]

    # Value chain checks
    vc = data["analyses"]["value_chain"]
    assert vc["total_cost"] > 0
    assert vc["margin_ratio"] > 0
    assert len(vc["linkages"]) > 0

    # Target costing checks
    tc = data["analyses"]["target_costing"]
    assert tc["target_cost"] > 0
    assert tc["cost_gap"] is not None
    assert len(tc["actions"]) > 0

    # Sustainability checks
    sc = data["analyses"]["sustainability"]
    assert sc["true_cost"] > sc["total_internal_cost"]
    assert sc["carbon_cost"] > 0

    # Profitability checks
    ep = data["analyses"]["profitability"]
    assert ep["gross_profit"] is not None
    assert ep["status"] in ["profitable", "loss"]

    # Persistence check (JSON fallback on dev)
    assert "persistence" in data
    for p in data["persistence"]:
        assert p["persisted"] is True
        assert p["mode"] in ["postgresql", "json_fallback"]

    assert data["overall_confidence"] > 0


# ── INDIVIDUAL ENGINE TESTS ──


def test_value_chain_only():
    r = client.post("/cost-engine/analyze/value-chain", json=FULL_EVENT_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert "analysis" in data
    assert data["analysis"]["analysis_type"] == "value_chain_analysis"
    assert "persistence" in data


def test_target_costing_only():
    r = client.post("/cost-engine/analyze/target-costing", json=FULL_EVENT_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    tc = data["analysis"]
    assert tc["target_cost"] == 250000 * 0.80  # 20% margin
    assert tc["current_cost"] == 195000
    assert tc["cost_gap"] == 195000 - 200000  # 5000 surplus


def test_sustainability_only():
    r = client.post("/cost-engine/analyze/sustainability", json=FULL_EVENT_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    sc = data["analysis"]
    assert sc["total_internal_cost"] == 10000  # 5000+3000+2000
    assert sc["total_externality"] == 10000  # 8000+2000+0
    assert sc["true_cost"] == 20000


def test_profitability_only():
    r = client.post("/cost-engine/analyze/profitability", json=FULL_EVENT_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    ep = data["analysis"]
    assert ep["revenue"] == 250000
    assert ep["status"] == "profitable"
    assert ep["client_profitability"]["client_name"] == "CISCO"


# ── CVP TEST ──

CVP_PAYLOAD = {
    "fixed_costs": 50000,
    "variable_cost_per_unit": 800,
    "selling_price_per_unit": 1500,
    "current_volume": 200,
    "target_profit": 30000,
}


def test_cvp_analysis():
    r = client.post("/cost-engine/analyze/cvp", json=CVP_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    analysis = data["analysis"]

    assert analysis["contribution_margin"] == 700  # 1500 - 800
    assert analysis["break_even_units"] == pytest.approx(71.43, rel=0.01)
    assert analysis["current_profit"] == pytest.approx(
        90000, rel=0.01
    )  # 200*700 - 50000
    assert analysis["target_volume"] == pytest.approx(
        114.29, rel=0.01
    )  # (50000+30000)/700
    assert analysis["margin_of_safety_pct"] > 0


# ── ABC TEST ──

ABC_PAYLOAD = {
    "activities": [
        {"name": "Event Planning", "hours": 40, "rate": 500},
        {"name": "On-site Coordination", "hours": 24, "rate": 400},
        {"name": "Post-event Reporting", "hours": 8, "rate": 350},
    ],
    "cost_pools": [
        {
            "pool": "Admin Overhead",
            "total_cost": 50000,
            "driver": "event_count",
            "volume": 10,
        },
        {
            "pool": "Facility Depreciation",
            "total_cost": 30000,
            "driver": "event_hours",
            "volume": 500,
        },
    ],
}


def test_abc_analysis():
    r = client.post("/cost-engine/analyze/abc", json=ABC_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    analysis = data["analysis"]

    assert (
        analysis["total_activity_cost"] == 40 * 500 + 24 * 400 + 8 * 350
    )  # 20000 + 9600 + 2800 = 32400
    assert analysis["total_pool_cost"] == 80000
    assert analysis["total_abc_cost"] == 32400 + 80000


# ── VENDOR SCORECARD TEST ──

VENDOR_PAYLOAD = {
    "vendor_id": 1,
    "vendor_name": "Grand Nile Venue",
    "quality_score": 88,
    "delivery_score": 92,
    "price_score": 75,
    "service_score": 85,
}


def test_vendor_scorecard():
    r = client.post("/cost-engine/analyze/vendor-scorecard", json=VENDOR_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    analysis = data["analysis"]

    # Default weights: quality 0.30, delivery 0.25, price 0.25, service 0.20
    expected = 88 * 0.30 + 92 * 0.25 + 75 * 0.25 + 85 * 0.20
    assert analysis["overall_score"] == pytest.approx(expected, abs=0.1)
    assert analysis["grade"] == "B"  # 85.15
    assert analysis["vendor_name"] == "Grand Nile Venue"
    assert "persistence" in data


# ── EDGE CASES ──


def test_cvp_impossible_break_even():
    """Price below variable cost — no break-even possible."""
    payload = {
        "fixed_costs": 50000,
        "variable_cost_per_unit": 1500,
        "selling_price_per_unit": 1000,
        "current_volume": 200,
    }
    r = client.post("/cost-engine/analyze/cvp", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "error" in data["analysis"]


def test_empty_event_analysis():
    """Minimal event with no activities."""
    payload = {
        "event_id": 99,
        "event_code": "EVT-EMPTY",
        "event_name": "Minimal Event",
        "client_id": 1,
        "client_name": "Test",
        "gross_sales": 100000,
        "budget": 80000,
        "actual_cost": 75000,
        "primary_activities": [],
        "support_activities": [],
        "sustainability_costs": [],
        "cost_drivers": [],
    }
    r = client.post("/cost-engine/analyze/event/full", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["analyses"]["profitability"]["total_cost"] >= 0
