from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": "pirx-api",
        "version": "0.1.1",
        "frontend_url": settings.frontend_url,
    }
