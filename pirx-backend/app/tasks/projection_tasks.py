from app.tasks import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.projection_tasks.recompute_projection")
def recompute_projection(user_id: str, event: str = "5000") -> dict:
    """Recompute projection for a user after feature update."""
    try:
        from app.services.projection_service import ProjectionService
        from app.services.supabase_client import SupabaseService

        svc = ProjectionService()
        db = SupabaseService()
        activities_raw = db.get_recent_activities(user_id, days=90)

        if not activities_raw:
            return {"status": "no_data", "user_id": user_id, "event": event}

        from app.services.feature_service import FeatureService
        from app.services.cleaning_service import CleaningService
        from app.models.activities import NormalizedActivity

        activities = [NormalizedActivity(**a) for a in activities_raw]
        avg_pace = CleaningService.compute_runner_avg_pace(activities)
        cleaned = CleaningService.clean_batch(activities, avg_pace)

        if not cleaned:
            return {"status": "no_valid_activities", "user_id": user_id}

        features = FeatureService.compute_all_features(cleaned)
        state = svc.recompute(user_id, event, features)

        return {
            "status": "updated",
            "user_id": user_id,
            "event": event,
            "projected_time": state.projected_time_seconds if state else None,
        }
    except Exception as e:
        logger.exception("recompute_projection failed")
        return {"status": "error", "user_id": user_id, "error": str(e)}


@celery_app.task(name="app.tasks.projection_tasks.recompute_all_events")
def recompute_all_events(user_id: str) -> dict:
    """Recompute projections for all events after race sync or major change."""
    events = ["1500", "3000", "5000", "10000"]
    results = {}
    for event in events:
        results[event] = recompute_projection(user_id, event)
    return {"user_id": user_id, "events": results}


@celery_app.task(name="app.tasks.projection_tasks.structural_decay_check")
def structural_decay_check() -> dict:
    """Daily cron: apply decay for inactive users."""
    try:
        from app.services.supabase_client import SupabaseService

        db = SupabaseService()
        # TODO: Query all users with last_activity_at > 10 days ago
        # For each: widen supported range, decrease readiness
        return {"status": "completed", "users_checked": 0, "users_decayed": 0}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.projection_tasks.weekly_summary")
def weekly_summary() -> dict:
    """Weekly cron: generate summaries for active users."""
    try:
        from app.services.supabase_client import SupabaseService
        from app.services.notification_service import NotificationService

        db = SupabaseService()
        notif_svc = NotificationService()
        # TODO: Load active users, compute weekly changes, send notifications
        return {"status": "completed", "summaries_sent": 0}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.projection_tasks.bias_correction")
def bias_correction() -> dict:
    """Monthly cron: iterative bias correction for users with race results."""
    try:
        import numpy as np  # noqa: F401
        from app.services.supabase_client import SupabaseService

        db = SupabaseService()
        epsilon = 0.01  # noqa: F841
        # TODO: Load users with race results, run correction loop
        return {"status": "completed", "users_corrected": 0}
    except Exception as e:
        return {"status": "error", "error": str(e)}
