from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ml_pipeline",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_soft_time_limit=settings.TRAINING_TIMEOUT_SECONDS,
    task_time_limit=settings.TRAINING_TIMEOUT_SECONDS + 30,
    beat_schedule={
        "check-model-performance": {
            "task": "ml.check_model_performance",
            "schedule": crontab(minute="0", hour="*/6"),
        },
        "daily-retraining-check": {
            "task": "ml.scheduled_retraining_check",
            "schedule": crontab(minute="0", hour="2"),
        },
        "weekly-garbage-collect": {
            "task": "ml.garbage_collect_models",
            "schedule": crontab(minute=0, hour=3, day_of_week=0),
        },
        "daily-cleanup-serving-logs": {
            "task": "ml.cleanup_serving_logs",
            "schedule": crontab(minute=30, hour=4),
        },
        "daily-cleanup-audit-logs": {
            "task": "ml.cleanup_audit_logs",
            "schedule": crontab(minute=45, hour=4),
        },
        "hourly-auto-retrain-check": {
            "task": "ml.run_auto_retrain_pipeline",
            "schedule": crontab(minute=0, hour="*/1"),
        },
    },
)

celery_app.autodiscover_tasks(["app.ml"])
