import logging

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.projection import (
    ProjectionResponse,
    ProjectionHistoryResponse,
    ProjectionHistoryPoint,
    TrajectoryResponse,
    TrajectoryScenario,
)
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_time(seconds: float) -> str:
    """Format seconds to MM:SS or H:MM:SS."""
    if seconds >= 3600:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{mins:02d}:{secs:02d}"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


def _mock_projection(event: str) -> ProjectionResponse:
    return ProjectionResponse(
        event=event,
        projected_time_seconds=0,
        projected_time_display="—",
        supported_range_low=0,
        supported_range_high=0,
        supported_range_display="—",
        baseline_time_seconds=0,
        total_improvement_seconds=0,
        volatility=0,
        last_updated=None,
        model_source=None,
        model_confidence=None,
        fallback_reason=None,
    )


def _mock_projection_history(event: str, days: int) -> ProjectionHistoryResponse:
    return ProjectionHistoryResponse(event=event, days=days, history=[])


@router.get("", response_model=ProjectionResponse)
async def get_projection(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get current projection for a specific event."""
    try:
        db = SupabaseService()
        projection = db.get_latest_projection(user["user_id"], event)
    except Exception:
        logger.exception("Failed to query projection_state")
        projection = None

    if projection:
        midpoint = projection["midpoint_seconds"]
        range_low = projection.get("range_low_seconds", midpoint * 0.97)
        range_high = projection.get("range_high_seconds", midpoint * 1.03)
        baseline = projection.get("baseline_seconds", midpoint + 78)
        volatility = projection.get("volatility", 0.0)
        improvement = baseline - midpoint

        return ProjectionResponse(
            event=event,
            projected_time_seconds=midpoint,
            projected_time_display=_format_time(midpoint),
            supported_range_low=range_low,
            supported_range_high=range_high,
            supported_range_display=f"{_format_time(range_low)} – {_format_time(range_high)}",
            baseline_time_seconds=baseline,
            total_improvement_seconds=improvement,
            volatility=volatility,
            last_updated=projection.get("computed_at"),
            model_source=projection.get("model_type"),
            model_confidence=projection.get("confidence_score"),
            fallback_reason=projection.get("fallback_reason"),
        )

    return _mock_projection(event)


@router.get("/history", response_model=ProjectionHistoryResponse)
async def get_projection_history(
    event: str = Query(default="5000"),
    days: int = Query(default=90, ge=7, le=365),
    user: dict = Depends(get_current_user),
):
    """Get projection history time-series."""
    try:
        db = SupabaseService()
        rows = db.get_projection_history(user["user_id"], event, days=days)
    except Exception:
        logger.exception("Failed to query projection history")
        rows = []

    if rows:
        history = [
            ProjectionHistoryPoint(
                date=row["computed_at"][:10],
                projected_time_seconds=row["midpoint_seconds"],
                event=event,
                range_low=row.get("range_low_seconds"),
                range_high=row.get("range_high_seconds"),
            )
            for row in reversed(rows)
        ]
        return ProjectionHistoryResponse(event=event, days=days, history=history)

    return _mock_projection_history(event, days)


EVENT_DISPLAY_NAMES = {
    "1500": "1500m", "3000": "3K", "5000": "5K", "10000": "10K",
    "21097": "Half Marathon", "42195": "Marathon",
}

DRIVER_KEYS = [
    "aerobic_base",
    "threshold_density",
    "speed_exposure",
    "running_economy",
    "load_consistency",
]

DRIVER_DISPLAY_NAMES = {
    "aerobic_base": "Aerobic Base",
    "threshold_density": "Threshold Density",
    "speed_exposure": "Speed Exposure",
    "running_economy": "Running Economy",
    "load_consistency": "Load Consistency",
}

def _load_user_features(user_id: str) -> dict | None:
    """Load computed features for a user. Returns None when no data exists."""
    try:
        from app.models.activities import NormalizedActivity
        from app.services.feature_service import FeatureService

        db = SupabaseService()
        activities_raw = db.get_recent_activities(user_id, days=180)
        if activities_raw:
            activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]
            return FeatureService.compute_all_features(activities, user_id=user_id)
    except Exception:
        logger.exception("Failed to load user features")
    return None


def _build_projection_narrative(driver_explanations: list[dict]) -> str:
    """Combine per-driver narratives into a 2-3 sentence top-level narrative."""
    sorted_drivers = sorted(driver_explanations, key=lambda d: abs(d["contribution_seconds"]), reverse=True)
    top = sorted_drivers[:2]

    parts = []
    for d in top:
        sign = "-" if d["contribution_seconds"] < 0 else "+"
        parts.append(f"{d['display_name']} (contributing {sign}{abs(d['contribution_seconds'])}s)")

    sentence = "Your projection is primarily driven by " + " and ".join(parts) + "."

    if top:
        best = top[0]
        sentence += f" {best['narrative']}"

    return sentence


@router.get("/explain")
async def explain_projection(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get SHAP-based explanation for the full projection across all drivers."""
    from app.ml.shap_explainer import SHAPExplainer

    features = _load_user_features(user["user_id"])
    if features is None:
        return {
            "event": event,
            "narrative": "Sync a wearable to see how your projection is calculated.",
            "drivers": [],
            "confidence": "low",
        }

    try:
        db = SupabaseService()
        driver_rows = db.get_latest_drivers(user["user_id"])
    except Exception:
        logger.exception("Failed to query driver_state for explain")
        driver_rows = []

    driver_contributions: dict[str, float] = {}
    if driver_rows:
        row = driver_rows[0]
        for key in DRIVER_KEYS:
            driver_contributions[key] = row.get(f"{key}_seconds", 0.0)

    driver_explanations = []
    confidences = []

    for key in DRIVER_KEYS:
        explanation = SHAPExplainer.explain_driver(key, features)
        contrib = driver_contributions.get(key, 0.0)
        driver_explanations.append({
            "driver_name": key,
            "display_name": DRIVER_DISPLAY_NAMES[key],
            "contribution_seconds": contrib,
            "overall_direction": explanation.overall_direction,
            "narrative": explanation.narrative,
            "top_factors": explanation.top_features,
        })
        confidences.append(explanation.confidence)

    narrative = _build_projection_narrative(driver_explanations)

    if "high" in confidences:
        overall_confidence = "high"
    elif confidences.count("medium") >= 3:
        overall_confidence = "medium"
    else:
        overall_confidence = "low"

    return {
        "event": event,
        "narrative": narrative,
        "drivers": driver_explanations,
        "confidence": overall_confidence,
    }


@router.get("/all")
async def get_all_projections(user: dict = Depends(get_current_user)):
    """Get projections across all supported events."""
    events = ["1500", "3000", "5000", "10000", "21097", "42195"]
    projections = []
    db = SupabaseService()
    for event in events:
        try:
            projection = db.get_latest_projection(user["user_id"], event)
            if projection:
                midpoint = projection["midpoint_seconds"]
                projections.append({
                    "event": event,
                    "display_name": EVENT_DISPLAY_NAMES.get(event, event),
                    "projected_time_seconds": midpoint,
                    "projected_time_display": _format_time(midpoint),
                    "supported_range_low": projection.get("range_low_seconds", midpoint * 0.97),
                    "supported_range_high": projection.get("range_high_seconds", midpoint * 1.03),
                    "total_improvement_seconds": projection.get("baseline_seconds", midpoint + 78) - midpoint,
                    "twenty_one_day_change": projection.get("twenty_one_day_change", 0),
                    "model_source": projection.get("model_type"),
                    "model_confidence": projection.get("confidence_score"),
                    "fallback_reason": projection.get("fallback_reason"),
                })
        except Exception:
            pass
    return {"projections": projections}


@router.get("/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get 2-week trajectory scenarios."""
    from app.ml.trajectory_engine import TrajectoryEngine

    try:
        db = SupabaseService()
        projection = db.get_latest_projection(user["user_id"], event)
    except Exception:
        logger.exception("Failed to query projection for trajectory")
        projection = None

    if not projection:
        return TrajectoryResponse(event=event, scenarios=[])

    current = projection["midpoint_seconds"]
    baseline_time = projection.get("baseline_seconds", current)

    try:
        engine = TrajectoryEngine()
        activities_raw = db.get_recent_activities(user["user_id"], days=180)
        if not activities_raw:
            return TrajectoryResponse(event=event, scenarios=[])

        from app.models.activities import NormalizedActivity
        from app.services.feature_service import FeatureService
        activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]
        real_features = FeatureService.compute_all_features(activities)

        scenarios = engine.compute_trajectories(
            user_id=user["user_id"],
            event=event,
            baseline_time_s=baseline_time,
            current_features=real_features,
        )
        return TrajectoryResponse(
            event=event,
            scenarios=[
                TrajectoryScenario(
                    label=s.label,
                    projected_time_seconds=s.projected_time_seconds,
                    projected_time_display=_format_time(s.projected_time_seconds),
                    description=s.description,
                    confidence=s.confidence,
                    delta_seconds=s.delta_from_current,
                )
                for s in scenarios
            ],
        )
    except Exception:
        logger.exception("TrajectoryEngine failed")
        return TrajectoryResponse(event=event, scenarios=[])
