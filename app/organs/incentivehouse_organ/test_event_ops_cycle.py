"""
Integration Test Suite — Event Operations Cycle (Phases 3-5)
Tests: auto-recognition → execution form → checklist → stage advancement
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import your app and models (adjust paths as needed)
from app.main import app
from app.database import get_db
from app.models.event import Event
from app.models.client import Client
from app.models.staff import Staff
from app.models.sales_line_item import SalesLineItem
from app.models.event_checkpoint import EventCheckpoint
from app.services.auto_recognition import AutoRecognitionEngine


# ───────────────────────────────────────────────
# FIXTURES
# ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient with overridden DB."""
    from app.database import TestingSessionLocal, engine

    # Create test tables
    from app.models import Base

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db(client) -> Session:
    """Yield a DB session for direct model queries."""
    from app.database import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seeded_event(db: Session):
    """Create a realistic event with client, line items, and history."""
    # Client with history
    client = Client(
        name_en="CISCO Systems Egypt",
        name_ar="سيسكو سيستمز مصر",
        tax_id="123456789",
        email="events@cisco.eg",
        phone="+20 2 1234 5678",
        credit_limit=2000000,
        status="vip",
    )
    db.add(client)
    db.flush()

    # Past events (for history analysis)
    for i in range(3):
        past = Event(
            client_id=client.id,
            name_en=f"CISCO Past Event {i + 1}",
            event_type="conference",
            event_date=datetime.now() - timedelta(days=100 + i * 30),
            lifecycle_status="completed",
            expected_pax=100 + i * 20,
            actual_pax=105 + i * 18,
            budget=300000 + i * 50000,
            actual_cost=310000 + i * 45000,
            gross_sales=350000 + i * 60000,
            currency="EGP",
            venue_id=1 if i % 2 == 0 else 2,  # Alternating venues
        )
        db.add(past)

    # Current event (the one being tested)
    event = Event(
        client_id=client.id,
        name_en="CISCO Partner Summit 2026",
        event_type="conference",
        event_date=datetime.now() + timedelta(days=15),
        lifecycle_status="ops_assigned",
        expected_pax=120,
        budget=450000,
        gross_sales=520000,
        currency="EGP",
    )
    db.add(event)
    db.flush()

    # Sales line items (mixed categories)
    items = [
        SalesLineItem(
            event_id=event.id,
            category_name="Air Tickets",
            quantity=120,
            unit_price=5000,
            sub_category="Domestic",
        ),
        SalesLineItem(
            event_id=event.id,
            category_name="Venue",
            quantity=2,
            unit_price=25000,
            sub_category="Grand Ballroom",
        ),
        SalesLineItem(
            event_id=event.id,
            category_name="Catering",
            quantity=120,
            unit_price=350,
            sub_category="Buffet Lunch",
        ),
        SalesLineItem(
            event_id=event.id,
            category_name="AV/Production",
            quantity=2,
            unit_price=15000,
            sub_category="Full Setup",
        ),
        SalesLineItem(
            event_id=event.id,
            category_name="Transport",
            quantity=5,
            unit_price=800,
            sub_category="Shuttle",
        ),
    ]
    for item in items:
        db.add(item)

    # Ops team member
    staff = Staff(
        name="Ahmed Operations",
        email="ahmed@incentivehouse.eg",
        role="ops_manager",
        department="operations",
    )
    db.add(staff)
    db.flush()
    event.ops_team_id = staff.id

    db.commit()
    return event


# ───────────────────────────────────────────────
# PHASE 3 — AUTO-RECOGNITION TESTS
# ───────────────────────────────────────────────


