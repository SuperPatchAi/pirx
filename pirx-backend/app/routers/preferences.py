from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

router = APIRouter()


class Preferences(BaseModel):
    projection_shifts: bool = True
    readiness_changes: bool = True
    intervention_alerts: bool = True
    weekly_summary: bool = True
    race_reminders: bool = True
    new_insights: bool = True


@router.get("")
async def get_preferences(user: dict = Depends(get_current_user)):
    db = SupabaseService()
    user_data = db.get_user(user["user_id"])
    if user_data and user_data.get("custom_fields"):
        prefs = user_data["custom_fields"].get("notification_preferences", {})
        return Preferences(**prefs)
    return Preferences()


@router.put("")
async def update_preferences(
    body: Preferences, user: dict = Depends(get_current_user)
):
    db = SupabaseService()
    user_data = db.get_user(user["user_id"])
    custom_fields = (user_data or {}).get("custom_fields", {}) or {}
    custom_fields["notification_preferences"] = body.model_dump()
    try:
        db.client.table("users").update(
            {"custom_fields": custom_fields}
        ).eq("user_id", user["user_id"]).execute()
    except Exception:
        pass
    return body
