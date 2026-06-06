"""Day 2 — Email Scheduler tests (2 tests)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.email_service import EmailScheduler


class TestEmailScheduler:
    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_scheduler_creates_jobs(self, mock_sched):
        instance = MagicMock()
        mock_sched.return_value = instance
        sched = EmailScheduler()
        call_count = instance.add_job.call_count
        assert call_count >= 2
        instance.start.assert_called_once()
        sched.shutdown()

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_scheduler_daily_summary_job_exists(self, mock_sched):
        instance = MagicMock()
        mock_sched.return_value = instance
        EmailScheduler()
        call_args_list = [
            call[1].get("id", "") for call in instance.add_job.call_args_list
        ]
        assert any("daily_summary" in str(arg) for arg in call_args_list)
