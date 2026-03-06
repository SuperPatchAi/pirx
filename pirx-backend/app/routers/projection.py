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
    projected = 1182.0
    range_low = 1155.0
    range_high = 1208.0
    return ProjectionResponse(
        event=event,
        projected_time_seconds=projected,
        projected_time_display=_format_time(projected),
        supported_range_low=range_low,
        supported_range_high=range_high,
        supported_range_display=f"{_format_time(range_low)} – {_format_time(range_high)}",
        baseline_time_seconds=1260.0,
        total_improvement_seconds=78.0,
        volatility=2.3,
        last_updated="2026-03-05T12:00:00Z",
    )


def _mock_projection_history(event: str, days: int) -> ProjectionHistoryResponse:
    from datetime import datetime, timedelta

    history = []
    base_time = 1260.0
    for i in range(min(days, 30)):
        date = datetime(2026, 3, 5) - timedelta(days=i)
        improvement = max(0, i * 2.5)
        history.append(
            ProjectionHistoryPoint(
                date=date.strftime("%Y-%m-%d"),
                projected_time_seconds=round(base_time - improvement, 1),
                event=event,
            )
        )
    history.reverse()
    return ProjectionHistoryResponse(event=event, days=days, history=history)


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
            )
            for row in reversed(rows)
        ]
        return ProjectionHistoryResponse(event=event, days=days, history=history)

    return _mock_projection_history(event, days)


@router.get("/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get 2-week trajectory scenarios."""
    try:
        db = SupabaseService()
        projection = db.get_latest_projection(user["user_id"], event)
        current = projection["midpoint_seconds"] if projection else 1182.0
    except Exception:
        logger.exception("Failed to query projection for trajectory")
        current = 1182.0

    return TrajectoryResponse(
        event=event,
        scenarios=[
            TrajectoryScenario(
                label="maintain",
                projected_time_seconds=current - 3,
                projected_time_display=_format_time(current - 3),
                description="Continue current training pattern",
            ),
            TrajectoryScenario(
                label="increase",
                projected_time_seconds=current - 8,
                projected_time_display=_format_time(current - 8),
                description="Increase threshold work by 10 min/week",
            ),
            TrajectoryScenario(
                label="decrease",
                projected_time_seconds=current + 5,
                projected_time_display=_format_time(current + 5),
                description="Reduce training volume by 20%",
            ),
        ],
    )
