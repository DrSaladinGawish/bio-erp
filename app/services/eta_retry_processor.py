import asyncio
import json
from datetime import datetime
from datetime import timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.eta_queue import ETASubmissionQueue
from app.services.eta_production import ETAProductionClient, ETAProductionError
from app.services.email_service import EmailService


class ETARetryProcessor:
    @staticmethod
    async def process_queue(limit: int = 10):
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ETASubmissionQueue)
                .where(ETASubmissionQueue.status.in_(["retrying", "pending"]))
                .where(ETASubmissionQueue.retry_count < ETASubmissionQueue.max_retries)
                .order_by(ETASubmissionQueue.updated_at)
                .limit(limit)
            )
            jobs = result.scalars().all()

            for job in jobs:
                try:
                    doc = json.loads(job.document_json)
                    result = await ETAProductionClient.submit_batch([doc])

                    accepted = result.get("accepted", [])
                    rejected = result.get("rejected", [])

                    if accepted:
                        job.status = "accepted"
                        job.eta_uuid = accepted[0].get("uuid")
                        job.eta_long_id = accepted[0].get("longId")
                        job.resolved_at = datetime.utcnow()
                        await EmailService.eta_alert(
                            recipient="admin@bioerp.local",
                            invoice_uuid=job.eta_uuid,
                            status="ACCEPTED",
                        )
                    elif rejected:
                        rej = rejected[0]
                        job.status = "rejected" if not rej["retryable"] else "retrying"
                        job.rejection_code = rej["code"]
                        job.rejection_reason = rej["reason"]
                        job.retry_count += 1
                        if job.retry_count >= job.max_retries:
                            job.status = "failed"
                            await EmailService.eta_alert(
                                recipient="admin@bioerp.local",
                                invoice_uuid=job.internal_id,
                                status="FAILED",
                                errors=[f"{rej['code']}: {rej['reason']}"],
                            )

                    job.submitted_at = datetime.utcnow()
                    job.last_error = None

                except ETAProductionError as e:
                    job.retry_count += 1
                    job.last_error = f"[{e.code}] {e.message}"
                    if job.retry_count >= job.max_retries:
                        job.status = "failed"
                    else:
                        job.status = "retrying"
                except Exception as e:
                    job.retry_count += 1
                    job.last_error = str(e)
                    if job.retry_count >= job.max_retries:
                        job.status = "failed"

                job.updated_at = datetime.utcnow()
                await db.commit()

    @staticmethod
    async def start_retry_loop(interval_seconds: int = 300):
        while True:
            try:
                await ETARetryProcessor.process_queue(limit=5)
            except Exception as e:
                print(f"[ETA Retry] Loop error: {e}")
            await asyncio.sleep(interval_seconds)
