from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def get_drivers(
    event: str = Query(default="3000"),
    user: dict = Depends(get_current_user),
):
    """Get all 5 driver states with contributions."""
    return {"message": "Not implemented", "event": event}


@router.get("/{driver_name}")
async def get_driver_detail(
    driver_name: str,
    days: int = Query(default=42),
    user: dict = Depends(get_current_user),
):
    """Get single driver trend data."""
    return {"message": "Not implemented", "driver": driver_name, "days": days}


@router.get("/{driver_name}/explain")
async def explain_driver(
    driver_name: str,
    user: dict = Depends(get_current_user),
):
    """Get SHAP-based explanation for driver change."""
    return {"message": "Not implemented", "driver": driver_name}
