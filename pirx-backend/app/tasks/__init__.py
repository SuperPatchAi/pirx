import logging
import os

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

broker = settings.celery_broker_url or settings.redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
backend = settings.celery_result_backend or settings.redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")

logger.info("Celery broker_url: %s", broker[:20] + "..." if len(broker) > 20 else broker)

celery_app = Celery("pirx")
celery_app.config_from_object(
    {
        "broker_url": broker,
        "result_backend": backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "task_routes": {
            "app.tasks.projection_tasks.*": {"queue": "projection"},
            "app.tasks.feature_engineering.*": {"queue": "projection"},
            "app.tasks.accuracy_tasks.*": {"queue": "projection"},
            "app.tasks.social_tasks.*": {"queue": "projection"},
            "app.tasks.sync_tasks.*": {"queue": "sync"},
        },
        "task_time_limit": 300,
        "task_soft_time_limit": 240,
        "beat_schedule": {
            "structural-decay-check-daily": {
                "task": "app.tasks.projection_tasks.structural_decay_check",
                "schedule": crontab(hour=3, minute=0),
            },
            "weekly-summary": {
                "task": "app.tasks.projection_tasks.weekly_summary",
                "schedule": crontab(hour=8, minute=0, day_of_week=1),
            },
            "monthly-bias-correction": {
                "task": "app.tasks.projection_tasks.bias_correction",
                "schedule": crontab(hour=4, minute=0, day_of_month=1),
            },
            "weekly-model-accuracy": {
                "task": "app.tasks.accuracy_tasks.compute_model_accuracy",
                "schedule": crontab(hour=5, minute=0, day_of_week=2),
            },
            "race-approaching-daily": {
                "task": "app.tasks.projection_tasks.check_race_approaching",
                "schedule": crontab(hour=9, minute=0),
            },
            "weekly-cohort-benchmarks": {
                "task": "app.tasks.social_tasks.compute_cohort_benchmarks",
                "schedule": crontab(hour=6, minute=0, day_of_week=3),
            },
        },
    }
)
