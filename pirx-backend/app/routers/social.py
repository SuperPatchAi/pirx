import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()

EVENT_DISPLAY_NAMES = {
    "1500": "1500m",
    "3000": "3K",
    "5000": "5K",
    "10000": "10K",
    "21097": "Half Marathon",
    "42195": "Marathon",
}

DRIVER_DISPLAY_NAMES = {
    "aerobic_base": "Aerobic Base",
    "threshold_density": "Threshold",
    "speed_exposure": "Speed",
    "running_economy": "Economy",
    "load_consistency": "Consistency",
}


def _format_time(seconds: float) -> str:
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}:{m:02d}:{s:02d}"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


@router.get("/card-data")
async def get_card_data(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get structured data for rendering a shareable Race Prediction Card."""
    db = SupabaseService()
    user_id = user["user_id"]

    projection = db.get_latest_projection(user_id, event)
    if not projection:
        raise HTTPException(status_code=404, detail="No projection found for this event")

    midpoint = projection["midpoint_seconds"]
    range_low = projection.get("range_low_seconds", midpoint * 0.97)
    range_high = projection.get("range_high_seconds", midpoint * 1.03)
    baseline = projection.get("baseline_seconds", midpoint)
    improvement = baseline - midpoint
    change_21d = projection.get("twenty_one_day_change", 0)

    drivers_raw = db.get_latest_drivers(user_id)
    driver_contributions = []
    if drivers_raw:
        row = drivers_raw[0]
        for key, display in DRIVER_DISPLAY_NAMES.items():
            contribution = row.get(f"{key}_seconds", 0.0)
            driver_contributions.append({
                "name": key,
                "display_name": display,
                "contribution_seconds": contribution,
            })

    user_data = db.get_user(user_id)
    display_name = user_data.get("display_name", "Runner") if user_data else "Runner"

    return {
        "event": event,
        "event_display": EVENT_DISPLAY_NAMES.get(event, f"{event}m"),
        "projected_time": _format_time(midpoint),
        "projected_time_seconds": midpoint,
        "supported_range": f"{_format_time(range_low)} – {_format_time(range_high)}",
        "improvement_seconds": round(improvement, 1),
        "twenty_one_day_change": round(change_21d, 1),
        "driver_contributions": driver_contributions,
        "user_display_name": display_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/cohort")
async def get_cohort_ranking(
    event: str = Query(default="5000"),
    user: dict = Depends(get_current_user),
):
    """Get user's percentile rank among all runners for an event."""
    db = SupabaseService()
    user_id = user["user_id"]

    user_proj = db.get_latest_projection(user_id, event)
    if not user_proj or not user_proj.get("midpoint_seconds"):
        return {"event": event, "percentile": None, "sample_size": 0}

    user_time = user_proj["midpoint_seconds"]

    try:
        result = (
            db.client.table("cohort_benchmarks")
            .select("*")
            .eq("event", event)
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            bench = result.data[0]
            p10 = bench.get("percentile_10", 0)
            p25 = bench.get("percentile_25", 0)
            p50 = bench.get("percentile_50", 0)
            p75 = bench.get("percentile_75", 0)
            p90 = bench.get("percentile_90", 0)
            sample = bench.get("sample_size", 0)

            if user_time <= p10:
                percentile = 95
            elif user_time <= p25:
                percentile = 75 + 20 * (p25 - user_time) / max(p25 - p10, 1)
            elif user_time <= p50:
                percentile = 50 + 25 * (p50 - user_time) / max(p50 - p25, 1)
            elif user_time <= p75:
                percentile = 25 + 25 * (p75 - user_time) / max(p75 - p50, 1)
            elif user_time <= p90:
                percentile = 10 + 15 * (p90 - user_time) / max(p90 - p75, 1)
            else:
                percentile = 5

            return {
                "event": event,
                "percentile": round(percentile),
                "sample_size": sample,
                "benchmarks": {
                    "p10": _format_time(p10),
                    "p25": _format_time(p25),
                    "p50": _format_time(p50),
                    "p75": _format_time(p75),
                    "p90": _format_time(p90),
                },
            }
    except Exception:
        logger.exception("Failed to get cohort benchmarks")

    return {"event": event, "percentile": None, "sample_size": 0}
