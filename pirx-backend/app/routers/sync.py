import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import settings
from app.dependencies import get_current_user
from app.models.sync import ConnectRequest, ConnectResponse, StravaWebhookEvent
from app.services.supabase_client import SupabaseService
from app.models.terra import TerraWebhookPayload, TerraWidgetRequest
from app.services.strava_service import StravaService
from app.services.terra_service import TerraService

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
    # TODO: Delete from wearable_connections, revoke token at provider
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
                "strava",
                {"activity_id": event.object_id},
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
            for activity in normalized:
                try:
                    db.insert_activity({
                        "user_id": user_id,
                        "source": activity.source,
                        "started_at": activity.timestamp.isoformat(),
                        "duration_seconds": activity.duration_seconds,
                        "distance_meters": activity.distance_meters,
                        "avg_hr": activity.avg_hr,
                        "max_hr": activity.max_hr,
                        "avg_pace_sec_per_km": activity.avg_pace_sec_per_km,
                        "elevation_gain_m": activity.elevation_gain_m,
                        "activity_type": activity.activity_type,
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


@router.post("/connect/{provider}")
async def connect_wearable_generic(
    provider: str, user: dict = Depends(get_current_user)
):
    """Generic wearable connection for Terra-based providers."""
    # TODO: Implement per-provider connection logic
    return {"message": "Not implemented", "provider": provider}


@router.post("/backfill")
async def trigger_backfill(user: dict = Depends(get_current_user)):
    """Trigger historical data backfill for a user."""
    # TODO: Queue Celery wearable_backfill task
    return {"message": "Backfill queued", "user_id": user["user_id"]}
