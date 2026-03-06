from fastapi import APIRouter, Depends, Query
from app.dependencies import get_current_user
from app.models.projection import (
    DriversResponse,
    DriverSummary,
    DriverDetailResponse,
    DriverDetailPoint,
    DriverExplanation,
)

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


@router.get("", response_model=DriversResponse)
async def get_drivers(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get all 5 driver states with contributions.

    TODO: Load from driver_state table via Supabase.
    """
    # Mock data
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


@router.get("/{driver_name}/explain", response_model=DriverExplanation)
async def explain_driver(
    driver_name: str,
    user: dict = Depends(get_current_user),
):
    """Get SHAP-based explanation for driver change.

    TODO: Compute SHAP values from projection engine.
    """
    return DriverExplanation(
        driver_name=driver_name,
        top_factors=[
            {"feature": "rolling_distance_7d", "impact": 0.35, "direction": "positive"},
            {"feature": "z2_pct", "impact": 0.25, "direction": "positive"},
            {"feature": "sessions_per_week", "impact": 0.15, "direction": "positive"},
        ],
        summary=f"Your {DRIVER_DISPLAY_NAMES.get(driver_name, driver_name)} improved primarily due to increased weekly volume and consistent Zone 2 training.",
    )


@router.get("/{driver_name}", response_model=DriverDetailResponse)
async def get_driver_detail(
    driver_name: str,
    days: int = Query(default=42, ge=7, le=90),
    user: dict = Depends(get_current_user),
):
    """Get single driver trend data.

    TODO: Load from driver_state history via Supabase.
    """
    from datetime import datetime, timedelta

    display_name = DRIVER_DISPLAY_NAMES.get(
        driver_name, driver_name.replace("_", " ").title()
    )
    description = DRIVER_DESCRIPTIONS.get(driver_name, "")

    # Mock history
    history = []
    base_score = 55.0
    for i in range(min(days, 30)):
        date = datetime(2026, 3, 5) - timedelta(days=i)
        score = base_score + (i * 0.5)
        history.append(
            DriverDetailPoint(
                date=date.strftime("%Y-%m-%d"),
                score=round(min(score, 100), 1),
            )
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
