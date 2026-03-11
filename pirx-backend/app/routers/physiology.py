from typing import Optional

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter()


class PhysiologyEntry(BaseModel):
    resting_hr: Optional[int] = None
    hrv: Optional[float] = None
    sleep_score: Optional[float] = None
    confidence_score: Optional[float] = Field(None, ge=1, le=10)
    fatigue_score: Optional[float] = Field(None, ge=1, le=10)
    focus_score: Optional[float] = Field(None, ge=1, le=10)
    notes: Optional[str] = None
    blood_lactate_rest: Optional[float] = None
    blood_lactate_easy: Optional[float] = None
    blood_lactate_threshold: Optional[float] = None
    blood_lactate_race: Optional[float] = None
    hemoglobin: Optional[float] = None
    hematocrit: Optional[float] = None
    ferritin: Optional[float] = None
    rbc: Optional[float] = None
    iron: Optional[float] = None
    vitamin_d: Optional[float] = None
    testosterone: Optional[float] = None


class MindsetCheckIn(BaseModel):
    confidence_score: Optional[float] = Field(None, ge=1, le=10)
    fatigue_score: Optional[float] = Field(None, ge=1, le=10)
    focus_score: Optional[float] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class PhysiologyResponse(BaseModel):
    entry_id: str
    timestamp: str
    source: str
    resting_hr: Optional[int] = None
    hrv: Optional[float] = None
    sleep_score: Optional[float] = None
    confidence_score: Optional[float] = None
    fatigue_score: Optional[float] = None
    focus_score: Optional[float] = None
    notes: Optional[str] = None


class PhysiologyTrendsResponse(BaseModel):
    entries: list[dict]
    period_days: int


@router.get("/trends", response_model=PhysiologyTrendsResponse)
async def get_physiology_trends(
    days: int = 30,
    user: dict = Depends(get_current_user),
):
    """Get physiology trend data for charts."""
    db = SupabaseService()
    entries = db.get_recent_physiology(user["user_id"], limit=days)
    if not entries:
        entries = _generate_mock_trends(days)
    return PhysiologyTrendsResponse(entries=entries, period_days=days)


@router.post("", response_model=dict)
async def create_physiology_entry(
    entry: PhysiologyEntry,
    user: dict = Depends(get_current_user),
):
    """Create a manual physiology entry."""
    db = SupabaseService()
    data = entry.model_dump(exclude_none=True)
    data["user_id"] = user["user_id"]
    data["source"] = "manual"

    try:
        result = db.client.table("physiology").insert(data).execute()
        return {
            "status": "created",
            "entry_id": result.data[0]["entry_id"] if result.data else None,
        }
    except Exception:
        logger.exception("Failed to insert physiology entry for user %s", user["user_id"])
        raise HTTPException(status_code=500, detail="Failed to save physiology entry")


@router.get("/latest")
async def get_latest_physiology(user: dict = Depends(get_current_user)):
    """Get a merged view of the freshest non-null physiology values.

    Because sleep, body, and daily webhooks arrive as separate rows, returning
    only the single newest row would hide values delivered by an earlier type.
    This merges the latest non-null value for each field across the most recent
    entries (up to 20, covering ~1 week of mixed webhook types).
    """
    db = SupabaseService()
    entries = db.get_recent_physiology(user["user_id"], limit=20)
    if not entries:
        return _generate_mock_latest()

    TOP_LEVEL_KEYS = {
        "sleep_score", "resting_hr", "hrv",
        "confidence_score", "fatigue_score", "focus_score", "notes",
    }
    CUSTOM_KEYS = {
        "weight_kg", "body_fat_percentage", "bmi", "vo2max_ml_per_min_per_kg",
        "avg_stress_level", "strain_level",
        "sleep_total_seconds", "sleep_deep_seconds", "sleep_light_seconds",
        "sleep_rem_seconds", "sleep_efficiency",
        "daily_activity_score", "daily_recovery_score", "daily_recovery_score_from_scores",
    }

    merged = {
        "entry_id": entries[0].get("entry_id"),
        "timestamp": entries[0].get("timestamp"),
        "source": entries[0].get("source"),
    }

    for key in TOP_LEVEL_KEYS:
        merged[key] = None
    merged_custom: dict = {}
    for key in CUSTOM_KEYS:
        merged_custom[key] = None

    for entry in entries:
        for key in TOP_LEVEL_KEYS:
            if merged[key] is None and entry.get(key) is not None:
                merged[key] = entry[key]
        cf = entry.get("custom_fields") or {}
        for key in CUSTOM_KEYS:
            if merged_custom[key] is None and cf.get(key) is not None:
                merged_custom[key] = cf[key]

    merged["custom_fields"] = merged_custom
    return merged


@router.post("/mindset")
async def submit_mindset_checkin(
    body: MindsetCheckIn,
    user: dict = Depends(get_current_user),
):
    """Submit a daily mindset check-in."""
    db = SupabaseService()
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="At least one score is required")
    data["user_id"] = user["user_id"]
    data["source"] = "mindset_checkin"
    try:
        result = db.client.table("physiology").insert(data).execute()
        return {
            "status": "recorded",
            "entry_id": result.data[0]["entry_id"] if result.data else None,
        }
    except Exception:
        logger.exception("Failed to save mindset check-in for user %s", user["user_id"])
        raise HTTPException(status_code=500, detail="Failed to save mindset check-in")


def _generate_mock_trends(days: int) -> list[dict]:
    return []


def _generate_mock_latest() -> dict:
    return {
        "entry_id": None,
        "timestamp": None,
        "source": None,
        "resting_hr": None,
        "hrv": None,
        "sleep_score": None,
        "confidence_score": None,
        "fatigue_score": None,
        "focus_score": None,
    }
