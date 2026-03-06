import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import settings
from app.dependencies import get_current_user
from app.models.sync import ConnectRequest, ConnectResponse, StravaWebhookEvent
from app.services.supabase_client import SupabaseService
from app.models.terra import TerraWebhookPayload, TerraWidgetRequest
from app.services.strava_service import StravaService
from app.services.terra_service import TerraService
from app.services.cleaning_service import CleaningService

logger = logging.getLogger(__name__)

router = APIRouter()
strava_service = StravaService()
terra_service = TerraService()


@router.get("/status")
async def get_sync_status(user: dict = Depends(get_current_user)):
    """Get wearable connection status for the current user."""
    try:
        db = SupabaseService()
        connections = db.get_wearable_connections(user["user_id"])
        return {
            "connections": [
                {
                    "provider": c.get("provider", "unknown"),
                    "connected": c.get("is_active", False),
                    "last_sync": c.get("last_sync_at"),
                }
                for c in connections
            ]
        }
    except Exception:
        return {"connections": []}


@router.get("/connect/strava")
async def get_strava_auth_url(
    redirect_uri: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Get Strava OAuth authorization URL."""
    url = strava_service.get_authorization_url(redirect_uri, state=user["user_id"])
    return {"authorization_url": url}


@router.post("/connect/strava")
async def connect_strava(
    body: ConnectRequest,
    user: dict = Depends(get_current_user),
):
    """Exchange Strava auth code for tokens and store connection."""
    try:
        token_data = await strava_service.exchange_token(body.code)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Strava token exchange failed: {str(e)}"
        )

    athlete = token_data.get("athlete", {})
    db = SupabaseService()

    try:
        db.client.table("wearable_connections").upsert(
            {
                "user_id": user["user_id"],
                "provider": "strava",
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "token_expires_at": token_data.get("expires_at"),
                "athlete_id": str(athlete.get("id", "")),
                "is_active": True,
            },
            on_conflict="user_id,provider",
        ).execute()
    except Exception:
        logger.exception("Failed to store Strava tokens for user %s", user["user_id"])

    try:
        from app.tasks.sync_tasks import backfill_history
        backfill_history.delay(user["user_id"], "strava")
    except Exception:
        logger.warning("Could not queue backfill for user %s", user["user_id"])

    return ConnectResponse(
        provider="strava",
        status="connected",
        athlete_name=f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
        or None,
    )


@router.post("/disconnect/{provider}")
async def disconnect_wearable(
    provider: str, user: dict = Depends(get_current_user)
):
    """Disconnect wearable and revoke tokens."""
    db = SupabaseService()
    try:
        db.client.table("wearable_connections").update(
            {"is_active": False, "sync_status": "disconnected"}
        ).eq("user_id", user["user_id"]).eq("provider", provider).execute()
    except Exception:
        logger.exception("Failed to disconnect %s for user %s", provider, user["user_id"])

    if provider == "strava":
        try:
            connections = db.get_wearable_connections(user["user_id"])
            strava_conn = next((c for c in connections if c.get("provider") == "strava"), None)
            if strava_conn and strava_conn.get("access_token"):
                import httpx
                httpx.post(
                    "https://www.strava.com/oauth/deauthorize",
                    params={"access_token": strava_conn["access_token"]},
                    timeout=10,
                )
        except Exception:
            logger.warning("Could not revoke Strava token for user %s", user["user_id"])

    return {"provider": provider, "status": "disconnected"}


@router.get("/webhook/strava")
async def strava_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Handle Strava webhook subscription verification."""
    if (
        hub_mode == "subscribe"
        and hub_verify_token == settings.strava_webhook_verify_token
    ):
        return {"hub.challenge": hub_challenge}
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/strava")
async def strava_webhook_receive(request: Request):
    """Handle incoming Strava webhook events. Must respond within 2 seconds."""
    payload = await request.json()
    event = StravaWebhookEvent(**payload)

    if event.object_type == "activity" and event.aspect_type == "create":
        try:
            from app.tasks.sync_tasks import process_activity
            process_activity.delay(
                str(event.owner_id),
                {"activity_id": event.object_id},
                "strava",
            )
        except Exception:
            logger.exception(
                "Failed to queue Strava activity %s for owner %s",
                event.object_id,
                event.owner_id,
            )

    return {"status": "ok"}


@router.post("/webhook/terra")
async def terra_webhook(request: Request):
    """Receive Terra API webhook for new activity data."""
    body = await request.body()
    signature = request.headers.get("terra-signature", "")
    if not TerraService.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    payload = TerraWebhookPayload(**(await request.json()))

    if payload.type == "auth" and payload.status == "success" and payload.user:
        logger.info(
            "Terra auth success: terra_user=%s provider=%s pirx_user=%s",
            payload.user.user_id,
            payload.user.provider,
            payload.user.reference_id,
        )
        if payload.user.reference_id:
            try:
                db = SupabaseService()
                db.client.table("wearable_connections").upsert(
                    {
                        "user_id": payload.user.reference_id,
                        "provider": payload.user.provider or "terra",
                        "terra_user_id": payload.user.user_id,
                        "is_active": True,
                    },
                    on_conflict="user_id,provider",
                ).execute()
            except Exception:
                logger.exception("Failed to store Terra connection")

    elif payload.type == "activity" and payload.data:
        normalized = []
        for activity_data in payload.data:
            try:
                normalized.append(TerraService.normalize_activity(activity_data))
            except Exception:
                logger.exception("Failed to normalize Terra activity")
        logger.info("Normalized %d Terra activities", len(normalized))

        if normalized and payload.user and payload.user.reference_id:
            user_id = payload.user.reference_id
            db = SupabaseService()
            for raw_act, activity in zip(payload.data, normalized):
                try:
                    cleaned = CleaningService.clean_activity(activity)
                    if cleaned and cleaned.duration_seconds and cleaned.duration_seconds >= 60:
                        db.insert_activity(user_id, {
                            "source": cleaned.source or "terra",
                            "external_id": str(raw_act.get("id", "")),
                            "timestamp": cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat(),
                            "started_at": cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat(),
                            "duration_seconds": cleaned.duration_seconds,
                            "distance_meters": cleaned.distance_meters,
                            "avg_hr": cleaned.avg_hr,
                            "max_hr": cleaned.max_hr,
                            "avg_pace_sec_per_km": cleaned.avg_pace_sec_per_km,
                            "elevation_gain_m": cleaned.elevation_gain_m,
                            "calories": cleaned.calories,
                            "activity_type": cleaned.activity_type,
                            "hr_zones": cleaned.hr_zones,
                        })
                except Exception:
                    logger.exception("Failed to insert Terra activity for user %s", user_id)

            try:
                from app.tasks.feature_engineering import compute_features
                compute_features.delay(user_id)
            except Exception:
                logger.exception("Failed to queue feature engineering for user %s", user_id)

    return {"status": "ok"}


@router.post("/connect/terra/widget")
async def connect_terra_widget(
    body: TerraWidgetRequest,
    user: dict = Depends(get_current_user),
):
    """Generate a Terra widget session for user to connect a wearable."""
    try:
        result = await terra_service.generate_widget_session(
            user_id=user["user_id"],
            redirect_url=body.redirect_url,
            failure_redirect_url=body.failure_redirect_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Terra widget session failed: {e}"
        )
    return result


TERRA_PROVIDERS = {"garmin", "apple_health", "fitbit", "suunto", "coros", "whoop", "oura", "polar"}


@router.post("/connect/{provider}")
async def connect_wearable_generic(
    provider: str, user: dict = Depends(get_current_user)
):
    """Connect a wearable via Terra widget session."""
    if provider == "strava":
        raise HTTPException(status_code=400, detail="Use /sync/connect/strava for Strava connections")

    if provider not in TERRA_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}'. Supported: {', '.join(sorted(TERRA_PROVIDERS))}",
        )

    try:
        result = await terra_service.generate_widget_session(
            user_id=user["user_id"],
            redirect_url=f"{settings.api_url or 'http://localhost:3000'}/settings?connected={provider}",
            failure_redirect_url=f"{settings.api_url or 'http://localhost:3000'}/settings?error={provider}",
        )
        return {"provider": provider, "widget_url": result.get("url"), "status": "widget_session_created"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to create {provider} connection session: {e}")


@router.post("/trigger")
async def trigger_sync(user: dict = Depends(get_current_user)):
    """Trigger a manual sync for the user's connected wearables."""
    try:
        from app.tasks.sync_tasks import backfill_history
        db = SupabaseService()
        connections = db.get_wearable_connections(user["user_id"])
        active = [c for c in connections if c.get("is_active")]
        for conn in active:
            provider = conn.get("provider", "strava")
            backfill_history.delay(user["user_id"], provider)
        return {"status": "sync_triggered", "providers": [c.get("provider") for c in active]}
    except Exception:
        return {"status": "sync_triggered", "providers": []}


@router.post("/backfill")
async def trigger_backfill(user: dict = Depends(get_current_user)):
    """Trigger historical data backfill for a user."""
    from app.tasks.sync_tasks import backfill_history
    db = SupabaseService()
    connections = db.get_wearable_connections(user["user_id"])
    active = [c for c in connections if c.get("is_active")]
    providers_queued = []
    for conn in active:
        provider = conn.get("provider", "strava")
        backfill_history.delay(user["user_id"], provider)
        providers_queued.append(provider)
    return {"message": "Backfill queued", "user_id": user["user_id"], "providers": providers_queued}
