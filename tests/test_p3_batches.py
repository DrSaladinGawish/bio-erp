"""P3 smoke tests — Batch lifecycle (CRUD + state machine).

Run: pytest tests/test_p3_batches.py -v
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


BASE = "/api/v1/manufacturing/batches"

SAMPLE_PAYLOAD = {
    "volume_l": 100.0,
    "target_biomass_gl": 15.0,
    "notes": "Test batch",
}

SAMPLE_UPDATE = {
    "volume_l": 200.0,
    "notes": "Updated test batch",
}


# ═══════════════════════════════════════════════════════════════════
#  Category 1 — CRUD  (6 tests)
# ═══════════════════════════════════════════════════════════════════

class TestBatchCRUD:

    async def test_create_returns_201(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(BASE, json=SAMPLE_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["batch_number"].startswith("BIO-")
        assert body["status"] == "draft"
        assert body["volume_l"] == 100.0

    async def test_create_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(BASE, json=SAMPLE_PAYLOAD)
        assert resp.status_code == 401

    async def test_list_returns_200(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "total" in body
        assert "page" in body

    async def test_list_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(BASE)
        assert resp.status_code == 401

    async def test_get_by_id_returns_200(self, client: AsyncClient, auth_headers: dict):
        created = await client.post(BASE, json=SAMPLE_PAYLOAD, headers=auth_headers)
        bid = created.json()["id"]
        resp = await client.get(f"{BASE}/{bid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == bid

    async def test_get_nonexistent_returns_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(f"{BASE}/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_update_returns_200(self, client: AsyncClient, auth_headers: dict):
        created = await client.post(BASE, json=SAMPLE_PAYLOAD, headers=auth_headers)
        bid = created.json()["id"]
        resp = await client.put(f"{BASE}/{bid}", json=SAMPLE_UPDATE, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["volume_l"] == 200.0

    async def test_update_nonexistent_returns_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(f"{BASE}/99999", json=SAMPLE_UPDATE, headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_returns_200(self, client: AsyncClient, auth_headers: dict):
        created = await client.post(BASE, json=SAMPLE_PAYLOAD, headers=auth_headers)
        bid = created.json()["id"]
        resp = await client.delete(f"{BASE}/{bid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(f"{BASE}/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.delete(f"{BASE}/1")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  Category 2 — State Machine  (6 tests)
# ═══════════════════════════════════════════════════════════════════

class TestBatchStateMachine:

    async def _create_draft(self, client, auth_headers) -> int:
        resp = await client.post(BASE, json=SAMPLE_PAYLOAD, headers=auth_headers)
        return resp.json()["id"]

    async def test_draft_to_released(self, client: AsyncClient, auth_headers: dict):
        bid = await self._create_draft(client, auth_headers)
        resp = await client.post(f"{BASE}/{bid}/release", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "released"

    async def test_released_to_in_progress(self, client: AsyncClient, auth_headers: dict):
        bid = await self._create_draft(client, auth_headers)
        await client.post(f"{BASE}/{bid}/release", headers=auth_headers)
        resp = await client.post(f"{BASE}/{bid}/start", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    async def test_in_progress_to_completed(self, client: AsyncClient, auth_headers: dict):
        bid = await self._create_draft(client, auth_headers)
        await client.post(f"{BASE}/{bid}/release", headers=auth_headers)
        await client.post(f"{BASE}/{bid}/start", headers=auth_headers)
        resp = await client.post(f"{BASE}/{bid}/complete?actual_biomass_gl=12.5", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["actual_biomass_gl"] == 12.5

    async def test_completed_to_archived(self, client: AsyncClient, auth_headers: dict):
        bid = await self._create_draft(client, auth_headers)
        await client.post(f"{BASE}/{bid}/release", headers=auth_headers)
        await client.post(f"{BASE}/{bid}/start", headers=auth_headers)
        await client.post(f"{BASE}/{bid}/complete", headers=auth_headers)
        resp = await client.post(f"{BASE}/{bid}/archive", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    async def test_draft_to_cancelled(self, client: AsyncClient, auth_headers: dict):
        bid = await self._create_draft(client, auth_headers)
        resp = await client.post(f"{BASE}/{bid}/cancel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_invalid_transition_returns_400(self, client: AsyncClient, auth_headers: dict):
        bid = await self._create_draft(client, auth_headers)
        resp = await client.post(f"{BASE}/{bid}/complete", headers=auth_headers)
        assert resp.status_code == 400

    async def test_state_machine_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/1/release")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  Category 3 — Pagination & Filtering  (2 tests)
# ═══════════════════════════════════════════════════════════════════

class TestBatchPagination:

    async def test_pagination_defaults(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert isinstance(body["data"], list)

    async def test_filter_by_status(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(f"{BASE}?status=draft", headers=auth_headers)
        assert resp.status_code == 200
        for b in resp.json()["data"]:
            assert b["status"] == "draft"
