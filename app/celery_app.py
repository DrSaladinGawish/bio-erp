from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "bioerp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.cbe_tasks",
        "app.tasks.eta_tasks",
        "app.tasks.email_tasks",
        "app.tasks.alert_tasks",
        "app.tasks.scm_tasks",
        "app.tasks.backup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Cairo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=300,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_scheduler="celery.beat.PersistentScheduler",
    beat_max_loop_interval=300,
)

celery_app.conf.beat_schedule = {
    "cbe-daily-sync": {
        "task": "app.tasks.cbe_tasks.sync_cbe_rates",
        "schedule": 86400.0,
        "kwargs": {},
    },
    "eta-retry-processor": {
        "task": "app.tasks.eta_tasks.process_eta_retry_queue",
        "schedule": 300.0,
        "kwargs": {"limit": 10},
    },
    "alert-monitor": {
        "task": "app.tasks.alert_tasks.monitor_alerts",
        "schedule": 300.0,
        "kwargs": {},
    },
    "scm-nightly-reconciliation": {
        "task": "app.tasks.scm_tasks.sync_period_actuals",
        "schedule": 86400.0,
        "kwargs": {},
    },
    "scm-variance-check": {
        "task": "app.tasks.scm_tasks.sync_period_actuals",
        "schedule": 3600.0,
        "kwargs": {"period_id": None},
    },
    "db-nightly-backup": {
        "task": "app.tasks.backup_tasks.create_db_backup",
        "schedule": 86400.0,
        "kwargs": {},
    },
}
