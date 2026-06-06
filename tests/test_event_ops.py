"""Tests for Event Lifecycle Operations (v2.5.0)."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as SyncSession

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp_test",
)
_sync_url = TEST_DB_URL.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, echo=False)


@pytest.fixture
def seeded_event():
    """Create a test event with ops briefing data, clean up after."""
    from app.models import Client, Event, EventOperation

    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    client_code = f"TST-EVENTS-{uid}"

    with SyncSession(_sync_engine) as session:
        with session.begin():
            branch_id = session.execute(
                text("SELECT id FROM branches WHERE code = 'HQ'")
            ).scalar()
            currency_id = session.execute(
                text("SELECT id FROM currencies WHERE code = 'USD'")
            ).scalar()

            client = Client(
                code=client_code,
                name_en="Test Events Client",
                branch_id=branch_id,
            )
            session.add(client)
            session.flush()
            client_id = client.id

            event = Event(
                event_code=f"EVT-TEST-{uid}",
                client_id=client_id,
                name_en="Test Event for Ops",
                venue="Test Venue",
                start_date="2026-06-15",
                end_date="2026-06-16",
                duration_days=2,
                lifecycle_status="CONFIRMED",
                execution_date=now,
                actual_pax=100,
                actual_cost=50000.0,
                total_revenue=100000.0,
                branch_id=branch_id,
                currency_id=currency_id,
                conversion_rate=1.0,
                amount_egp=100000.0,
            )
            session.add(event)
            session.flush()
            event_id = event.id

            ops = EventOperation(
                event_id=event_id,
                briefing_completed=False,
                sound_check_done=False,
            )
            session.add(ops)
            session.flush()
            ops_id = ops.id

    yield {
        "event_id": event_id,
        "ops_id": ops_id,
        "client_id": client_id,
        "client_code": client_code,
    }

    with SyncSession(_sync_engine) as session:
        with session.begin():
            session.execute(
                text("DELETE FROM event_operations WHERE id = :oid"),
                {"oid": ops_id},
            )
            session.execute(
                text("DELETE FROM events WHERE id = :eid"),
                {"eid": event_id},
            )
            session.execute(
                text("DELETE FROM clients WHERE code = :cc"),
                {"cc": client_code},
            )


@pytest.fixture
def seeded_event_without_ops():
    """Create a test event WITHOUT ops briefing (for briefing creation tests)."""
    from app.models import Client, Event

    uid = uuid.uuid4().hex[:6]

    with SyncSession(_sync_engine) as session:
        with session.begin():
            branch_id = session.execute(
                text("SELECT id FROM branches WHERE code = 'HQ'")
            ).scalar()
            currency_id = session.execute(
                text("SELECT id FROM currencies WHERE code = 'USD'")
            ).scalar()

            client = Client(
                code=f"TST-EV2-{uid}",
                name_en="Test Events Client 2",
                branch_id=branch_id,
            )
            session.add(client)
            session.flush()
            client_id = client.id

            event = Event(
                event_code=f"EVT-TEST2-{uid}",
                client_id=client_id,
                name_en="Test Event for Ops 2",
                venue="Another Venue",
                start_date="2026-07-01",
                end_date="2026-07-02",
                duration_days=2,
                lifecycle_status="DRAFT",
                branch_id=branch_id,
                currency_id=currency_id,
                conversion_rate=1.0,
                amount_egp=0.0,
            )
            session.add(event)
            session.flush()
            event_id = event.id

    yield {"event_id": event_id, "client_id": client_id}

    with SyncSession(_sync_engine) as session:
        with session.begin():
            session.execute(
                text("DELETE FROM event_operations WHERE event_id = :eid"),
                {"eid": event_id},
            )
            session.execute(
                text("DELETE FROM events WHERE id = :eid2"),
                {"eid2": event_id},
            )
            session.execute(
                text("DELETE FROM clients WHERE id = :cid"),
                {"cid": client_id},
            )


# ── Lifecycle Transitions ──────────────────────────────────────────


async def test_lifecycle_transition(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    event_id = seeded_event["event_id"]
    resp = await client.post(
        f"/api/v1/event-ops/lifecycle/{event_id}",
        headers=auth_headers,
        json={"lifecycle_status": "IN_PROGRESS"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == event_id
    assert data["lifecycle_status"] == "IN_PROGRESS"


async def test_lifecycle_transition_invalid_status(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    event_id = seeded_event["event_id"]
    resp = await client.post(
        f"/api/v1/event-ops/lifecycle/{event_id}",
        headers=auth_headers,
        json={"lifecycle_status": "INVALID_STATUS"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data


async def test_lifecycle_transition_not_found(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.post(
        "/api/v1/event-ops/lifecycle/99999",
        headers=auth_headers,
        json={"lifecycle_status": "EXECUTED"},
    )
    assert resp.status_code == 404


# ── Ops Briefing ───────────────────────────────────────────────────


async def test_ops_briefing_create(
    client: AsyncClient, auth_headers: dict, seeded_event_without_ops: dict
):
    event_id = seeded_event_without_ops["event_id"]
    resp = await client.post(
        f"/api/v1/event-ops/briefing/{event_id}",
        headers=auth_headers,
        json={
            "briefing_completed": True,
            "sound_check_done": True,
            "catering_final_count": 120,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_ops_briefing_get(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    event_id = seeded_event["event_id"]
    resp = await client.get(
        f"/api/v1/event-ops/briefing/{event_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == event_id
    assert "briefing_completed" in data


# ── Run Sheet ──────────────────────────────────────────────────────


async def test_run_sheet_update(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    event_id = seeded_event["event_id"]
    run_sheet = [
        {"time": "09:00", "activity": "Load in", "owner": "Ops", "status": "done"},
        {"time": "10:00", "activity": "Sound check", "owner": "AV", "status": "done"},
    ]
    resp = await client.put(
        f"/api/v1/event-ops/run-sheet/{event_id}",
        headers=auth_headers,
        json={"run_sheet": run_sheet},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    # Verify by getting it back
    resp2 = await client.get(
        f"/api/v1/event-ops/run-sheet/{event_id}",
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["run_sheet"] == run_sheet


# ── Post-Event Report ──────────────────────────────────────────────


async def test_post_event_report(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    event_id = seeded_event["event_id"]
    resp = await client.post(
        f"/api/v1/event-ops/post-event/{event_id}",
        headers=auth_headers,
        json={
            "post_event_notes": "Event went well. Minor AV issue resolved.",
            "client_signatory_name": "John Smith",
            "actual_pax": 98,
            "actual_cost": 48000.0,
            "lifecycle_status": "EXECUTED",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ── Recognition ────────────────────────────────────────────────────


async def test_recognition_suggest_services(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    client_id = seeded_event["client_id"]
    resp = await client.get(
        f"/api/v1/event-ops/recognition/suggest-services?client_id={client_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "client_history" in data
    assert "category_template" in data


# ── Ops Dashboard ─────────────────────────────────────────────────


async def test_ops_dashboard(
    client: AsyncClient, auth_headers: dict, seeded_event: dict
):
    resp = await client.get(
        "/api/v1/event-ops/dashboard",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "today_count" in data
    assert "week_count" in data
    assert "pending_briefings" in data
    assert "todays_events" in data
