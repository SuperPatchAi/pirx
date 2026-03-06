from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, drivers, features, health, projection, readiness, sync

app = FastAPI(
    title="PIRX API",
    description="Performance Intelligence Rx — Projection Engine & ML Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(projection.router, prefix="/projection", tags=["projection"])
app.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
app.include_router(readiness.router, prefix="/readiness", tags=["readiness"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(features.router, prefix="/features", tags=["features"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
