"""P6B smoke tests: E-Invoice, GRDSLAB, Dashboard & Events routers.

One test per router — verifies no 500 error on basic GET.
10 tests covering: events, dashboard, GRDSLAB, reports, monitoring.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestEvents:
    ENDPOINTS = [
        "/api/v1/events",
        "/api/v1/events/branch-summary",
        "/api/v1/events/sync-status",
        "/api/v1/events/pipeline",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


class TestDashboard:
    ENDPOINTS = [
        "/api/v1/dashboard/stats",
        "/api/v1/dashboard/top-clients",
        "/api/v1/dashboard/recent-events",
        "/api/v1/dashboard/supplier-performance",
        "/api/v1/dashboard/eta-compliance",
        "/api/v1/dashboard/branch-comparison",
        "/api/v1/dashboard/",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


class TestGRDSLAB:
    ENDPOINTS = [
        "/api/v1/grdslab/convert",
        "/api/v1/grdslab/soil-types",
        "/api/v1/grdslab/forklift-table",
        "/api/v1/grdslab/aashto-trucks",
        "/api/v1/grdslab/conversion-factors",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient):
        resp = await client.get(path)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


class TestHealthMonitoring:
    ENDPOINTS = [
        "/health",
        "/",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient):
        resp = await client.get(path)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"
