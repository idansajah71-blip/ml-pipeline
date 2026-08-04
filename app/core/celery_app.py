from celery import Celery
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
)

celery_app.autodiscover_tasks(["app.ml"])
