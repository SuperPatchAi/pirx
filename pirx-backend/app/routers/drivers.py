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
    drivers = [
        DriverSummary(
            driver_name="aerobic_base",
            display_name="Aerobic Base",
            contribution_seconds=23.4,
            score=72,
            trend="improving",
            trend_emoji="↑",
        ),
        DriverSummary(
            driver_name="threshold_density",
            display_name="Threshold Density",
            contribution_seconds=19.5,
            score=65,
            trend="improving",
            trend_emoji="↑",
        ),
        DriverSummary(
            driver_name="speed_exposure",
            display_name="Speed Exposure",
            contribution_seconds=11.7,
            score=48,
            trend="stable",
            trend_emoji="→",
        ),
        DriverSummary(
            driver_name="running_economy",
            display_name="Running Economy",
            contribution_seconds=12.2,
            score=58,
            trend="stable",
            trend_emoji="→",
        ),
        DriverSummary(
            driver_name="load_consistency",
            display_name="Load Consistency",
            contribution_seconds=11.2,
            score=70,
            trend="improving",
            trend_emoji="↑",
        ),
    ]
    total = sum(d.contribution_seconds for d in drivers)
    return DriversResponse(event=event, drivers=drivers, total_improvement_seconds=total)


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
    from datetime import datetime, timedelta

    display_name = DRIVER_DISPLAY_NAMES.get(
        driver_name, driver_name.replace("_", " ").title()
    )
    description = DRIVER_DESCRIPTIONS.get(driver_name, "")
    history = []
    base_score = 55.0
    for i in range(min(days, 30)):
        date = datetime(2026, 3, 5) - timedelta(days=i)
        score = base_score + (i * 0.5)
        history.append(
            DriverDetailPoint(date=date.strftime("%Y-%m-%d"), score=round(min(score, 100), 1))
        )
    history.reverse()
    return DriverDetailResponse(
        driver_name=driver_name,
        display_name=display_name,
        description=description,
        score=72.0,
        trend="improving",
        contribution_seconds=23.4,
        history=history,
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

    # TODO: Load real features from Supabase
    mock_features = {
        "rolling_distance_7d": 35000, "rolling_distance_21d": 90000, "rolling_distance_42d": 170000,
        "z1_pct": 0.35, "z2_pct": 0.32, "z4_pct": 0.14, "z5_pct": 0.06,
        "threshold_density_min_week": 22, "speed_exposure_min_week": 8,
        "hr_drift_sustained": 0.035, "late_session_pace_decay": 0.025,
        "matched_hr_band_pace": 265,
        "weekly_load_stddev": 2500, "block_variance": 2800,
        "session_density_stability": 0.85, "acwr_4w": 1.1,
    }
    explanation = SHAPExplainer.explain_driver(driver_name, mock_features)
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
