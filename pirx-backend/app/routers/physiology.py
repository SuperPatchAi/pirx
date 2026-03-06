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
    """Get the most recent physiology entry."""
    db = SupabaseService()
    entries = db.get_recent_physiology(user["user_id"], limit=1)
    if entries:
        return entries[0]
    return _generate_mock_latest()


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
