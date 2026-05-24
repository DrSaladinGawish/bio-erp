import httpx
from datetime import datetime
from datetime import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Currency, CurrencyRate

CBE_API_URL = "https://www.cbe.org.eg/api/exchange_rate/USD"


async def fetch_cbe_rate() -> float | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(CBE_API_URL)
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("rate") or data.get("USD") or data.get("price")
            if isinstance(rate, (int, float)) and rate > 0:
                return float(rate)
            if "rates" in data and isinstance(data["rates"], list):
                for r in data["rates"]:
                    if r.get("currency") == "USD":
                        return float(r.get("buy", r.get("rate", 0)))
            return None
        except Exception as e:
            print(f"[CBE Sync] Fetch error: {e}")
            return None


async def sync_cbe_rate():
    rate = await fetch_cbe_rate()
    if not rate:
        print("[CBE Sync] No rate fetched; skipping update")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Currency).where(Currency.code == "USD"))
        usd = result.scalar_one_or_none()

        if not usd:
            print("[CBE Sync] USD currency not found; seed currencies first")
            return

        await db.execute(
            CurrencyRate.__table__.update()
            .where(CurrencyRate.currency_id == usd.id)
            .where(CurrencyRate.is_active)
            .values(is_active=False)
        )

        new_rate = CurrencyRate(
            currency_id=usd.id,
            rate_to_egp=rate,
            is_active=True,
            effective_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(new_rate)
        await db.commit()
        print(f"[CBE Sync] USD/EGP = {rate} @ {datetime.utcnow().isoformat()}")


def start_cbe_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_cbe_rate,
        CronTrigger(hour=6, minute=0, timezone="Africa/Cairo"),
        id="cbe_daily_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    print("[CBE Sync] Scheduler started â€” daily at 06:00 Cairo")
    return scheduler


async def trigger_manual_sync():
    await sync_cbe_rate()
