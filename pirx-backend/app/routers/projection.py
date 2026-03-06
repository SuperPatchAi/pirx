from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def get_projection(
    event: str = Query(default="3000"),
    user: dict = Depends(get_current_user),
):
    """Get current projection for a specific event."""
    return {"message": "Not implemented", "event": event, "user_id": user["user_id"]}


@router.get("/history")
async def get_projection_history(
    event: str = Query(default="3000"),
    days: int = Query(default=90),
    user: dict = Depends(get_current_user),
):
    """Get projection history time-series."""
    return {"message": "Not implemented", "event": event, "days": days}


@router.get("/trajectory")
async def get_trajectory(
    event: str = Query(default="3000"),
    user: dict = Depends(get_current_user),
):
    """Get 2-week trajectory scenarios."""
    return {"message": "Not implemented", "event": event}
