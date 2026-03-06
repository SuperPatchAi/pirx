import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import settings
from app.dependencies import get_current_user
from app.models.sync import ConnectRequest, ConnectResponse, StravaWebhookEvent
from app.models.terra import TerraWebhookPayload, TerraWidgetRequest
from app.services.strava_service import StravaService
from app.services.terra_service import TerraService

logger = logging.getLogger(__name__)

router = APIRouter()
strava_service = StravaService()
terra_service = TerraService()


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
    # TODO: Store tokens in wearable_connections table (encrypted)
    # TODO: Queue backfill task

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
        # TODO: Queue Celery task to fetch full activity and process
        pass

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
        # TODO: Store terra_user_id in wearable_connections table

    elif payload.type == "activity" and payload.data:
        normalized = []
        for activity_data in payload.data:
            try:
                normalized.append(TerraService.normalize_activity(activity_data))
            except Exception:
                logger.exception("Failed to normalize Terra activity")
        logger.info("Normalized %d Terra activities", len(normalized))
        # TODO: Store normalized activities in activities table
        # TODO: Queue feature engineering task

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
