from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime, timezone
import logging

from app.dependencies import get_current_user
from app.ml.readiness_engine import ReadinessEngine
from app.ml.injury_risk_model import InjuryRiskModel
from app.models.activities import NormalizedActivity
from app.services.supabase_client import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)


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
    activities_raw = db.get_recent_activities(user["user_id"], days=180)

    if activities_raw:
        activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]

        for a in activities:
            if a.timestamp and a.timestamp.tzinfo:
                a.timestamp = a.timestamp.replace(tzinfo=None)

        from app.services.feature_service import FeatureService
        features = FeatureService.compute_all_features(activities, user_id=user["user_id"])

        now_utc = datetime.now(timezone.utc)
        now_naive = now_utc.replace(tzinfo=None)
        days_since_last = None
        days_since_threshold = None
        days_since_long_run = None
        days_since_race = None

        for a in activities:
            ts = a.timestamp
            if not ts:
                continue
            diff = (now_naive - ts).days
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
                days_since_long_run = (now_naive - last_long.timestamp).days
            else:
                days_since_long_run = 30

        physiology = db.get_recent_physiology(user["user_id"], limit=3)
        latest_physiology = physiology[0] if physiology else {}
        sleep_score = (latest_physiology.get("sleep_score") or 75) if latest_physiology else 75

        result = ReadinessEngine.compute_readiness(
            features=features,
            days_since_last_activity=days_since_last or 1,
            days_since_last_threshold=days_since_threshold,
            days_since_last_long_run=days_since_long_run,
            days_since_last_race=days_since_race,
            sleep_score=sleep_score,
        )
    else:
        return ReadinessResponse(
            score=0,
            label="Insufficient Data",
            components={},
            factors=[{"name": "No activities synced", "impact": "neutral", "detail": "Sync a wearable to see your readiness score."}],
        )

    injury_risk_prob = InjuryRiskModel.predict_probability(features, sleep_score)
    risk_band = InjuryRiskModel.get_risk_band(injury_risk_prob)
    latest_custom_fields = latest_physiology.get("custom_fields") if activities_raw else {}
    if not isinstance(latest_custom_fields, dict):
        latest_custom_fields = {}
    latest_weight = latest_custom_fields.get("weight_kg")
    latest_body_fat = latest_custom_fields.get("body_fat_percentage")
    latest_bmi = latest_custom_fields.get("bmi")
    body_factor_detail_parts = []
    if latest_weight is not None:
        body_factor_detail_parts.append(f"weight {float(latest_weight):.1f} kg")
    if latest_body_fat is not None:
        body_factor_detail_parts.append(f"body fat {float(latest_body_fat):.1f}%")
    if latest_bmi is not None:
        body_factor_detail_parts.append(f"BMI {float(latest_bmi):.1f}")
    body_factor_detail = ", ".join(body_factor_detail_parts) if body_factor_detail_parts else None
    try:
        db.insert_injury_risk_assessment(
            {
                "user_id": user["user_id"],
                "event": event,
                "model_id": None,
                "risk_probability": injury_risk_prob,
                "risk_band": risk_band,
                "feature_contributions": {
                    "acwr_4w": features.get("acwr_4w"),
                    "weekly_load_stddev": features.get("weekly_load_stddev"),
                    "session_density_stability": features.get("session_density_stability"),
                    "sleep_score": sleep_score,
                    "weight_kg": latest_weight,
                    "body_fat_percentage": latest_body_fat,
                    "bmi": latest_bmi,
                },
            }
        )
    except Exception:
        logger.warning("Failed to persist injury risk assessment", exc_info=True)

    return ReadinessResponse(
        score=result.score,
        label=result.label,
        components={
            **result.components,
            "injury_risk": round((1.0 - injury_risk_prob) * 100.0, 1),
        },
        factors=[
            *result.factors,
            *(
                [
                    {
                        "factor": "Sleep recovery signal",
                        "impact": (
                            "positive"
                            if sleep_score >= 80
                            else "negative"
                            if sleep_score <= 60
                            else "neutral"
                        ),
                        "detail": f"Latest wearable sleep score {sleep_score:.0f}/100.",
                    }
                ]
                if sleep_score is not None
                else []
            ),
            *(
                [
                    {
                        "factor": "Body composition signal",
                        "impact": "neutral",
                        "detail": body_factor_detail,
                    }
                ]
                if body_factor_detail
                else []
            ),
            {
                "factor": "Injury risk model",
                "impact": (
                    "negative" if risk_band == "high" else "neutral" if risk_band == "moderate" else "positive"
                ),
                "detail": f"Estimated risk {injury_risk_prob * 100:.1f}% ({risk_band})",
            },
        ],
    )
