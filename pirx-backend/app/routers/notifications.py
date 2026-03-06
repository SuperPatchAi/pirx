from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.notification_service import TRIGGER_TYPES, NotificationService
from app.services.supabase_client import SupabaseService

router = APIRouter()


class NotificationResponse(BaseModel):
    id: str | None = None
    notification_type: str
    title: str
    body: str
    delivered_at: str | None = None
    read_at: str | None = None
    deep_link: str | None = None


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict


@router.post("/subscribe")
async def subscribe_push(
    body: PushSubscription, user: dict = Depends(get_current_user)
):
    db = SupabaseService()
    try:
        db.client.table("push_subscriptions").upsert(
            {
                "user_id": user["user_id"],
                "endpoint": body.endpoint,
                "p256dh": body.keys.get("p256dh", ""),
                "auth": body.keys.get("auth", ""),
            }
        ).execute()
        return {"status": "subscribed"}
    except Exception:
        return {"status": "error"}


@router.post("/unsubscribe")
async def unsubscribe_push(
    body: PushSubscription, user: dict = Depends(get_current_user)
):
    db = SupabaseService()
    try:
        db.client.table("push_subscriptions").delete().eq(
            "user_id", user["user_id"]
        ).eq("endpoint", body.endpoint).execute()
        return {"status": "unsubscribed"}
    except Exception:
        return {"status": "error"}


@router.get("", response_model=NotificationsListResponse)
async def get_notifications(
    limit: int = Query(default=20, le=50),
    user: dict = Depends(get_current_user),
):
    """Get recent notifications for the current user."""
    svc = NotificationService()
    notifications = svc.get_user_notifications(user["user_id"], limit)
    unread = sum(1 for n in notifications if n.get("read_at") is None)
    return NotificationsListResponse(
        notifications=[
            NotificationResponse(
                **{k: n.get(k) for k in NotificationResponse.model_fields}
            )
            for n in notifications
        ],
        unread_count=unread,
    )


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
):
    """Mark a notification as read."""
    svc = NotificationService()
    svc.db.client.table("notification_log").update(
        {"read_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", notification_id).eq("user_id", user["user_id"]).execute()
    return {"status": "ok"}


@router.get("/triggers")
async def get_trigger_types(user: dict = Depends(get_current_user)):
    """Get available notification trigger types."""
    return {"triggers": TRIGGER_TYPES}
