from fastapi import APIRouter, Depends, Query
from app.dependencies import get_current_user
from app.models.projection import (
    ProjectionResponse,
    ProjectionHistoryResponse,
    ProjectionHistoryPoint,
    TrajectoryResponse,
    TrajectoryScenario,
)

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


@router.get("", response_model=ProjectionResponse)
async def get_projection(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get current projection for a specific event.

    TODO: Load from projection_state table via Supabase.
    """
    # Mock data - replace with DB query
    projected = 1182.0  # 19:42
    range_low = 1155.0  # 19:15
    range_high = 1208.0  # 20:08

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


@router.get("/history", response_model=ProjectionHistoryResponse)
async def get_projection_history(
    event: str = Query(default="5000"),
    days: int = Query(default=90, ge=7, le=365),
    user: dict = Depends(get_current_user),
):
    """Get projection history time-series.

    TODO: Query projection_state table, aggregate by day.
    """
    from datetime import datetime, timedelta

    # Mock history data
    history = []
    base_time = 1260.0
    for i in range(min(days, 30)):
        date = datetime(2026, 3, 5) - timedelta(days=i)
        improvement = max(0, i * 2.5)  # gradual improvement
        history.append(
            ProjectionHistoryPoint(
                date=date.strftime("%Y-%m-%d"),
                projected_time_seconds=round(base_time - improvement, 1),
                event=event,
            )
        )

    history.reverse()

    return ProjectionHistoryResponse(event=event, days=days, history=history)


@router.get("/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get 2-week trajectory scenarios.

    TODO: Compute from projection engine + feature trends.
    """
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
