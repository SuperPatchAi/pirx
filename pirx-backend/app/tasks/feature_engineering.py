from app.tasks import celery_app


@celery_app.task(name="app.tasks.feature_engineering.compute_features")
def compute_features(user_id: str) -> dict:
    """Compute rolling-window feature vectors after new activity sync.

    Steps:
    1. Load recent activities from Supabase
    2. Compute 7/14/21/42-day rolling metrics
    3. Calculate HR zone distributions and ACWR
    4. Store feature vectors in feature_snapshots table
    5. Trigger projection recompute
    """
    return {"status": "not_implemented", "user_id": user_id}
