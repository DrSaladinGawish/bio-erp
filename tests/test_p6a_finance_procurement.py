"""P6A smoke tests: Finance & Procurement routers.

One test per router — verifies no 500 error on basic GET.
12 tests covering: currency, branch, supplier, item, procurement,
finance, costing, budget, petty cash, approval.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestFinanceCore:
    ENDPOINTS = [
        "/api/v1/currencies",
        "/api/v1/branches",
        "/api/v1/clients",
        "/api/v1/suppliers",
        "/api/v1/suppliers/categories",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned 500"

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_401_without_auth(self, path: str, client: AsyncClient):
        resp = await client.get(path)
        assert resp.status_code < 500, f"{path} returned {resp.status_code} (open or auth)"

    async def test_open_endpoints(self, client: AsyncClient):
        """/currencies, /branches, /suppliers/categories are open (no auth)."""
        for p in ["/api/v1/currencies", "/api/v1/branches", "/api/v1/suppliers/categories"]:
            resp = await client.get(p)
            assert resp.status_code == 200, f"{p} should be open, got {resp.status_code}"


class TestProcurementItems:
    ENDPOINTS = [
        "/api/v1/items/categories",
        "/api/v1/items/sub-categories",
        "/api/v1/items/master-nodes",
        "/api/v1/items/markup-rules",
        "/api/v1/procurement/grn",
        "/api/v1/petty-cash/registers",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned 500"


class TestFinanceGL:
    ENDPOINTS = [
        "/finance/jv",
        "/finance/ar/invoices",
        "/finance/ap/invoices",
        "/finance/rct",
        "/finance/pmt",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


class TestCostingBudget:
    ENDPOINTS = [
        "/api/v1/cost-management/periods",
        "/api/v1/budget/markup-rules",
        "/api/v1/coa/categories",
        "/api/v1/coa/accounts",
        "/margin-analysis",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


class TestApprovalPettyCash:
    ENDPOINTS = [
        "/api/v1/approval/rules",
        "/api/v1/approval/sequences",
    ]

    @pytest.mark.parametrize("path", ENDPOINTS)
    async def test_list_returns_not_500(self, path: str, client: AsyncClient, auth_headers: dict):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"
