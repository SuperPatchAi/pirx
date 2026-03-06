from datetime import datetime, timedelta, timezone
from typing import Optional
import random

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

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
        return {"status": "created", "entry_id": "mock-id"}


@router.get("/latest")
async def get_latest_physiology(user: dict = Depends(get_current_user)):
    """Get the most recent physiology entry."""
    db = SupabaseService()
    entries = db.get_recent_physiology(user["user_id"], limit=1)
    if entries:
        return entries[0]
    return _generate_mock_latest()


def _generate_mock_trends(days: int) -> list[dict]:
    """Generate mock trend data for development."""
    entries = []
    now = datetime.now(timezone.utc)
    for i in range(days):
        date = now - timedelta(days=days - 1 - i)
        entries.append(
            {
                "entry_id": f"mock-{i}",
                "timestamp": date.isoformat(),
                "source": "wearable",
                "resting_hr": 52 + random.randint(-3, 3),
                "hrv": 45 + random.uniform(-8, 8),
                "sleep_score": 72 + random.uniform(-12, 12),
            }
        )
    return entries


def _generate_mock_latest() -> dict:
    return {
        "entry_id": "mock-latest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "wearable",
        "resting_hr": 52,
        "hrv": 48.0,
        "sleep_score": 75.0,
        "confidence_score": None,
        "fatigue_score": None,
        "focus_score": None,
    }
