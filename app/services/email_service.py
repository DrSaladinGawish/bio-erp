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

    @staticmethod
    async def send_invoice_reminder(
        to: str, invoice_no: str, amount: float, due_date: str
    ) -> bool:
        html = f"""
        <html><body style="font-family:Arial,sans-serif">
        <h2>Invoice Reminder</h2>
        <p>Invoice <strong>{invoice_no}</strong> of <strong>{amount:,.2f}</strong>
        is due on <strong>{due_date}</strong>.</p>
        <p>Please arrange payment before the due date.</p>
        <hr><p style="font-size:12px;color:#666">BIO-ERP Automated Reminder</p>
        </body></html>
        """
        return await EmailService.send(
            to=[to],
            subject=f"Invoice Reminder: {invoice_no}",
            body_html=html,
            body_text=f"Invoice {invoice_no} for {amount:,.2f} due on {due_date}.",
        )

    @staticmethod
    async def send_daily_summary(to: str, summary: dict) -> bool:
        date = summary.get("date", "unknown")
        new_pnrs = summary.get("new_pnrs", 0)
        sales_count = summary.get("sales_count", 0)
        sales_total = summary.get("sales_total", 0.0)
        purchase_count = summary.get("purchase_count", 0)
        bank_count = summary.get("bank_count", 0)
        html = f"""
        <html><body style="font-family:Arial,sans-serif">
        <h2>Daily Summary — {date}</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
        <tr><th>Metric</th><th>Count</th><th>Total</th></tr>
        <tr><td>New PNRs</td><td>{new_pnrs}</td><td>—</td></tr>
        <tr><td>Sales</td><td>{sales_count}</td><td>{sales_total:,.2f}</td></tr>
        <tr><td>Purchases</td><td>{purchase_count}</td><td>—</td></tr>
        <tr><td>Bank Transactions</td><td>{bank_count}</td><td>—</td></tr>
        </table>
        <hr><p style="font-size:12px;color:#666">BIO-ERP Daily Summary</p>
        </body></html>
        """
        return await EmailService.send(
            to=[to],
            subject=f"Daily Summary — {date}",
            body_html=html,
        )


class EmailScheduler:
    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()
        self.scheduler.start()

    def _setup_jobs(self):
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler.add_job(
            self._send_daily_report,
            CronTrigger(hour=8, minute=0, timezone="Africa/Cairo"),
            id="daily_summary_report",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        self.scheduler.add_job(
            self._send_weekly_report,
            CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="Africa/Cairo"),
            id="weekly_summary_report",
            replace_existing=True,
            misfire_grace_time=3600,
        )

    async def _send_daily_report(self):
        print("[EmailScheduler] Daily report job triggered")
        from app.services.dashboard_service import get_dashboard_data
        try:
            data = await get_dashboard_data()
            summary = {
                "date": "daily",
                "new_pnrs": data.get("new_pnrs", 0),
                "sales_count": data.get("sales_count", 0),
                "sales_total": data.get("revenue", 0.0),
                "purchase_count": data.get("purchase_count", 0),
                "bank_count": data.get("bank_count", 0),
            }
            await EmailService.send_daily_summary(
                FROM_EMAIL or "admin@bioerp.local", summary
            )
        except Exception as e:
            print(f"[EmailScheduler] Daily report error: {e}")

    async def _send_weekly_report(self):
        print("[EmailScheduler] Weekly report job triggered")

    def shutdown(self):
        self.scheduler.shutdown(wait=False)
