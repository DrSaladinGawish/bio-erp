import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.eta_queue import ETASubmissionQueue
from app.services.email_service import EmailService
from app.services.health import HealthCheck


class AlertService:
    THRESHOLDS = {
        "eta_failed_queue": 10,
        "db_latency_ms": 1000,
        "eta_latency_ms": 10000,
        "disk_percent": 90,
        "backup_stale_hours": 26,
    }

    @staticmethod
    async def check_eta_queue() -> list[dict]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ETASubmissionQueue.status, func.count()).group_by(
                    ETASubmissionQueue.status
                )
            )
            counts = {status: count for status, count in result.all()}

            alerts = []
            failed = counts.get("failed", 0)
            if failed >= AlertService.THRESHOLDS["eta_failed_queue"]:
                alerts.append(
                    {
                        "severity": "critical",
                        "component": "eta_queue",
                        "message": f"{failed} failed ETA submissions require manual review",
                        "count": failed,
                    }
                )

            retrying = counts.get("retrying", 0)
            if retrying > 0:
                alerts.append(
                    {
                        "severity": "warning",
                        "component": "eta_queue",
                        "message": f"{retrying} ETA submissions in retry loop",
                        "count": retrying,
                    }
                )

            return alerts

    @staticmethod
    async def check_health() -> list[dict]:
        health = await HealthCheck.full_check()
        alerts = []

        db = health["checks"]["database"]
        if db["status"] == "unhealthy":
            alerts.append(
                {
                    "severity": "critical",
                    "component": "database",
                    "message": f"Database unhealthy: {db.get('error', 'unknown')}",
                }
            )
        elif db.get("latency_ms", 0) > AlertService.THRESHOLDS["db_latency_ms"]:
            alerts.append(
                {
                    "severity": "warning",
                    "component": "database",
                    "message": f"DB latency {db['latency_ms']}ms exceeds threshold",
                }
            )

        eta = health["checks"]["eta_api"]
        if eta["status"] == "unhealthy":
            alerts.append(
                {
                    "severity": "critical",
                    "component": "eta_api",
                    "message": f"ETA API unreachable: {eta.get('error', 'unknown')}",
                }
            )

        disk = health["checks"]["disk"]
        if disk.get("status") == "critical":
            alerts.append(
                {
                    "severity": "critical",
                    "component": "disk",
                    "message": f"Disk usage critical: {disk['percent_used']}%",
                }
            )

        return alerts

    @staticmethod
    async def run_all_checks() -> list[dict]:
        queue_alerts, health_alerts = await asyncio.gather(
            AlertService.check_eta_queue(),
            AlertService.check_health(),
        )
        return queue_alerts + health_alerts

    @staticmethod
    async def notify(alerts: list[dict]):
        if not alerts:
            return

        critical = [a for a in alerts if a["severity"] == "critical"]
        warnings = [a for a in alerts if a["severity"] == "warning"]

        if critical:
            body = "<h2>BIO-ERP Critical Alerts</h2>" + "".join(
                [
                    f"<p><strong>{a['component']}:</strong> {a['message']}</p>"
                    for a in critical
                ]
            )
            await EmailService.send(
                to=["admin@bioerp.local"],
                subject=f"CRITICAL: {len(critical)} BIO-ERP alerts",
                body_html=body,
            )

        if warnings:
            body = "<h2>BIO-ERP Warnings</h2>" + "".join(
                [
                    f"<p><strong>{a['component']}:</strong> {a['message']}</p>"
                    for a in warnings
                ]
            )
            await EmailService.send(
                to=["admin@bioerp.local"],
                subject=f"Warning: {len(warnings)} BIO-ERP alerts",
                body_html=body,
            )

    @staticmethod
    async def start_monitoring_loop(interval_seconds: int = 300):
        while True:
            try:
                alerts = await AlertService.run_all_checks()
                if alerts:
                    await AlertService.notify(alerts)
            except Exception as e:
                print(f"[AlertService] Monitoring error: {e}")
            await asyncio.sleep(interval_seconds)
