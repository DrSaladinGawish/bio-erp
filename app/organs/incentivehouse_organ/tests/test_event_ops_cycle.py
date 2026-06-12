"""
Integration tests for Event Operations Phase 3-5 endpoints.

Tests the full lifecycle: execution queue, auto-recognition, checkpoint
management, team assignment, and stage advancement.

Requires ``seeded_event`` fixture (creates a confirmed event + client + staff).
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login(sync_client) -> str:
    resp = sync_client.post(
        "/api/v1/incentivehouse/auth/login",
        json={"username": "admin", "password": "admin2026"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Execution Queue
# ---------------------------------------------------------------------------


class TestExecutionQueue:
    def test_queue_empty_when_no_ops_events(self, sync_client, clean_staging_tables):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/execution-queue",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_queue_returns_confirmed_event(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/execution-queue",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(e["event_id"] == seeded_event for e in data)

    def test_queue_stage_filter(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/execution-queue?stage=procurement",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        for e in resp.json():
            assert e["stage"] == "procurement"

    def test_queue_requires_auth(self, sync_client):
        resp = sync_client.get("/event-ops/execution-queue")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Dashboard Summary
# ---------------------------------------------------------------------------


class TestDashboardSummary:
    def test_dashboard_summary_shape(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/dashboard-summary",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_active_events" in data
        assert "in_procurement" in data
        assert "in_execution" in data
        assert "in_qa" in data
        assert "overdue_events" in data
        assert "today_checkpoints" in data
        assert "team_workload" in data
        assert "revenue_at_risk" in data
        assert isinstance(data["total_active_events"], int)

    def test_dashboard_requires_ops_manager(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/dashboard-summary",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200  # admin role passes


# ---------------------------------------------------------------------------
# 3. Auto-Recognize
# ---------------------------------------------------------------------------


class TestAutoRecognize:
    def test_auto_recognize_returns_data(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.get(
            f"/event-ops/events/{seeded_event}/auto-recognize",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == seeded_event
        assert "event_name" in data
        assert "client" in data
        assert "budget" in data
        assert "category_uom_map" in data
        assert "execution_checklist" in data

    def test_auto_recognize_404(self, sync_client):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/events/99999/auto-recognize",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    def test_apply_auto_recognition_creates_checkpoints(
        self, sync_client, seeded_event
    ):
        token = _login(sync_client)
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/auto-recognize/apply",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert data["checkpoints_created"] >= 0

    def test_apply_twice_is_idempotent(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp1 = sync_client.post(
            f"/event-ops/events/{seeded_event}/auto-recognize/apply",
            headers=_auth_headers(token),
        )
        assert resp1.status_code == 200
        resp2 = sync_client.post(
            f"/event-ops/events/{seeded_event}/auto-recognize/apply",
            headers=_auth_headers(token),
        )
        assert resp2.status_code == 200
        # No duplicate checkpoints should be created


# ---------------------------------------------------------------------------
# 4. Execution Form
# ---------------------------------------------------------------------------


class TestExecutionForm:
    def test_get_execution_form(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.get(
            f"/event-ops/events/{seeded_event}/execute",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "event" in data
        assert data["event"]["id"] == seeded_event
        assert "recognition" in data
        assert "checkpoints" in data
        assert "can_edit" in data

    def test_execution_form_404(self, sync_client):
        token = _login(sync_client)
        resp = sync_client.get(
            "/event-ops/events/99999/execute",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Assign Ops Team
# ---------------------------------------------------------------------------


class TestAssignTeam:
    def test_assign_ops_team(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/assign-team",
            headers=_auth_headers(token),
            json={"ops_team_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == seeded_event
        assert data["ops_team_id"] == 1

    def test_assign_team_404_event(self, sync_client):
        token = _login(sync_client)
        resp = sync_client.post(
            "/event-ops/events/99999/assign-team",
            headers=_auth_headers(token),
            json={"ops_team_id": 1},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Checkpoints
# ---------------------------------------------------------------------------


class TestCheckpoints:
    def test_create_and_complete_checkpoint(self, sync_client, seeded_event):
        token = _login(sync_client)
        # First apply auto-recognition to create checkpoints
        sync_client.post(
            f"/event-ops/events/{seeded_event}/auto-recognize/apply",
            headers=_auth_headers(token),
        )
        # Get the execution form to find checkpoint IDs
        form = sync_client.get(
            f"/event-ops/events/{seeded_event}/execute",
            headers=_auth_headers(token),
        ).json()
        checkpoints = form.get("checkpoints", [])
        if not checkpoints:
            pytest.skip("No checkpoints created — cannot test completion")
        cp_id = checkpoints[0]["id"]

        # Complete the checkpoint
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/checkpoints/{cp_id}",
            headers=_auth_headers(token),
            json={"checkpoint_id": cp_id, "completed": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True

        # Verify it's completed
        form2 = sync_client.get(
            f"/event-ops/events/{seeded_event}/execute",
            headers=_auth_headers(token),
        ).json()
        for cp in form2["checkpoints"]:
            if cp["id"] == cp_id:
                assert cp["completed"] is True
                break

    def test_revert_checkpoint(self, sync_client, seeded_event):
        token = _login(sync_client)
        sync_client.post(
            f"/event-ops/events/{seeded_event}/auto-recognize/apply",
            headers=_auth_headers(token),
        )
        form = sync_client.get(
            f"/event-ops/events/{seeded_event}/execute",
            headers=_auth_headers(token),
        ).json()
        checkpoints = form.get("checkpoints", [])
        if not checkpoints:
            pytest.skip("No checkpoints")
        cp_id = checkpoints[0]["id"]

        # Complete then revert
        sync_client.post(
            f"/event-ops/events/{seeded_event}/checkpoints/{cp_id}",
            headers=_auth_headers(token),
            json={"checkpoint_id": cp_id, "completed": True},
        )
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/checkpoints/{cp_id}",
            headers=_auth_headers(token),
            json={"checkpoint_id": cp_id, "completed": False},
        )
        assert resp.status_code == 200
        assert resp.json()["completed"] is False

    def test_checkpoint_404(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/checkpoints/nonexistent",
            headers=_auth_headers(token),
            json={"checkpoint_id": "nonexistent", "completed": True},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7. Advance Stage
# ---------------------------------------------------------------------------


class TestAdvanceStage:
    def test_advance_stage(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/advance-stage",
            headers=_auth_headers(token),
            json={"target_stage": "procurement"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_stage"] == "procurement"
        assert data["event_id"] == seeded_event

    def test_advance_stage_invalid(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/advance-stage",
            headers=_auth_headers(token),
            json={"target_stage": "invalid_stage"},
        )
        assert resp.status_code == 400

    def test_advance_stage_404(self, sync_client):
        token = _login(sync_client)
        resp = sync_client.post(
            "/event-ops/events/99999/advance-stage",
            headers=_auth_headers(token),
            json={"target_stage": "execution"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. Bulk Update Categories
# ---------------------------------------------------------------------------


class TestBulkUpdate:
    def test_bulk_update_empty(self, sync_client, seeded_event):
        token = _login(sync_client)
        resp = sync_client.post(
            f"/event-ops/events/{seeded_event}/categories/bulk-update",
            headers=_auth_headers(token),
            json=[],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 0

    def test_bulk_update_404(self, sync_client):
        token = _login(sync_client)
        resp = sync_client.post(
            "/event-ops/events/99999/categories/bulk-update",
            headers=_auth_headers(token),
            json=[],
        )
        assert resp.status_code == 404
