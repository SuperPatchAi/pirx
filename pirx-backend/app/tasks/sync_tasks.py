from app.tasks import celery_app


@celery_app.task(name="app.tasks.sync_tasks.process_activity")
def process_activity(user_id: str, raw_payload: dict, source: str = "unknown") -> dict:
    """Process a single incoming activity from webhook.

    Steps:
    1. Normalize based on source (Strava/Terra)
    2. Clean via CleaningService
    3. Store in activities table (TODO: Supabase)
    4. Trigger feature engineering
    """
    from app.services.cleaning_service import CleaningService
    from app.models.activities import NormalizedActivity

    result = {"user_id": user_id, "source": source, "status": "processed"}

    if source == "strava":
        from app.services.strava_service import StravaService
        activity = StravaService.normalize_activity(raw_payload)
    elif source in ("terra", "garmin", "fitbit", "suunto", "coros"):
        from app.services.terra_service import TerraService
        activity = TerraService.normalize_activity(raw_payload)
    else:
        try:
            activity = NormalizedActivity(**raw_payload)
        except Exception as e:
            result["status"] = "normalization_failed"
            result["error"] = str(e)
            return result

    cleaned = CleaningService.clean_activity(activity)
    if cleaned is None:
        result["status"] = "filtered_out"
        result["reason"] = "Failed cleaning pipeline"
        return result

    # TODO: Store in Supabase activities table
    # store_activity(user_id, cleaned)

    from app.tasks.feature_engineering import compute_features
    compute_features.delay(user_id)

    result["activity_type"] = cleaned.activity_type
    result["distance_meters"] = cleaned.distance_meters
    return result


@celery_app.task(name="app.tasks.sync_tasks.backfill_history")
def backfill_history(user_id: str, provider: str) -> dict:
    """Backfill historical data on initial wearable connection."""
    try:
        from app.services.supabase_client import SupabaseService
        from app.services.cleaning_service import CleaningService
        from app.services.feature_service import FeatureService
        from app.models.activities import NormalizedActivity

        db = SupabaseService()

        if provider == "strava":
            from app.services.strava_service import StravaService  # noqa: F401
            # TODO: Get user's Strava token, fetch 6-12 months of activities
            pass
        elif provider in ("terra", "garmin", "fitbit", "suunto", "coros"):
            from app.services.terra_service import TerraService  # noqa: F401
            # TODO: Fetch via Terra API
            pass

        # TODO: For each activity: normalize, clean, store
        # Then run full feature engineering
        # Then trigger recompute_all_events

        return {
            "status": "completed",
            "user_id": user_id,
            "provider": provider,
            "activities_imported": 0,
            "activities_valid": 0,
        }
    except Exception as e:
        return {"status": "error", "user_id": user_id, "error": str(e)}
