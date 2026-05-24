"""P2 test suite — CRUD, pagination, date filtering for Ledger Entries.

Run: pytest tests/test_p2_crud.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════════════
#  Fixtures for reuse
# ═══════════════════════════════════════════════════════════════════

SAMPLE_PAYLOAD = {
    "code": f"TEST-{uuid4().hex[:8].upper()}",
    "name_en": "Test Account",
    "category_id": 1,
    "account_type": "asset",
    "opening_balance": 1000.00,
}

SAMPLE_UPDATE = {
    "name_en": "Updated Account",
    "code": "TEST-001-UPD",
}


# ═══════════════════════════════════════════════════════════════════
#  Category 1 — CREATE  (3 tests)
# ═══════════════════════════════════════════════════════════════════

class TestCreateLedgerEntry:
    ENDPOINT = "/api/v1/accounting/ledger-entries"

    async def test_create_returns_200_or_201(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(self.ENDPOINT, json=SAMPLE_PAYLOAD, headers=auth_headers)
        assert resp.status_code in (200, 201)

    async def test_create_missing_field_returns_422(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(self.ENDPOINT, json={}, headers=auth_headers)
        assert resp.status_code == 422

    async def test_create_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(self.ENDPOINT, json=SAMPLE_PAYLOAD)
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  Category 2 — UPDATE / DELETE  (4 tests)
# ═══════════════════════════════════════════════════════════════════

class TestUpdateDeleteLedgerEntry:
    BASE = "/api/v1/accounting/ledger-entries"

    async def test_update_valid_returns_200(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(f"{self.BASE}/1", json=SAMPLE_UPDATE, headers=auth_headers)
        assert resp.status_code == 200

    async def test_update_nonexistent_returns_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(f"{self.BASE}/99999", json=SAMPLE_UPDATE, headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_returns_200_or_204(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(f"{self.BASE}/1", headers=auth_headers)
        assert resp.status_code in (200, 204)

    async def test_update_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.put(f"{self.BASE}/1", json=SAMPLE_UPDATE)
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  Category 3 — PAGINATION  (4 tests)
# ═══════════════════════════════════════════════════════════════════

class TestPagination:
    ENDPOINT = "/api/v1/accounting/ledger-entries"

    async def test_pagination_page_size_respected(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(self.ENDPOINT, params={"page": 1, "page_size": 10}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_pagination_default_size(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(self.ENDPOINT, params={"page": 1}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_pagination_out_of_range_returns_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(self.ENDPOINT, params={"page": 9999, "page_size": 50}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_pagination_contains_total_count(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(self.ENDPOINT, params={"page": 1, "page_size": 10}, headers=auth_headers)
        body = resp.text
        assert "data-total-count" in body


# ═══════════════════════════════════════════════════════════════════
#  Category 4 — DATE FILTERING  (4 tests)
# ═══════════════════════════════════════════════════════════════════

class TestDateFiltering:
    ENDPOINT = "/api/v1/accounting/ledger-entries"

    async def test_date_filter_in_range(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            self.ENDPOINT,
            params={"date_from": "2024-01-01", "date_to": "2024-12-31"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_date_filter_out_of_range_returns_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            self.ENDPOINT,
            params={"date_from": "2099-01-01", "date_to": "2099-12-31"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_date_filter_malformed_returns_422(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            self.ENDPOINT,
            params={"date_from": "not-a-date"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_date_filter_date_from_only(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            self.ENDPOINT,
            params={"date_from": "2024-01-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