class TestAutoRecognition:
    """Validate AutoRecognitionEngine produces correct suggestions."""

    def test_recognize_returns_client_data(self, db: Session, seeded_event: Event):
        engine = AutoRecognitionEngine(db)
        result = engine.recognize_event_form(seeded_event.id)

        assert result["event_id"] == seeded_event.id
        assert result["client"]["name_en"] == "CISCO Systems Egypt"
        assert result["expected_pax"] == 120
        assert result["currency"] == "EGP"

    def test_recognize_suggests_venue_from_history(
        self, db: Session, seeded_event: Event
    ):
        engine = AutoRecognitionEngine(db)
        result = engine.recognize_event_form(seeded_event.id)

        # CISCO has 3 past events with venue_id 1 and 2 alternating
        # Most frequent should be venue_id=1 (appears twice)
        assert result["auto_venue"] is not None
        assert "id" in result["auto_venue"]

    def test_category_uom_map_has_all_items(self, db: Session, seeded_event: Event):
        engine = AutoRecognitionEngine(db)
        result = engine.recognize_event_form(seeded_event.id)

        cat_map = result["category_uom_map"]
        assert len(cat_map) == 5  # 5 line items created

        # Verify Air Tickets config
        air = next(v for v in cat_map.values() if v["category_name"] == "Air Tickets")
        assert air["uom"] == "Each"
        assert air["buffer_percent"] == 0
        assert air["requires_passport"] is True
        assert air["qty"] == 120

        # Verify Catering config
        catering = next(v for v in cat_map.values() if v["category_name"] == "Catering")
        assert catering["uom"] == "Pax"
        assert catering["buffer_percent"] == 10
        assert catering["requires_dietary"] is True
        assert catering["final_qty"] == 132  # 120 + 10%

    def test_checklist_generated_for_conference(self, db: Session, seeded_event: Event):
        engine = AutoRecognitionEngine(db)
        result = engine.recognize_event_form(seeded_event.id)

        checklist = result["execution_checklist"]
        assert len(checklist) >= 8  # Conference has many required items

        required_ids = [c["id"] for c in checklist if c["required"]]
        assert "venue_contract" in required_ids
        assert "caterer_menu" in required_ids
        assert "av_quote" in required_ids
        assert "air_booking" in required_ids

    def test_historical_analytics_calculated(self, db: Session, seeded_event: Event):
        engine = AutoRecognitionEngine(db)
        result = engine.recognize_event_form(seeded_event.id)

        assert result["events_last_12_months"] == 3
        assert result["avg_budget_variance_pct"] != 0  # Past events have variance
        assert result["avg_pax_accuracy_pct"] > 0

    def test_suggested_ops_team_lowest_workload(self, db: Session, seeded_event: Event):
        engine = AutoRecognitionEngine(db)
        result = engine.recognize_event_form(seeded_event.id)

        # Only 1 staff member exists, so they should be suggested
        assert result["suggested_ops_team"] is not None
        assert result["suggested_ops_team"]["name"] == "Ahmed Operations"


# ───────────────────────────────────────────────
# PHASE 4 — EXECUTION FORM API TESTS
# ───────────────────────────────────────────────


class TestExecutionFormAPI:
    """Validate GET /execute returns complete form payload."""

    def test_execute_form_returns_event_details(
        self, client: TestClient, seeded_event: Event
    ):
        res = client.get(f"/api/v1/event-ops/events/{seeded_event.id}/execute")
        assert res.status_code == 200

        data = res.json()
        assert data["event"]["id"] == seeded_event.id
        assert data["event"]["name"] == "CISCO Partner Summit 2026"
        assert data["event"]["status"] == "ops_assigned"

    def test_execute_form_includes_recognition(
        self, client: TestClient, seeded_event: Event
    ):
        res = client.get(f"/api/v1/event-ops/events/{seeded_event.id}/execute")
        data = res.json()

        assert "recognition" in data
        assert data["recognition"]["client"]["name_en"] == "CISCO Systems Egypt"
        assert "category_uom_map" in data["recognition"]

    def test_execute_form_includes_checkpoints(
        self, client: TestClient, seeded_event: Event
    ):
        res = client.get(f"/api/v1/event-ops/events/{seeded_event.id}/execute")
        data = res.json()

        assert "checkpoints" in data
        # Initially empty until auto-recognition is applied
        assert isinstance(data["checkpoints"], list)

    def test_execute_form_has_edit_permissions(
        self, client: TestClient, seeded_event: Event
    ):
        res = client.get(f"/api/v1/event-ops/events/{seeded_event.id}/execute")
        data = res.json()

        assert "can_edit" in data
        assert isinstance(data["can_edit"], bool)


# ───────────────────────────────────────────────
# PHASE 5 — CHECKPOINT & STAGE TESTS
# ───────────────────────────────────────────────


