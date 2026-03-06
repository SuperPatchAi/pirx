from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery("pirx")
celery_app.config_from_object(
    {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "task_routes": {
            "app.tasks.projection_tasks.*": {"queue": "projection"},
            "app.tasks.feature_engineering.*": {"queue": "projection"},
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
        },
    }
)
