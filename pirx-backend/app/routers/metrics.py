from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

router = APIRouter()


@router.get("/weekly")
async def get_weekly_metrics(user: dict = Depends(get_current_user)):
    """Get weekly training metrics: sessions, distance, ACWR."""
    db = SupabaseService()
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        activities = db.get_activities_since(user["user_id"], seven_days_ago)
    except Exception:
        activities = []

    sessions = len(activities)
    distance_km = round(sum(a.get("distance_meters", 0) for a in activities) / 1000, 1) if activities else 0

    acwr = None
    try:
        from app.models.activities import NormalizedActivity
        from app.services.feature_service import FeatureService
        all_activities_raw = db.get_recent_activities(user["user_id"], days=180)
        if all_activities_raw:
            all_activities = [NormalizedActivity.from_db_dict(a) for a in all_activities_raw]
            features = FeatureService.compute_all_features(all_activities)
            acwr = features.get("acwr_4w")
    except Exception:
        pass

    return {
        "sessions_per_week": sessions,
        "distance_km_per_week": distance_km,
        "acwr": acwr,
    }
