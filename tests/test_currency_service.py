"""Day 2 — Currency Service tests (6 tests)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.currency_service import CurrencyService


class TestCurrencyService:
    async def test_currency_service_initializes(self):
        service = CurrencyService()
        assert service.base_url is not None
        assert len(service.rates) == 0

    @patch("httpx.AsyncClient.get", side_effect=Exception("Network error"))
    async def test_refresh_rates_fallback(self, mock_get):
        service = CurrencyService()
        await service._refresh_rates()
        assert "USD" in service.rates
        assert "EGP" in service.rates
        assert service.rates["USD"] == 1.0
        assert service.last_update is not None

    async def test_get_rate_calculates(self):
        service = CurrencyService()
        service.rates = {"USD": 1.0, "EGP": 50.5, "EUR": 0.92}
        service.last_update = datetime.now()
        rate = await service.get_rate("USD", "EGP")
        assert rate == 50.5
        rate = await service.get_rate("EUR", "USD")
        assert abs(rate - 1.087) < 0.01

    async def test_convert_returns_structure(self):
        service = CurrencyService()
        service.rates = {"USD": 1.0, "EGP": 50.5}
        service.last_update = datetime.now()
        result = await service.convert(100.0, "USD", "EGP")
        assert result["original_amount"] == 100.0
        assert result["original_currency"] == "USD"
        assert result["converted_currency"] == "EGP"
        assert result["converted_amount"] == 5050.0
        assert "rate" in result

    async def test_currency_api_endpoint(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/currency/convert?amount=100&from=USD&to=EGP"
        )
        assert resp.status_code < 500

    async def test_currency_rates_endpoint(self, client: AsyncClient):
        resp = await client.get("/api/v1/currency/rates")
        assert resp.status_code < 500
        data = resp.json()
        assert "base" in data
        assert "rates" in data
