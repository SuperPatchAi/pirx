from fastapi import APIRouter, Depends

from app.dependencies import get_current_user

router = APIRouter()


@router.get("/zones")
async def get_zone_distribution(user: dict = Depends(get_current_user)):
    """Get HR zone distribution and pace guide."""
    return {"message": "Not implemented"}


@router.get("/economy")
async def get_running_economy(user: dict = Depends(get_current_user)):
    """Get running economy metrics."""
    return {"message": "Not implemented"}
