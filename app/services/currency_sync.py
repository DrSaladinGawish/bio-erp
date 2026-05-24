import httpx
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.currency import Currency


class CurrencySyncService:
    CBE_URL = "https://www.cbe.org.eg/api/currency-rates"
    FALLBACK_URLS = [
        "https://api.exchangerate-api.com/v4/latest/EGP",
        "https://api.bankfxapi.com/v1/rates",
    ]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_from_cbe(self) -> dict:
        results = {"updated": [], "failed": []}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self.CBE_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    for rate_data in data.get("rates", []):
                        await self._update_rate(
                            rate_data["currency"],
                            rate_data.get("mid", 1.0),
                            rate_data.get("buy"),
                            rate_data.get("sell"),
                        )
                        results["updated"].append(rate_data["currency"])
        except Exception as e:
            results["failed"].append(f"CBE: {str(e)}")
            await self._try_fallback(results)
        return results

    async def _try_fallback(self, results: dict):
        for url in self.FALLBACK_URLS:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        data.get("base", "USD")
                        base_rate = data.get("rates", {}).get("EGP", 1.0)
                        for code, rate in data.get("rates", {}).items():
                            egp_rate = rate / base_rate if base_rate else 0
                            await self._update_rate(code, round(egp_rate, 6))
                            if code not in results["updated"]:
                                results["updated"].append(code)
                        return
            except Exception as e:
                results["failed"].append(f"Fallback {url}: {str(e)}")

    async def _update_rate(
        self, code: str, mid: float, buy: float | None = None, sell: float | None = None
    ):
        result = await self.session.execute(
            select(Currency).where(Currency.code == code.upper())
        )
        currency = result.scalar_one_or_none()
        if currency:
            currency.mid_rate = mid
            if buy:
                currency.buy_rate = buy
            if sell:
                currency.sell_rate = sell
            currency.last_sync_at = datetime.now(timezone.utc).replace(tzinfo=None)
