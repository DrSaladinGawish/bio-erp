import asyncio
from celery import shared_task
from app.services.alert_service import AlertService


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def monitor_alerts(self):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        alerts = loop.run_until_complete(AlertService.run_all_checks())
        if alerts:
            loop.run_until_complete(AlertService.notify(alerts))
        loop.close()
        return f"Alert monitoring cycle complete: {len(alerts)} alerts"
    except Exception as exc:
        raise self.retry(exc=exc)
