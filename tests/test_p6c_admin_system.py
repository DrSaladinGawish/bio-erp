"""P6C smoke tests: Admin, Auth, System & Strategic routers.

One test per router — verifies no 500 error on basic GET.
8 tests covering: admin, auth, system, strategic cost, costing.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestAdminAuth:
    ENDPOINTS = [
        "/api/v1/admin/users",
        "/api/v1/admin/roles",
        "/api/v1/admin/permissions",
        "/api/v1/admin/audit-log",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_401_without_auth(self, path: str, client: AsyncClient):
        resp = await client.get(path)
        assert resp.status_code in (401, 403), f"{path} should require auth, got {resp.status_code}"


class TestAuthMe:
    async def test_me_returns_200(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200

    async def test_me_returns_401_without_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)


class TestStrategicCost:
    ENDPOINTS = [
        "/strategic/target-costing",
        "/strategic/variance",
        "/strategic/kaizen",
        "/strategic/bsc",
        "/strategic/profitability/event/1",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


class TestCostingAnalysis:
    ENDPOINTS = [
        "/margin-analysis",
        "/biological-health",
        "/variance/1",
        "/abc/1",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"
