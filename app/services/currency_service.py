from datetime import datetime, timezone


class CurrencyService:
    FALLBACK_RATES = {
        "USD": 1.0,
        "EGP": 50.5,
        "EUR": 0.92,
        "GBP": 0.79,
        "SAR": 3.75,
        "AED": 3.67,
    }

    def __init__(self):
        self.base_url = "https://api.exchangerate-api.com/v4/latest/USD"
        self.rates: dict[str, float] = {}
        self.last_update: datetime | None = None
        self._fallback_loaded = False

    async def _refresh_rates(self) -> None:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.base_url)
                if resp.status_code == 200:
                    data = resp.json()
                    self.rates = data.get("rates", {})
                    self.last_update = datetime.now(timezone.utc)
                    return
        except Exception:
            pass
        if not self._fallback_loaded:
            self.rates = dict(self.FALLBACK_RATES)
            self._fallback_loaded = True
            self.last_update = datetime.now(timezone.utc)

    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        if not self.rates:
            await self._refresh_rates()
        from_rate = self.rates.get(from_currency.upper())
        to_rate = self.rates.get(to_currency.upper())
        if from_rate is None or to_rate is None:
            raise ValueError(f"Unsupported currency: {from_currency} → {to_currency}")
        return to_rate / from_rate

    async def convert(self, amount: float, from_currency: str, to_currency: str) -> dict:
        rate = await self.get_rate(from_currency, to_currency)
        return {
            "original_amount": amount,
            "original_currency": from_currency.upper(),
            "converted_amount": round(amount * rate, 2),
            "converted_currency": to_currency.upper(),
            "rate": round(rate, 6),
            "rate_source": "live" if self.last_update else "fallback",
        }


currency_service = CurrencyService()
