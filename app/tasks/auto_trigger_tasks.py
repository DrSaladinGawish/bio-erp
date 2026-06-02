from app.celery_app import celery_app
from structlog import get_logger

logger = get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_auto_trigger(self, trigger_type: str, payload: dict) -> dict:
    try:
        logger.info("auto_trigger.run", trigger_type=trigger_type)
        result = _dispatch_trigger(trigger_type, payload)
        logger.info("auto_trigger.completed", trigger_type=trigger_type)
        return {"status": "completed", "result": result}
    except Exception as exc:
        logger.error("auto_trigger.failed", trigger_type=trigger_type, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_cost_threshold_alert(self, job_id: str, cost_value: float) -> dict:
    logger.info("cost_threshold.alert", job_id=job_id, cost=cost_value)
    return {"status": "alerted", "job_id": job_id, "threshold_breached": cost_value}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_sustainability_check(self, scm_id: str) -> dict:
    logger.info("sustainability.check", scm_id=scm_id)
    return {"status": "checked", "scm_id": scm_id}


def _dispatch_trigger(trigger_type: str, payload: dict) -> dict:
    dispatcher = {
        "job_created": lambda p: {"action": "validate_job", "job_id": p.get("job_id")},
        "cost_threshold": lambda p: {"action": "notify_approver", "threshold": p.get("value")},
        "scm_update": lambda p: {"action": "recalc_strategic_cost", "scm_id": p.get("scm_id")},
        "sustainability_check": lambda p: {"action": "generate_sustainability_report", "context": p},
    }
    handler = dispatcher.get(trigger_type)
    if handler is None:
        raise ValueError(f"Unknown trigger type: {trigger_type}")
    return handler(payload)
