import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()


class CoachRegister(BaseModel):
    display_name: str
    organization: Optional[str] = None


class AthleteInvite(BaseModel):
    athlete_email: str


def _format_time(seconds: float) -> str:
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}:{m:02d}:{s:02d}"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


@router.post("/register")
async def register_as_coach(
    body: CoachRegister,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    user_id = user["user_id"]

    existing = db.client.table("coaches").select("coach_id").eq("coach_id", user_id).execute()
    if existing.data:
        return {"status": "already_registered", "coach_id": user_id}

    db.client.table("coaches").insert({
        "coach_id": user_id,
        "display_name": body.display_name,
        "organization": body.organization,
    }).execute()

    return {"status": "registered", "coach_id": user_id}


@router.get("/profile")
async def get_coach_profile(user: dict = Depends(get_current_user)):
    db = SupabaseService()
    result = db.client.table("coaches").select("*").eq("coach_id", user["user_id"]).execute()
    if result.data:
        coach = result.data[0]
        athletes_result = (
            db.client.table("coach_athletes")
            .select("id")
            .eq("coach_id", user["user_id"])
            .eq("status", "active")
            .execute()
        )
        return {
            "is_coach": True,
            "display_name": coach.get("display_name"),
            "organization": coach.get("organization"),
            "tier": coach.get("tier"),
            "max_athletes": coach.get("max_athletes"),
            "current_athletes": len(athletes_result.data) if athletes_result.data else 0,
        }
    return {"is_coach": False}


@router.post("/invite")
async def invite_athlete(
    body: AthleteInvite,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    coach_id = user["user_id"]

    coach = db.client.table("coaches").select("max_athletes").eq("coach_id", coach_id).execute()
    if not coach.data:
        raise HTTPException(status_code=403, detail="Not registered as a coach")

    max_athletes = coach.data[0].get("max_athletes", 5)
    current = (
        db.client.table("coach_athletes")
        .select("id")
        .eq("coach_id", coach_id)
        .neq("status", "revoked")
        .execute()
    )
    if current.data and len(current.data) >= max_athletes:
        raise HTTPException(status_code=400, detail=f"Maximum of {max_athletes} athletes reached")

    athlete_user = db.client.table("users").select("user_id").eq("email", body.athlete_email).execute()
    athlete_id = athlete_user.data[0]["user_id"] if athlete_user.data else None

    if not athlete_id:
        raise HTTPException(status_code=404, detail="No user found with that email")

    existing = (
        db.client.table("coach_athletes")
        .select("id, status")
        .eq("coach_id", coach_id)
        .eq("athlete_id", athlete_id)
        .execute()
    )
    if existing.data:
        row = existing.data[0]
        if row["status"] == "active":
            return {"status": "already_active"}
        if row["status"] == "pending":
            return {"status": "already_pending"}
        db.client.table("coach_athletes").update({
            "status": "pending",
            "invited_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row["id"]).execute()
        return {"status": "reinvited"}

    db.client.table("coach_athletes").insert({
        "coach_id": coach_id,
        "athlete_id": athlete_id,
        "athlete_email": body.athlete_email,
        "status": "pending",
    }).execute()

    return {"status": "invited", "athlete_email": body.athlete_email}


@router.get("/athletes")
async def list_athletes(user: dict = Depends(get_current_user)):
    db = SupabaseService()
    coach_id = user["user_id"]

    result = (
        db.client.table("coach_athletes")
        .select("*")
        .eq("coach_id", coach_id)
        .neq("status", "revoked")
        .order("invited_at", desc=True)
        .execute()
    )
    if not result.data:
        return {"athletes": []}

    athletes = []
    for row in result.data:
        athlete_id = row["athlete_id"]
        athlete_data = {
            "id": athlete_id,
            "email": row.get("athlete_email", ""),
            "status": row["status"],
            "invited_at": row.get("invited_at"),
        }

        if row["status"] != "active":
            athletes.append(athlete_data)
            continue

        user_info = db.get_user(athlete_id)
        athlete_data["display_name"] = user_info.get("display_name", "Unknown") if user_info else "Unknown"
        athlete_data["primary_event"] = user_info.get("primary_event", "5000") if user_info else "5000"

        proj = db.get_latest_projection(athlete_id, athlete_data["primary_event"])
        if proj:
            midpoint = proj.get("midpoint_seconds", 0)
            athlete_data["projected_time"] = _format_time(midpoint) if midpoint else "—"
            athlete_data["projected_time_seconds"] = midpoint
            athlete_data["twenty_one_day_change"] = proj.get("twenty_one_day_change", 0)
        else:
            athlete_data["projected_time"] = "—"
            athlete_data["projected_time_seconds"] = 0
            athlete_data["twenty_one_day_change"] = 0

        try:
            from app.ml.readiness_engine import ReadinessEngine
            from app.models.activities import NormalizedActivity
            from app.services.feature_service import FeatureService

            activities_raw = db.get_recent_activities(athlete_id, days=90)
            if activities_raw:
                activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]
                features = FeatureService.compute_all_features(activities)
                readiness = ReadinessEngine().compute_readiness(
                    features=features,
                    days_since_last_activity=0,
                    days_since_long_run=None,
                    sleep_score=None,
                )
                athlete_data["readiness_score"] = readiness.score
            else:
                athlete_data["readiness_score"] = None
        except Exception:
            athlete_data["readiness_score"] = None

        athletes.append(athlete_data)

    return {"athletes": athletes}


@router.get("/athlete/{athlete_id}/projection")
async def get_athlete_projection(
    athlete_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    _verify_coach_access(db, user["user_id"], athlete_id)

    user_info = db.get_user(athlete_id)
    event = user_info.get("primary_event", "5000") if user_info else "5000"

    events = ["1500", "3000", "5000", "10000", "21097", "42195"]
    projections = {}
    for ev in events:
        proj = db.get_latest_projection(athlete_id, ev)
        if proj:
            midpoint = proj.get("midpoint_seconds", 0)
            projections[ev] = {
                "projected_time": _format_time(midpoint),
                "projected_time_seconds": midpoint,
                "range_low": proj.get("range_low_seconds"),
                "range_high": proj.get("range_high_seconds"),
                "twenty_one_day_change": proj.get("twenty_one_day_change", 0),
            }

    return {"athlete_id": athlete_id, "primary_event": event, "projections": projections}


@router.get("/athlete/{athlete_id}/drivers")
async def get_athlete_drivers(
    athlete_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    _verify_coach_access(db, user["user_id"], athlete_id)

    drivers_raw = db.get_latest_drivers(athlete_id)
    if not drivers_raw:
        return {"drivers": []}

    row = drivers_raw[0]
    DRIVER_NAMES = {
        "aerobic_base": "Aerobic Base",
        "threshold_density": "Threshold Density",
        "speed_exposure": "Speed Exposure",
        "running_economy": "Running Economy",
        "load_consistency": "Load Consistency",
    }
    drivers = []
    for key, display in DRIVER_NAMES.items():
        drivers.append({
            "name": key,
            "display_name": display,
            "contribution_seconds": row.get(f"{key}_seconds", 0),
            "score": row.get(f"{key}_score", 50),
            "trend": row.get(f"{key}_trend", "stable"),
        })

    return {"drivers": drivers}


@router.get("/athlete/{athlete_id}/readiness")
async def get_athlete_readiness(
    athlete_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    _verify_coach_access(db, user["user_id"], athlete_id)

    try:
        from app.ml.readiness_engine import ReadinessEngine
        from app.models.activities import NormalizedActivity
        from app.services.feature_service import FeatureService

        activities_raw = db.get_recent_activities(athlete_id, days=90)
        if not activities_raw:
            return {"score": 0, "label": "Insufficient Data", "factors": []}

        activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]
        features = FeatureService.compute_all_features(activities)
        result = ReadinessEngine().compute_readiness(
            features=features,
            days_since_last_activity=0,
            days_since_long_run=None,
            sleep_score=None,
        )
        return {"score": result.score, "label": result.label, "factors": result.factors}
    except Exception:
        logger.exception("Failed to compute athlete readiness")
        return {"score": 0, "label": "Error", "factors": []}


@router.delete("/athlete/{athlete_id}")
async def remove_athlete(
    athlete_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    db.client.table("coach_athletes").update({"status": "revoked"}).eq(
        "coach_id", user["user_id"]
    ).eq("athlete_id", athlete_id).execute()
    return {"status": "removed", "athlete_id": athlete_id}


@router.post("/accept-invite/{coach_id}")
async def accept_invite(
    coach_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    result = (
        db.client.table("coach_athletes")
        .select("id, status")
        .eq("coach_id", coach_id)
        .eq("athlete_id", user["user_id"])
        .eq("status", "pending")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No pending invitation found")

    db.client.table("coach_athletes").update({
        "status": "active",
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", result.data[0]["id"]).execute()

    return {"status": "accepted", "coach_id": coach_id}


@router.post("/decline-invite/{coach_id}")
async def decline_invite(
    coach_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    db.client.table("coach_athletes").update({"status": "revoked"}).eq(
        "coach_id", coach_id
    ).eq("athlete_id", user["user_id"]).eq("status", "pending").execute()
    return {"status": "declined", "coach_id": coach_id}


@router.get("/my-coaches")
async def get_my_coaches(user: dict = Depends(get_current_user)):
    db = SupabaseService()
    result = (
        db.client.table("coach_athletes")
        .select("*")
        .eq("athlete_id", user["user_id"])
        .neq("status", "revoked")
        .execute()
    )
    if not result.data:
        return {"coaches": []}

    coaches = []
    for row in result.data:
        coach_info = (
            db.client.table("coaches")
            .select("display_name, organization")
            .eq("coach_id", row["coach_id"])
            .execute()
        )
        coach_data = coach_info.data[0] if coach_info.data else {}
        coaches.append({
            "coach_id": row["coach_id"],
            "display_name": coach_data.get("display_name", "Unknown"),
            "organization": coach_data.get("organization"),
            "status": row["status"],
            "invited_at": row.get("invited_at"),
        })

    return {"coaches": coaches}


@router.post("/revoke-coach/{coach_id}")
async def revoke_coach_access(
    coach_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    db.client.table("coach_athletes").update({"status": "revoked"}).eq(
        "coach_id", coach_id
    ).eq("athlete_id", user["user_id"]).execute()
    return {"status": "revoked", "coach_id": coach_id}


def _verify_coach_access(db: SupabaseService, coach_id: str, athlete_id: str):
    result = (
        db.client.table("coach_athletes")
        .select("status")
        .eq("coach_id", coach_id)
        .eq("athlete_id", athlete_id)
        .eq("status", "active")
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=403,
            detail="No active coaching relationship with this athlete",
        )
