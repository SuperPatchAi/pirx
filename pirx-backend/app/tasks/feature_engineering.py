from app.tasks import celery_app

STRUCTURAL_SHIFT_THRESHOLD_SECONDS = 2.0


@celery_app.task(name="app.tasks.feature_engineering.compute_features")
def compute_features(user_id: str, activity_data: dict = None) -> dict:
    """Compute rolling-window features after new activity sync.

    Pipeline:
    1. Load recent activities for user (TODO: from Supabase)
    2. Clean activities through CleaningService
    3. Compute 27 features via FeatureService
    4. Cache features in Redis (TODO)
    5. Check structural shift threshold
    6. If shift >= 2 seconds, queue recompute_projection

    For now, this operates on passed-in data since DB isn't connected yet.
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
            NormalizedActivity(**a) if isinstance(a, dict) else a for a in raw_list
        ]
    else:
        # TODO: Load from Supabase
        # activities = load_user_activities(user_id, days=90)
        activities = []

    if not activities:
        result["status"] = "no_activities"
        return result

    runner_avg_pace = CleaningService.compute_runner_avg_pace(activities)

    cleaned = CleaningService.clean_batch(activities, runner_avg_pace)
    result["activities_cleaned"] = len(cleaned)

    if not cleaned:
        result["status"] = "all_filtered"
        return result

    features = FeatureService.compute_all_features(cleaned)
    result["features_computed"] = sum(1 for v in features.values() if v is not None)

    # TODO: Cache in Redis
    # cache_features(user_id, features)

    # TODO: Check structural shift
    # current_projection = get_current_projection(user_id)
    # if shift >= STRUCTURAL_SHIFT_THRESHOLD_SECONDS:
    #     recompute_projection.delay(user_id)
    #     result["projection_recompute_triggered"] = True

    return result
