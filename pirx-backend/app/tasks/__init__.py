from celery import Celery

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
    }
)
