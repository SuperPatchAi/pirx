import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import account, accuracy, activities, chat, coach, drivers, features, health, metrics, notifications, onboarding, physiology, preferences, projection, readiness, social, sync

app = FastAPI(
    title="PIRX API",
    description="Performance Intelligence Rx — Projection Engine & ML Backend",
    version="0.1.0",
)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

app.add_middleware(RequestLoggingMiddleware)

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
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(physiology.router, prefix="/physiology", tags=["physiology"])
app.include_router(account.router, prefix="/account", tags=["account"])
app.include_router(activities.router, prefix="/activities", tags=["activities"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
app.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(accuracy.router, prefix="/accuracy", tags=["accuracy"])
app.include_router(social.router, prefix="/social", tags=["social"])
app.include_router(coach.router, prefix="/coach", tags=["coach"])
