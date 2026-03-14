import logging

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.projection import (
    DriversResponse,
    DriverSummary,
    DriverDetailResponse,
    DriverDetailPoint,
)
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter()

DRIVER_DISPLAY_NAMES = {
    "aerobic_base": "Aerobic Base",
    "threshold_density": "Threshold Density",
    "speed_exposure": "Speed Exposure",
    "running_economy": "Running Economy",
    "load_consistency": "Load Consistency",
}

DRIVER_DESCRIPTIONS = {
    "aerobic_base": "Volume and easy-effort training that builds your aerobic foundation",
    "threshold_density": "Time spent at threshold intensity (Zone 4) that raises your lactate ceiling",
    "speed_exposure": "High-intensity work (Zone 5) that develops top-end speed",
    "running_economy": "How efficiently you convert energy to pace at a given effort",
    "load_consistency": "Regularity of training load week-to-week",
}

DRIVER_KEYS = [
    "aerobic_base",
    "threshold_density",
    "speed_exposure",
    "running_economy",
    "load_consistency",
]

TREND_EMOJI = {"improving": "↑", "stable": "→", "declining": "↓"}


def _mock_drivers(event: str) -> DriversResponse:
    return DriversResponse(event=event, drivers=[], total_improvement_seconds=0)


def _row_to_driver_summaries(row: dict) -> list[DriverSummary]:
    """Convert a driver_state DB row into a list of DriverSummary models."""
    summaries = []
    for key in DRIVER_KEYS:
        contribution = row.get(f"{key}_seconds", 0.0)
        score = row.get(f"{key}_score", 50.0)
        trend = row.get(f"{key}_trend", "stable")
        summaries.append(
            DriverSummary(
                driver_name=key,
                display_name=DRIVER_DISPLAY_NAMES[key],
                contribution_seconds=contribution,
                score=score,
                trend=trend,
                trend_emoji=TREND_EMOJI.get(trend, "→"),
            )
        )
    return summaries


def _mock_driver_detail(driver_name: str, days: int) -> DriverDetailResponse:
    display_name = DRIVER_DISPLAY_NAMES.get(
        driver_name, driver_name.replace("_", " ").title()
    )
    description = DRIVER_DESCRIPTIONS.get(driver_name, "")
    return DriverDetailResponse(
        driver_name=driver_name,
        display_name=display_name,
        description=description,
        score=0,
        trend="stable",
        contribution_seconds=0,
        history=[],
    )


@router.get("", response_model=DriversResponse)
async def get_drivers(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get all 5 driver states with contributions."""
    try:
        db = SupabaseService()
        rows = db.get_latest_drivers(user["user_id"])
    except Exception:
        logger.exception("Failed to query driver_state")
        rows = []

    if rows:
        row = rows[0]
        drivers = _row_to_driver_summaries(row)
        total = sum(d.contribution_seconds for d in drivers)
        return DriversResponse(event=event, drivers=drivers, total_improvement_seconds=total)

    return _mock_drivers(event)


@router.get("/{driver_name}/explain")
async def explain_driver(
    driver_name: str,
    user: dict = Depends(get_current_user),
):
    """Get SHAP-based explanation for driver change."""
    from app.ml.shap_explainer import SHAPExplainer

    features = None
    try:
        from app.models.activities import NormalizedActivity

        db = SupabaseService()
        activities_raw = db.get_recent_activities(user["user_id"], days=180)
        if activities_raw:
            from app.services.feature_service import FeatureService
            activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]
            features = FeatureService.compute_all_features(activities, user_id=user["user_id"])
    except Exception:
        logger.exception("Failed to load features for explain_driver")

    if features is None:
        return {
            "driver_name": driver_name,
            "display_name": driver_name.replace("_", " ").title(),
            "overall_direction": "stable",
            "top_factors": [],
            "summary": "Sync a wearable to see how this driver affects your projection.",
            "confidence": "low",
        }

    gb_model = None
    try:
        from app.ml.gb_projection_model import GBProjectionModel
        active = db.get_active_model(user["user_id"], "5000")
        if active and active.get("model_family") == "gb":
            artifact = db.get_latest_model_artifact(active.get("model_id"))
            if artifact and isinstance(artifact.get("weight_bytes"), bytes):
                gb_model = GBProjectionModel()
                gb_model.deserialize(artifact["weight_bytes"])
    except Exception:
        pass

    explanation = SHAPExplainer.explain_driver(driver_name, features, gb_model=gb_model)
    return {
        "driver_name": explanation.driver_name,
        "display_name": explanation.display_name,
        "overall_direction": explanation.overall_direction,
        "top_factors": explanation.top_features,
        "summary": explanation.narrative,
        "confidence": explanation.confidence,
    }


@router.get("/{driver_name}", response_model=DriverDetailResponse)
async def get_driver_detail(
    driver_name: str,
    days: int = Query(default=42, ge=7, le=90),
    user: dict = Depends(get_current_user),
):
    """Get single driver trend data."""
    display_name = DRIVER_DISPLAY_NAMES.get(
        driver_name, driver_name.replace("_", " ").title()
    )
    description = DRIVER_DESCRIPTIONS.get(driver_name, "")

    try:
        db = SupabaseService()
        rows = db.get_driver_history(user["user_id"], days=days)
    except Exception:
        logger.exception("Failed to query driver history")
        rows = []

    if rows:
        latest = rows[0]
        score = latest.get(f"{driver_name}_score", 50.0)
        trend = latest.get(f"{driver_name}_trend", "stable")
        contribution = latest.get(f"{driver_name}_seconds", 0.0)

        history = [
            DriverDetailPoint(
                date=row["computed_at"][:10],
                score=row.get(f"{driver_name}_score", 50.0),
            )
            for row in reversed(rows)
        ]

        return DriverDetailResponse(
            driver_name=driver_name,
            display_name=display_name,
            description=description,
            score=score,
            trend=trend,
            contribution_seconds=contribution,
            history=history,
        )

    return _mock_driver_detail(driver_name, days)
