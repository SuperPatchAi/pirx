"""Activities API — list activities by date range for calendar and history views."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

router = APIRouter()


@router.get("")
async def list_activities(
    user: dict = Depends(get_current_user),
    from_date: str = Query(..., alias="from", description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., alias="to", description="End date YYYY-MM-DD"),
):
    """Get activities for a date range. Used by calendar heatmap and activity history."""
    db = SupabaseService()
    from_iso = f"{from_date}T00:00:00Z"
    to_iso = f"{to_date}T23:59:59Z"
    activities = db.get_activities_range(user["user_id"], from_iso, to_iso)
    return {"activities": activities}
