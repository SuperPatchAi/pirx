import os

from app.tasks import celery_app


@celery_app.task(name="app.tasks.feature_engineering.compute_features")
def compute_features(user_id: str, activity_data: dict = None) -> dict:
    """Compute rolling-window features after new activity sync.

    Pipeline:
    1. Load recent activities for user from Supabase
    2. Clean activities through CleaningService
    3. Compute 25 features via FeatureService
    4. Cache features in Redis
    5. Queue recompute_all_events for all distance projections
    """
    from app.services.cleaning_service import CleaningService
    from app.services.feature_service import FeatureService
    from app.models.activities import NormalizedActivity

    result = {
        "user_id": user_id,
        "status": "completed",
        "features_computed": 0,
        "activities_cleaned": 0,
        "projection_recompute_triggered": False,
    }

    if activity_data:
        raw_list = [activity_data] if isinstance(activity_data, dict) else activity_data
        activities = [
            NormalizedActivity.from_db_dict(a) if isinstance(a, dict) else a for a in raw_list
        ]
    else:
        from app.services.supabase_client import SupabaseService
        db = SupabaseService()
        raw = db.get_recent_activities(user_id, days=90)
        activities = [NormalizedActivity.from_db_dict(a) for a in raw] if raw else []

    if not activities:
        result["status"] = "no_activities"
        return result

    for a in activities:
        if a.timestamp and a.timestamp.tzinfo:
            a.timestamp = a.timestamp.replace(tzinfo=None)

    runner_avg_pace = CleaningService.compute_runner_avg_pace(activities)

    cleaned = CleaningService.clean_batch(activities, runner_avg_pace)
    result["activities_cleaned"] = len(cleaned)

    if not cleaned:
        result["status"] = "all_filtered"
        return result

    features = FeatureService.compute_all_features(cleaned, user_id=user_id)
    result["features_computed"] = sum(1 for v in features.values() if v is not None)

    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        import json as _json
        r.setex(f"pirx:features:{user_id}", 3600, _json.dumps({k: v for k, v in features.items() if v is not None}))
    except Exception:
        pass

    from app.tasks.projection_tasks import recompute_all_events
    recompute_all_events.delay(user_id)
    result["projection_recompute_triggered"] = True

    return result
