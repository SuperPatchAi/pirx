from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime, timezone

from app.dependencies import get_current_user
from app.ml.readiness_engine import ReadinessEngine
from app.models.activities import NormalizedActivity
from app.services.supabase_client import SupabaseService

router = APIRouter()


class ReadinessResponse(BaseModel):
    score: float
    label: str
    components: dict[str, float]
    factors: list[dict]


@router.get("", response_model=ReadinessResponse)
async def get_readiness(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    activities_raw = db.get_recent_activities(user["user_id"], days=90)

    if activities_raw:
        activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]

        from app.services.feature_service import FeatureService
        features = FeatureService.compute_all_features(activities)

        now = datetime.now(timezone.utc)
        days_since_last = None
        days_since_threshold = None
        days_since_long_run = None
        days_since_race = None

        for a in activities:
            ts = a.timestamp
            if not ts:
                continue
            act_time = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            diff = (now - act_time).days
            if days_since_last is None or diff < days_since_last:
                days_since_last = diff
            if a.activity_type == "threshold" and (days_since_threshold is None or diff < days_since_threshold):
                days_since_threshold = diff
            if a.activity_type == "long_run" and (days_since_long_run is None or diff < days_since_long_run):
                days_since_long_run = diff
            if a.activity_type == "race" and (days_since_race is None or diff < days_since_race):
                days_since_race = diff

        if days_since_long_run is None:
            long_runs = [a for a in activities if (a.distance_meters or 0) >= 15000]
            if long_runs:
                last_long = max(long_runs, key=lambda x: x.timestamp)
                lt = last_long.timestamp
                lt = lt if lt.tzinfo else lt.replace(tzinfo=timezone.utc)
                days_since_long_run = (now - lt).days
            else:
                days_since_long_run = 30

        physiology = db.get_recent_physiology(user["user_id"], limit=1)
        sleep_score = physiology[0].get("sleep_score", 75) if physiology else 75

        result = ReadinessEngine.compute_readiness(
            features=features,
            days_since_last_activity=days_since_last or 1,
            days_since_last_threshold=days_since_threshold,
            days_since_last_long_run=days_since_long_run,
            days_since_last_race=days_since_race,
            sleep_score=sleep_score,
        )
    else:
        mock_features = {
            "acwr_4w": 1.1,
            "weekly_load_stddev": 4000,
            "session_density_stability": 0.8,
        }
        result = ReadinessEngine.compute_readiness(
            features=mock_features,
            days_since_last_activity=1,
            days_since_last_threshold=4,
            days_since_last_long_run=5,
            days_since_last_race=None,
            sleep_score=78,
        )

    return ReadinessResponse(
        score=result.score,
        label=result.label,
        components=result.components,
        factors=result.factors,
    )
