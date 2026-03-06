from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user

router = APIRouter()


@router.post("/connect/{provider}")
async def connect_wearable(provider: str, user: dict = Depends(get_current_user)):
    """Initiate wearable OAuth connection."""
    return {"message": "Not implemented", "provider": provider}


@router.post("/disconnect/{provider}")
async def disconnect_wearable(provider: str, user: dict = Depends(get_current_user)):
    """Disconnect wearable and revoke tokens."""
    return {"message": "Not implemented", "provider": provider}


@router.post("/webhook/terra")
async def terra_webhook(request: Request):
    """Receive Terra API webhook for new activity data."""
    return {"message": "Not implemented"}


@router.post("/webhook/strava")
async def strava_webhook(request: Request):
    """Receive Strava webhook for new activity data."""
    return {"message": "Not implemented"}


@router.post("/backfill")
async def trigger_backfill(user: dict = Depends(get_current_user)):
    """Trigger historical data backfill for a user."""
    return {"message": "Not implemented"}
