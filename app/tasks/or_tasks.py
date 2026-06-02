from app.celery_app import celery_app
from structlog import get_logger

logger = get_logger()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def run_or_engine(self, engine_name: str, params: dict) -> dict:
    try:
        logger.info("or_engine.run", engine=engine_name)
        from app.organs.or_organ.orchestrator import ORDispatcher
        result = ORDispatcher.dispatch(engine_name, params)
        logger.info("or_engine.completed", engine=engine_name)
        return {"status": "completed", "result": result}
    except Exception as exc:
        logger.error("or_engine.failed", engine=engine_name, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def run_batch_optimization(self, job_id: str, engine_list: list[dict]) -> dict:
    results = {}
    for item in engine_list:
        try:
            res = run_or_engine.delay(item["engine"], item["params"])
            results[item["engine"]] = res.id
        except Exception as exc:
            results[item["engine"]] = {"error": str(exc)}
    return {"job_id": job_id, "task_ids": results}
