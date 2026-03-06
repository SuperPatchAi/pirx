from app.tasks import celery_app


@celery_app.task(name="app.tasks.sync_tasks.process_activity")
def process_activity(user_id: str, raw_payload: dict) -> dict:
    """Process a single incoming activity from webhook.

    Steps:
    1. Normalize raw payload to NormalizedActivity schema
    2. Classify activity type (easy, threshold, interval, race, cross-training)
    3. Store normalized activity in Supabase
    4. Trigger feature engineering pipeline
    """
    return {"status": "not_implemented", "user_id": user_id}


@celery_app.task(name="app.tasks.sync_tasks.backfill_history")
def backfill_history(user_id: str, provider: str) -> dict:
    """Backfill 6-12 months of historical data on initial wearable connection."""
    return {"status": "not_implemented", "user_id": user_id, "provider": provider}
