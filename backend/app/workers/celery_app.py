"""Celery configuration for background tasks."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "neuroseek",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=[
        "app.workers.tasks.training",
        "app.workers.tasks.inference",
        "app.workers.tasks.evaluation",
    ],
)

# Configuration
celery_app.conf.update(
    task_serializer=settings.celery.task_serializer,
    result_serializer=settings.celery.result_serializer,
    accept_content=settings.celery.accept_content,
    timezone=settings.celery.timezone,
    enable_utc=settings.celery.enable_utc,
    task_routes=settings.celery.task_routes,
    worker_prefetch_multiplier=settings.celery.worker_prefetch_multiplier,
    task_acks_late=settings.celery.task_acks_late,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,
    result_expires=86400,  # 24 hours
    worker_max_tasks_per_child=10,
    beat_schedule={
        "check-training-trigger": {
            "task": "app.workers.tasks.training.check_training_trigger",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-runs": {
            "task": "app.workers.tasks.training.cleanup_old_runs",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")