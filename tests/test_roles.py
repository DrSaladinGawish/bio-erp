"""Tests for roles & RBAC endpoints (v2.4.2)."""
from __future__ import annotations

import os

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
def seeded_user():
    """Create a non-admin user for role assignment tests."""
    from app.auth import hash_password

    with SyncSession(_sync_engine) as session, session.begin():
        result = session.execute(
            text("SELECT id FROM users WHERE username = 'role_test_user'")
        )
        existing = result.scalar()
        if existing:
            yield {"user_id": existing}
            return

        branch = session.execute(text("SELECT id FROM branches LIMIT 1")).scalar()

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        session.execute(
            text(
                """INSERT INTO users (username, email, hashed_password, full_name_en,
                    branch_id, is_superuser, is_active, created_at, updated_at)
                VALUES (:u, :e, :p, :n, :b, false, true, :now, :now)"""
            ),
            {
                "u": "role_test_user",
                "e": "role_test@bioerp.local",
                "p": hash_password("test123"),
                "n": "Role Test User",
                "b": branch or 1,
                "now": now,
            },
        )
        session.flush()
        result = session.execute(
            text("SELECT id FROM users WHERE username = 'role_test_user'")
        )
        user_id = result.scalar()

    yield {"user_id": user_id}

    with SyncSession(_sync_engine) as session, session.begin():
        session.execute(
            text("DELETE FROM user_roles WHERE user_id = :uid"), {"uid": user_id}
        )
        session.execute(
            text("DELETE FROM users WHERE id = :uid"), {"uid": user_id}
        )


async def test_list_roles(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/roles/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    names = [r["name"] for r in data]
    assert "admin" in names
    assert "manager" in names
    assert "operator" in names
    assert "read_only" in names


async def test_list_roles_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/roles/")
    assert resp.status_code == 403


async def test_my_permissions(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/roles/my-permissions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_superuser"] is True
    assert data["username"] == "admin"
    assert isinstance(data["permissions"], list)


async def test_my_permissions_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/roles/my-permissions")
    assert resp.status_code == 403


async def test_get_role_by_id(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/roles/", headers=auth_headers)
    roles = resp.json()
    assert len(roles) > 0
    role_id = roles[0]["id"]

    resp = await client.get(
        f"/api/v1/roles/{role_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == role_id
    assert "name" in data
    assert "permissions" in data


async def test_get_role_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/roles/99999", headers=auth_headers)
    assert resp.status_code == 404


async def test_assign_role(
    client: AsyncClient, auth_headers: dict, seeded_user: dict
):
    resp = await client.get("/api/v1/roles/", headers=auth_headers)
    roles = resp.json()
    read_only = next(r for r in roles if r["name"] == "read_only")

    resp = await client.post(
        f"/api/v1/roles/{read_only['id']}/assign/{seeded_user['user_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "assigned" in resp.json()["message"].lower()


async def test_remove_role(
    client: AsyncClient, auth_headers: dict, seeded_user: dict
):
    resp = await client.get("/api/v1/roles/", headers=auth_headers)
    roles = resp.json()
    read_only = next(r for r in roles if r["name"] == "read_only")

    await client.post(
        f"/api/v1/roles/{read_only['id']}/assign/{seeded_user['user_id']}",
        headers=auth_headers,
    )

    resp = await client.request(
        "DELETE",
        f"/api/v1/roles/{read_only['id']}/assign/{seeded_user['user_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "removed" in resp.json()["message"].lower()
