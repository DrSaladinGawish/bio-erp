import asyncio
from celery import shared_task
from app.services.email_service import EmailService


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(
    self,
    to: list,
    subject: str,
    body_html: str | None = None,
    body_text: str | None = None,
):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(
            EmailService.send(
                to=to, subject=subject, body_html=body_html, body_text=body_text
            )
        )
        loop.close()
        return f"Email sent to {to}: {success}"
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def send_eta_alert(
    self, recipient: str, invoice_uuid: str, status: str, errors: list | None = None
):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            EmailService.eta_alert(
                recipient=recipient,
                invoice_uuid=invoice_uuid,
                status=status,
                errors=errors,
            )
        )
        loop.close()
        return f"ETA alert sent to {recipient} for {invoice_uuid}"
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def send_approval_request(
    self,
    recipient: str,
    doc_type: str,
    doc_id: int,
    amount: float,
    currency: str = "EGP",
):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            EmailService.approval_request(
                recipient=recipient,
                doc_type=doc_type,
                doc_id=doc_id,
                amount=amount,
                currency=currency,
            )
        )
        loop.close()
        return f"Approval request sent to {recipient} for {doc_type}#{doc_id}"
    except Exception as exc:
        raise self.retry(exc=exc)
