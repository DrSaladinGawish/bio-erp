"""Day 2 — Email Service tests (6 tests)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_service import EmailService, EmailScheduler


class TestEmailService:
    async def test_email_service_initializes(self):
        assert EmailService.send is not None
        assert EmailService.eta_alert is not None

    @patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
    @patch("app.services.email_service.SMTP_USER", "test@test.com")
    @patch("app.services.email_service.SMTP_PASS", "secret")
    async def test_send_invoice_reminder_format(self, mock_send):
        result = await EmailService.send_invoice_reminder(
            "client@test.com", "INV-001", 5000.00, "2025-06-30"
        )
        assert mock_send.called
        assert result is True

    @patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
    @patch("app.services.email_service.SMTP_USER", "test@test.com")
    @patch("app.services.email_service.SMTP_PASS", "secret")
    async def test_send_daily_summary_format(self, mock_send):
        summary = {
            "date": "2025-06-06",
            "new_pnrs": 5,
            "sales_count": 3,
            "sales_total": 15000.00,
            "purchase_count": 2,
            "bank_count": 10,
        }
        result = await EmailService.send_daily_summary(
            "admin@incentivehouse.com", summary
        )
        assert mock_send.called
        assert result is True

    @patch("app.services.email_service.SMTP_USER", None)
    @patch("app.services.email_service.SMTP_PASS", None)
    async def test_email_service_without_smtp_logs(self):
        result = await EmailService.send_invoice_reminder(
            "client@test.com", "INV-001", 5000.00, "2025-06-30"
        )
        assert result is False

    async def test_email_api_endpoint(self, client):
        resp = await client.post(
            "/api/v1/intelligence/email/trigger",
            json={"to": "test@example.com", "subject": "Test", "body": "Hello"},
        )
        assert resp.status_code in (200, 201)


class TestEmailScheduler:
    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_email_scheduler_setup(self, mock_sched):
        instance = MagicMock()
        mock_sched.return_value = instance
        scheduler = EmailScheduler()
        assert instance.add_job.called
        assert instance.start.called
        scheduler.shutdown()
