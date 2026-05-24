"""P0 smoke tests for BIO_ERP v5.

Categories (17 tests):
  Root / Health         3
  Auth Login            5
  Ledger Inquiry        4
  Ledger Entries        3
  DB Integrity          2

Every test is isolated — database changes roll back automatically.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ═══════════════════════════════════════════════════════════════════
#  Category 1 — Root / Health  (3)
# ═══════════════════════════════════════════════════════════════════

class TestRootHealth:
    async def test_root_returns_200(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200

    async def test_root_returns_json(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.headers.get("content-type", "").startswith("application/json")

    async def test_root_has_expected_keys(self, client: AsyncClient):
        resp = await client.get("/")
        body = resp.json()
        assert "version" in body
        assert body["message"] == "BIO_ERP v5"


# ═══════════════════════════════════════════════════════════════════
#  Category 2 — Auth Login  (5)
# ═══════════════════════════════════════════════════════════════════

class TestAuthLogin:
    async def test_login_valid_credentials_returns_200(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/accounting/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200

    async def test_login_returns_valid_jwt_structure(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/accounting/login",
            json={"username": "admin", "password": "admin123"},
        )
        body = resp.json()
        assert "access_token" in body
        parts = body["access_token"].split(".")
        assert len(parts) == 3

    async def test_login_invalid_password_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/accounting/login",
            json={"username": "admin", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/accounting/login",
            json={"username": "ghost", "password": "anything"},
        )
        assert resp.status_code == 401

    async def test_login_missing_fields_returns_400_or_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/accounting/login",
            json={"username": "admin"},
        )
        assert resp.status_code in (400, 422)


# ═══════════════════════════════════════════════════════════════════
#  Category 3 — Ledger Inquiry  (4)
# ═══════════════════════════════════════════════════════════════════

class TestLedgerInquiry:
    async def test_ledger_inquiry_returns_200(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/accounting/ledger-inquiry", headers=auth_headers)
        assert resp.status_code == 200

    async def test_ledger_inquiry_returns_html(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/accounting/ledger-inquiry", headers=auth_headers)
        assert "text/html" in resp.headers.get("content-type", "")

    async def test_ledger_inquiry_contains_table_structure(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/accounting/ledger-inquiry", headers=auth_headers)
        html = resp.text
        assert "Ledger Inquiry" in html
        assert "<table" in html or "table" in html.lower()

    async def test_ledger_inquiry_unauthorized_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/accounting/ledger-inquiry")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  Category 4 — Ledger Entries  (3)
# ═══════════════════════════════════════════════════════════════════

class TestLedgerEntries:
    async def test_ledger_entries_returns_200(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/accounting/ledger-entries", headers=auth_headers)
        assert resp.status_code == 200

    async def test_ledger_entries_has_htmx_headers_or_fragment(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/accounting/ledger-entries", headers=auth_headers)
        assert "text/html" in resp.headers.get("content-type", "")
        assert "<table" in resp.text or "table-responsive" in resp.text

    async def test_ledger_entries_unauthorized_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/accounting/ledger-entries")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  Category 5 — DB Integrity  (2)
# ═══════════════════════════════════════════════════════════════════

class TestDatabaseIntegrity:
    async def test_db_session_active(self, db_session: AsyncSession):
        result = await db_session.execute(text("SELECT 1 AS ok"))
        assert result.scalar_one() == 1

    async def test_db_isolation(self, db_session: AsyncSession):
        result = await db_session.execute(text("SELECT current_database()"))
        db_name = result.scalar_one()
        assert db_name.endswith("_test"), (
            f"Tests are pointing at '{db_name}' — expected *_test database"
        )
