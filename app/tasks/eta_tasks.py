import asyncio
from celery import shared_task
from app.services.eta_retry_processor import ETARetryProcessor


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def process_eta_retry_queue(self, limit: int = 10):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ETARetryProcessor.process_queue(limit=limit))
        loop.close()
        return f"ETA retry queue processed (limit={limit})"
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def submit_eta_invoice(self, invoice_id: int):
    try:
        from app.services.eta_production import ETAProductionClient

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _submit():
            async with ETAProductionClient() as client:
                return await client.submit_invoice(invoice_id)

        result = loop.run_until_complete(_submit())
        loop.close()
        return f"ETA invoice {invoice_id} submitted: {result}"
    except Exception as exc:
        raise self.retry(exc=exc)
