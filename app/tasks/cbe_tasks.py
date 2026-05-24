import asyncio
from celery import shared_task
from app.database import AsyncSessionLocal
from app.services.cbe_sync import sync_cbe_rate
from app.services.currency_sync import CurrencySyncService


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_cbe_rates(self):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(sync_cbe_rate())
        loop.close()
        return "CBE sync complete"
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def sync_all_currencies(self):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _sync():
            async with AsyncSessionLocal() as session:
                service = CurrencySyncService(session)
                return await service.sync_from_cbe()

        result = loop.run_until_complete(_sync())
        loop.close()
        return f"Multi-currency sync: {len(result.get('updated', []))} updated"
    except Exception as exc:
        raise self.retry(exc=exc)
