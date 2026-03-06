from fastapi import APIRouter, Depends

from app.dependencies import get_current_user

router = APIRouter()


@router.post("")
async def chat(user: dict = Depends(get_current_user)):
    """Send message to PIRX AI chat agent."""
    return {"message": "Not implemented - Phase 3"}
