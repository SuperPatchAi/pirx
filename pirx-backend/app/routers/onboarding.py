import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter()

STANDARD_EVENTS = {
    "1500": 1500,
    "3000": 3000,
    "5000": 5000,
    "10000": 10000,
    "21097": 21097,
    "42195": 42195,
}

RIEGEL_EXPONENT = 1.06

DRIVERS = [
    "aerobic_base",
    "threshold_density",
    "speed_exposure",
    "load_consistency",
    "running_economy",
]

COLD_START_EVENT = "5000"
COLD_START_TIME = 1500.0  # 25:00


def riegel_scale(baseline_time: float, baseline_distance: int, target_distance: int) -> float:
    return baseline_time * (target_distance / baseline_distance) ** RIEGEL_EXPONENT


def _format_time(seconds: float) -> str:
    if seconds >= 3600:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{mins:02d}:{secs:02d}"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


# ── Request / Response Models ───────────────────────────────────────

class SetBaselineRequest(BaseModel):
    event: str
    time_seconds: float
    source: str = "manual"


class GenerateProjectionRequest(BaseModel):
    primary_event: str


class DetectedRace(BaseModel):
    event: str
    time_seconds: float
    timestamp: Optional[str] = None
    distance_meters: Optional[float] = None


class DetectBaselineResponse(BaseModel):
    baseline_event: str
    baseline_time_seconds: float
    baseline_source: str
    detected_races: list[DetectedRace]


# ── Endpoints ───────────────────────────────────────────────────────

@router.post("/detect-baseline", response_model=DetectBaselineResponse)
async def detect_baseline(user: dict = Depends(get_current_user)):
    """Detect baseline from the user's race history, or return a cold-start default."""
    user_id = user["user_id"]
    db = SupabaseService()

    try:
        races = db.get_race_activities(user_id)
    except Exception:
        logger.exception("Failed to query race activities")
        races = []

    if races:
        detected = []
        for r in races:
            dist = r.get("distance_meters") or r.get("distance")
            elapsed = r.get("elapsed_time_seconds") or r.get("moving_time_seconds")
            if dist and elapsed:
                event_label = _match_event(dist)
                detected.append(
                    DetectedRace(
                        event=event_label,
                        time_seconds=elapsed,
                        timestamp=r.get("timestamp"),
                        distance_meters=dist,
                    )
                )

        if detected:
            best = min(detected, key=lambda d: d.time_seconds)
            return DetectBaselineResponse(
                baseline_event=best.event,
                baseline_time_seconds=best.time_seconds,
                baseline_source="race_history",
                detected_races=detected,
            )

    return DetectBaselineResponse(
        baseline_event=COLD_START_EVENT,
        baseline_time_seconds=COLD_START_TIME,
        baseline_source="cold_start",
        detected_races=[],
    )


@router.post("/set-baseline")
async def set_baseline(
    body: SetBaselineRequest,
    user: dict = Depends(get_current_user),
):
    """Write the chosen baseline to the users table."""
    user_id = user["user_id"]
    db = SupabaseService()

    update_data = {
        "baseline_event": body.event,
        "baseline_time_seconds": body.time_seconds,
        "baseline_source": body.source,
        "primary_event": body.event,
    }

    try:
        db.client.table("users").update(update_data).eq("user_id", user_id).execute()
    except Exception:
        logger.exception("Failed to update baseline on user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to save baseline")

    return {
        "status": "ok",
        "baseline_event": body.event,
        "baseline_time_seconds": body.time_seconds,
        "primary_event": body.event,
    }


@router.post("/generate-projection")
async def generate_projection(
    body: GenerateProjectionRequest,
    user: dict = Depends(get_current_user),
):
    """Generate initial projections for all standard events after onboarding."""
    user_id = user["user_id"]
    db = SupabaseService()

    user_row = db.get_user(user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    baseline_seconds = user_row.get("baseline_time_seconds")
    baseline_event = user_row.get("baseline_event")
    if not baseline_seconds or not baseline_event:
        raise HTTPException(
            status_code=400,
            detail="Baseline not set. Call /set-baseline first.",
        )

    baseline_distance = STANDARD_EVENTS.get(baseline_event)
    if not baseline_distance:
        raise HTTPException(status_code=400, detail=f"Unknown baseline event: {baseline_event}")

    now = datetime.now(timezone.utc).isoformat()
    projections = {}

    for event_label, distance in STANDARD_EVENTS.items():
        if event_label == baseline_event:
            midpoint = baseline_seconds
        else:
            midpoint = riegel_scale(baseline_seconds, baseline_distance, distance)

        range_lower = midpoint * 0.97
        range_upper = midpoint * 1.03

        projection_data = {
            "user_id": user_id,
            "event": event_label,
            "midpoint_seconds": round(midpoint, 2),
            "range_lower": round(range_lower, 2),
            "range_upper": round(range_upper, 2),
            "range_low_seconds": round(range_lower, 2),
            "range_high_seconds": round(range_upper, 2),
            "confidence_score": 0.5,
            "volatility_score": 0.2,
            "volatility": 0.2,
            "baseline_seconds": round(midpoint, 2),
            "status": "Holding",
            "model_type": "lmc",
            "computed_at": now,
        }

        try:
            result = db.insert_projection(projection_data)
            projections[event_label] = result
        except Exception:
            logger.exception("Failed to insert projection for event %s", event_label)
            projections[event_label] = projection_data

    driver_data = {
        "user_id": user_id,
        "computed_at": now,
    }
    for driver in DRIVERS:
        driver_data[f"{driver}_seconds"] = 0.0
        driver_data[f"{driver}_score"] = 50
        driver_data[f"{driver}_trend"] = "stable"

    try:
        db.insert_driver_state(driver_data)
    except Exception:
        logger.exception("Failed to insert initial driver state")

    try:
        db.client.table("users").update(
            {"onboarding_completed": True}
        ).eq("user_id", user_id).execute()
    except Exception:
        logger.exception("Failed to mark onboarding complete for user %s", user_id)

    primary = projections.get(body.primary_event, projections.get(baseline_event))

    return {
        "status": "ok",
        "primary_event": body.primary_event,
        "primary_projection": primary,
        "all_projections": projections,
    }


# ── Helpers ─────────────────────────────────────────────────────────

def _match_event(distance_meters: float) -> str:
    """Snap a raw distance to the nearest standard event label."""
    best_label = "5000"
    best_diff = float("inf")
    for label, dist in STANDARD_EVENTS.items():
        diff = abs(distance_meters - dist)
        if diff < best_diff:
            best_diff = diff
            best_label = label
    return best_label