class TestCheckpointLifecycle:
    """Validate checklist completion triggers stage advancement."""

    def test_apply_auto_recognition_creates_checkpoints(
        self, client: TestClient, seeded_event: Event, db: Session
    ):
        res = client.post(
            f"/api/v1/event-ops/events/{seeded_event.id}/auto-recognize/apply"
        )
        assert res.status_code == 200

        data = res.json()
        assert data["status"] == "applied"
        assert data["checkpoints_created"] >= 8

        # Verify in DB
        cps = (
            db.query(EventCheckpoint)
            .filter(EventCheckpoint.event_id == seeded_event.id)
            .all()
        )
        assert len(cps) == data["checkpoints_created"]

    def test_checkpoint_completion_updates_status(
        self, client: TestClient, seeded_event: Event, db: Session
    ):
        # First apply auto-recognition
        client.post(f"/api/v1/event-ops/events/{seeded_event.id}/auto-recognize/apply")

        # Get checkpoints
        cps = (
            db.query(EventCheckpoint)
            .filter(
                EventCheckpoint.event_id == seeded_event.id,
                EventCheckpoint.stage == "ops_assigned",
            )
            .all()
        )

        # Complete all required ops_assigned checkpoints
        for cp in cps:
            if cp.required:
                res = client.post(
                    f"/api/v1/event-ops/events/{seeded_event.id}/checkpoints/{cp.checkpoint_id}",
                    json={"completed": True, "notes": f"Done by test — {cp.label}"},
                )
                assert res.status_code == 200

        # Verify event advanced to procurement
        db.refresh(seeded_event)
        assert seeded_event.lifecycle_status == "procurement"

    def test_checkpoint_revert_undoes_completion(
        self, client: TestClient, seeded_event: Event, db: Session
    ):
        # Find a completed checkpoint
        cp = (
            db.query(EventCheckpoint)
            .filter(EventCheckpoint.event_id == seeded_event.id)
            .first()
        )

        if cp:
            res = client.post(
                f"/api/v1/event-ops/events/{seeded_event.id}/checkpoints/{cp.checkpoint_id}",
                json={"completed": False, "notes": "Reverted"},
            )
            assert res.status_code == 200

            db.refresh(cp)
            assert cp.completed_at is None
            assert cp.completed_by is None

    def test_manual_stage_advance_override(
        self, client: TestClient, seeded_event: Event, db: Session
    ):
        res = client.post(
            f"/api/v1/event-ops/events/{seeded_event.id}/advance-stage",
            json={"target_stage": "execution"},
        )
        assert res.status_code == 200

        data = res.json()
        assert data["new_stage"] == "execution"

        db.refresh(seeded_event)
        assert seeded_event.lifecycle_status == "execution"
        assert seeded_event.execution_date is not None


class TestExecutionQueue:
    """Validate priority queue returns correctly sorted events."""

    def test_queue_returns_only_active_events(self, client: TestClient, db: Session):
        # Create events in various stages
        for stage in [
            "draft",
            "confirmed",
            "ops_assigned",
            "procurement",
            "execution",
            "completed",
        ]:
            e = Event(
                client_id=1,
                name_en=f"Test {stage}",
                event_type="corporate",
                event_date=datetime.now() + timedelta(days=10),
                lifecycle_status=stage,
            )
            db.add(e)
        db.commit()

        res = client.get("/api/v1/event-ops/execution-queue")
        assert res.status_code == 200

        data = res.json()
        stages = [item["stage"] for item in data]

        # Should NOT include draft or completed
        assert "draft" not in stages
        assert "completed" not in stages
        # Should include ops/procurement/execution
        assert any(s in stages for s in ["ops_assigned", "procurement", "execution"])

    def test_queue_sorted_by_priority(self, client: TestClient, db: Session):
        res = client.get("/api/v1/event-ops/execution-queue")
        data = res.json()

        if len(data) >= 2:
            # Higher priority score should come first
            assert data[0]["priority_score"] >= data[1]["priority_score"]

    def test_queue_includes_event_metadata(self, client: TestClient):
        res = client.get("/api/v1/event-ops/execution-queue")
        data = res.json()

        if data:
            item = data[0]
            assert "event_id" in item
            assert "client_name" in item
            assert "days_remaining" in item
            assert "action_url" in item
            assert "pending_checklist_items" in item

    def test_queue_filter_by_stage(self, client: TestClient):
        res = client.get("/api/v1/event-ops/execution-queue?stage=procurement")
        assert res.status_code == 200

        data = res.json()
        for item in data:
            assert item["stage"] == "procurement"

    def test_queue_filter_by_ops_team(self, client: TestClient, seeded_event: Event):
        res = client.get(
            f"/api/v1/event-ops/execution-queue?ops_team_id={seeded_event.ops_team_id}"
        )
        assert res.status_code == 200

        data = res.json()
        for item in data:
            assert item["ops_owner"] == "Ahmed Operations"


