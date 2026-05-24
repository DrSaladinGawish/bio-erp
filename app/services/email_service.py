import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

settings = get_settings()

SMTP_HOST = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = getattr(settings, "SMTP_PORT", 587)
SMTP_USER = getattr(settings, "SMTP_USER", None)
SMTP_PASS = getattr(settings, "SMTP_PASS", None)
FROM_EMAIL = getattr(settings, "FROM_EMAIL", SMTP_USER)


class EmailService:
    @staticmethod
    async def send(
        to: list[str],
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
    ) -> bool:
        if not SMTP_USER or not SMTP_PASS:
            print("[Email] SMTP not configured; skipped")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL or "noreply@bioerp.local"
        msg["To"] = ", ".join(to)

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                start_tls=True,
                username=SMTP_USER,
                password=SMTP_PASS,
            )
            print(f"[Email] Sent: {subject} \u2192 {to}")
            return True
        except Exception as e:
            print(f"[Email] Failed: {e}")
            return False

    @staticmethod
    async def eta_alert(
        recipient: str, invoice_uuid: str, status: str, errors: list | None = None
    ):
        html = f"""
        <html dir="rtl"><body style="font-family:Arial,sans-serif">
        <h2>\u062a\u0646\u0628\u064a\u0647 ETA â€” Invoice Status</h2>
        <p><strong>UUID:</strong> {invoice_uuid}</p>
        <p><strong>Status:</strong> {status}</p>
        {f'<p style="color:red"><strong>Errors:</strong> {", ".join(errors)}</p>' if errors else ""}
        <hr><p style="font-size:12px;color:#666">BIO-ERP Automated Alert</p>
        </body></html>
        """
        await EmailService.send(
            to=[recipient],
            subject=f"ETA Alert: {invoice_uuid} [{status}]",
            body_html=html,
            body_text=f"Invoice {invoice_uuid} status: {status}",
        )

    @staticmethod
    async def approval_request(
        recipient: str, doc_type: str, doc_id: int, amount: float, currency: str = "EGP"
    ):
        html = f"""
        <html dir="rtl"><body style="font-family:Arial,sans-serif">
        <h2>\u0637\u0644\u0628 \u0645\u0648\u0627\u0641\u0642\u0629 â€” Approval Required</h2>
        <p>Document: <strong>{doc_type} #{doc_id}</strong></p>
        <p>Amount: <strong>{amount:,.2f} {currency}</strong></p>
        <p>Please review in the BIO-ERP dashboard.</p>
        </body></html>
        """
        await EmailService.send(
            to=[recipient],
            subject=f"Approval Required: {doc_type} #{doc_id}",
            body_html=html,
        )
