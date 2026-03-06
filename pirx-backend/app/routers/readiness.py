from fastapi import APIRouter, Depends

from app.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def get_readiness(user: dict = Depends(get_current_user)):
    """Get Event Readiness scores across all events."""
    return {"message": "Not implemented"}