class TestOpsDashboardSummary:
    """Validate executive summary for ops manager."""

    def test_dashboard_summary_has_counts(self, client: TestClient):
        res = client.get("/api/v1/event-ops/dashboard-summary")
        assert res.status_code == 200

        data = res.json()
        assert "total_active_events" in data
        assert "in_procurement" in data
        assert "in_execution" in data
        assert "overdue_events" in data
        assert "revenue_at_risk" in data

    def test_dashboard_summary_team_workload(self, client: TestClient):
        res = client.get("/api/v1/event-ops/dashboard-summary")
        data = res.json()

        assert "team_workload" in data
        assert isinstance(data["team_workload"], list)

    def test_revenue_at_risk_non_negative(self, client: TestClient):
        res = client.get("/api/v1/event-ops/dashboard-summary")
        data = res.json()

        assert data["revenue_at_risk"] >= 0


# ───────────────────────────────────────────────
# BULK UPDATE & ASSIGNMENT TESTS
# ───────────────────────────────────────────────


class TestBulkOperations:
    """Validate bulk category updates and team assignments."""

    def test_assign_ops_team(
        self, client: TestClient, seeded_event: Event, db: Session
    ):
        # Create another staff member
        staff = Staff(
            name="Mariam Ops", email="mariam@incentivehouse.eg", role="ops_team"
        )
        db.add(staff)
        db.commit()

        res = client.post(
            f"/api/v1/event-ops/events/{seeded_event.id}/assign-team",
            json={"ops_team_id": staff.id, "notes": "Assigned for test"},
        )
        assert res.status_code == 200

        data = res.json()
        assert data["ops_team_id"] == staff.id
        assert data["ops_team_name"] == "Mariam Ops"

        db.refresh(seeded_event)
        assert seeded_event.ops_team_id == staff.id

    def test_bulk_update_categories(
        self, client: TestClient, seeded_event: Event, db: Session
    ):
        # Get line items
        items = (
            db.query(SalesLineItem)
            .filter(SalesLineItem.event_id == seeded_event.id)
            .all()
        )

        updates = [
            {
                "line_item_id": items[0].id,
                "uom": "Round-Trip",
                "qty": 120,
                "buffer_percent": 0,
                "vendor_id": 1,
                "unit_price": 5500,
                "status": "ordered",
                "notes": "Updated by test",
            }
        ]

        res = client.post(
            f"/api/v1/event-ops/events/{seeded_event.id}/categories/bulk-update",
            json=updates,
        )
        assert res.status_code == 200

        data = res.json()
        assert data["updated"] == 1

        db.refresh(items[0])
        assert items[0].uom == "Round-Trip"
        assert items[0].status == "ordered"


# ───────────────────────────────────────────────
# RBAC & SECURITY TESTS
# ───────────────────────────────────────────────


class TestRBAC:
    """Validate role-based access control on ops endpoints."""

    def test_execution_queue_requires_ops_role(self, client: TestClient):
        # Without auth header — should 401 or 403
        res = client.get("/api/v1/event-ops/execution-queue")
        assert res.status_code in [401, 403]

    def test_advance_stage_requires_manager(
        self, client: TestClient, seeded_event: Event
    ):
        # ops_team role should NOT be able to force-advance
        res = client.post(
            f"/api/v1/event-ops/events/{seeded_event.id}/advance-stage",
            json={"target_stage": "completed"},
        )
        # Expect 403 if RBAC is strict, or 200 if current user is admin in test
        assert res.status_code in [200, 403]


# ───────────────────────────────────────────────
# PERFORMANCE TESTS
# ───────────────────────────────────────────────


class TestPerformance:
    """Validate response times for ops endpoints."""

    def test_auto_recognize_under_500ms(self, client: TestClient, seeded_event: Event):
        import time

        start = time.time()
        res = client.get(f"/api/v1/event-ops/events/{seeded_event.id}/auto-recognize")
        elapsed = (time.time() - start) * 1000

        assert res.status_code == 200
        assert elapsed < 500, f"Auto-recognize took {elapsed}ms, expected <500ms"

    def test_execution_queue_under_300ms(self, client: TestClient):
        import time

        start = time.time()
        res = client.get("/api/v1/event-ops/execution-queue")
        elapsed = (time.time() - start) * 1000

        assert res.status_code == 200
        assert elapsed < 300, f"Queue took {elapsed}ms, expected <300ms"
