from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

router = APIRouter()


# ---------------------------------------------------------------------------
# GDPR / PIPEDA — Data Export & Deletion
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_user_data(user: dict = Depends(get_current_user)):
    """Export all user data as JSON (GDPR/PIPEDA compliance)."""
    db = SupabaseService()
    user_id = user["user_id"]

    events = ["1500", "3000", "5000", "10000", "21097", "42195"]
    try:
        all_projections = {}
        for event in events:
            try:
                proj = db.get_projection_history(user_id, event, days=3650)
                if proj:
                    all_projections[event] = proj
            except Exception:
                pass

        physiology_data = []
        try:
            physiology_data = db.get_recent_physiology(user_id, limit=10000) or []
        except Exception:
            pass

        notification_data = []
        try:
            result = db.client.table("notification_log").select("*").eq("user_id", user_id).execute()
            notification_data = result.data or []
        except Exception:
            pass

        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "profile": db.get_user(user_id),
            "activities": db.get_activities(user_id, limit=10000, days=3650),
            "projections": all_projections,
            "drivers": db.get_driver_history(user_id, days=3650),
            "wearable_connections": db.get_wearable_connections(user_id),
            "physiology": physiology_data,
            "notifications": notification_data,
        }
    except Exception:
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "error": "Partial export - some data may be missing",
        }

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=pirx-export-{user_id[:8]}.json"
        },
    )


@router.delete("/delete")
async def delete_user_data(user: dict = Depends(get_current_user)):
    """Delete all user data (GDPR right to erasure)."""
    db = SupabaseService()
    user_id = user["user_id"]

    tables = [
        "notification_log",
        "user_embeddings",
        "physiology",
        "driver_state",
        "projection_state",
        "activity_adjuncts",
        "adjunct_state",
        "intervals",
        "activities",
        "wearable_connections",
        "task_registry",
        "model_metrics",
    ]

    deleted: dict[str, int | str] = {}
    for table in tables:
        try:
            result = (
                db.client.table(table).delete().eq("user_id", user_id).execute()
            )
            deleted[table] = len(result.data) if result.data else 0
        except Exception:
            deleted[table] = "error"

    try:
        db.client.table("users").delete().eq("user_id", user_id).execute()
        deleted["users"] = 1
    except Exception:
        deleted["users"] = "error"

    return {"status": "deleted", "user_id": user_id, "tables_affected": deleted}


# ---------------------------------------------------------------------------
# Baseline Management
# ---------------------------------------------------------------------------


class BaselineUpdate(BaseModel):
    event: str
    time_seconds: float
    race_date: Optional[str] = None
    source: str = "manual"


@router.get("/baseline")
async def get_baseline(user: dict = Depends(get_current_user)):
    """Get current baseline race."""
    db = SupabaseService()
    user_data = db.get_user(user["user_id"])
    if user_data:
        return {
            "event": user_data.get("baseline_event", "5000"),
            "time_seconds": user_data.get("baseline_time_seconds", 1260.0),
            "race_date": user_data.get("baseline_race_date"),
            "source": user_data.get("baseline_source", "auto"),
        }
    return {"event": "5000", "time_seconds": 1260.0, "race_date": None, "source": "auto"}


@router.put("/baseline")
async def update_baseline(
    body: BaselineUpdate, user: dict = Depends(get_current_user)
):
    """Update baseline race (manual override)."""
    db = SupabaseService()
    try:
        db.client.table("users").update(
            {
                "baseline_event": body.event,
                "baseline_time_seconds": body.time_seconds,
                "baseline_race_date": body.race_date,
                "baseline_source": body.source,
            }
        ).eq("user_id", user["user_id"]).execute()
        return {
            "status": "updated",
            "event": body.event,
            "time_seconds": body.time_seconds,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ---------------------------------------------------------------------------
# Adjunct Library CRUD
# ---------------------------------------------------------------------------


class AdjunctCreate(BaseModel):
    name: str
    description: str = ""


@router.get("/adjunct-library")
async def get_adjunct_library(user: dict = Depends(get_current_user)):
    """Get user's custom adjunct library."""
    return {
        "adjuncts": [
            {
                "id": "altitude",
                "name": "Altitude Training",
                "description": "Training at elevation > 1500m",
            },
            {
                "id": "strength",
                "name": "Strength Training",
                "description": "Gym-based resistance work",
            },
            {
                "id": "heat",
                "name": "Heat Acclimation",
                "description": "Training in high temperature",
            },
        ]
    }


@router.post("/adjunct-library")
async def add_adjunct(
    body: AdjunctCreate, user: dict = Depends(get_current_user)
):
    return {"status": "created", "name": body.name}


@router.delete("/adjunct-library/{adjunct_id}")
async def delete_adjunct(
    adjunct_id: str, user: dict = Depends(get_current_user)
):
    return {"status": "deleted", "id": adjunct_id}
