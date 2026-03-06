from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.ml.readiness_engine import ReadinessEngine

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
    """Get Event Readiness score.

    Readiness is independent from projection — it indicates
    race-day preparedness, not structural fitness.

    TODO: Load real features and physiological data from Supabase.
    """
    # TODO: Load real user features
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
