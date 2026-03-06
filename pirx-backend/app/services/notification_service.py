"""Notification service for triggering and managing push notifications.

Handles evaluation of notification triggers, user preference checking,
and dispatching notifications to the notification_log (and future push delivery).
"""

from dataclasses import dataclass
from typing import Optional

from app.services.supabase_client import SupabaseService

TRIGGER_TYPES = [
    "projection_update",
    "readiness_shift",
    "intervention",
    "weekly_summary",
    "race_approaching",
    "new_insight",
]

TRIGGER_THRESHOLDS = {
    "projection_update": 2.0,
    "readiness_shift": 5.0,
    "intervention": 1.5,
}

DEEP_LINKS = {
    "projection_update": "/event/{event}",
    "readiness_shift": "/dashboard",
    "intervention": "/dashboard",
    "weekly_summary": "/performance",
    "race_approaching": "/event/{event}",
    "new_insight": "/driver/{driver}",
}


@dataclass
class NotificationPayload:
    notification_type: str
    title: str
    body: str
    deep_link: str


class NotificationService:
    """Evaluates notification triggers and dispatches notifications."""

    def __init__(self):
        self.db = SupabaseService()

    def check_projection_update(
        self,
        user_id: str,
        event: str,
        old_time_s: float,
        new_time_s: float,
    ) -> Optional[NotificationPayload]:
        delta = old_time_s - new_time_s
        abs_delta = abs(delta)

        if abs_delta < TRIGGER_THRESHOLDS["projection_update"]:
            return None

        direction = "faster" if delta > 0 else "slower"
        mins = int(abs_delta) // 60
        secs = round(abs_delta % 60)
        time_str = f"{mins}:{secs:02d}" if mins > 0 else f"{secs}s"

        return NotificationPayload(
            notification_type="projection_update",
            title="Projection Updated",
            body=f"Your {event}m projection moved {time_str} {direction}",
            deep_link=DEEP_LINKS["projection_update"].format(event=event),
        )

    def check_readiness_shift(
        self,
        user_id: str,
        old_score: float,
        new_score: float,
    ) -> Optional[NotificationPayload]:
        delta = abs(new_score - old_score)

        if delta < TRIGGER_THRESHOLDS["readiness_shift"]:
            return None

        direction = "improved" if new_score > old_score else "declined"
        return NotificationPayload(
            notification_type="readiness_shift",
            title="Readiness Shift",
            body=f"Your readiness {direction} to {new_score:.0f}/100",
            deep_link=DEEP_LINKS["readiness_shift"],
        )

    def check_intervention(
        self,
        user_id: str,
        acwr: float,
    ) -> Optional[NotificationPayload]:
        if acwr < TRIGGER_THRESHOLDS["intervention"]:
            return None

        return NotificationPayload(
            notification_type="intervention",
            title="Training Load Alert",
            body=f"ACWR is {acwr:.2f} — consider reducing intensity this week",
            deep_link=DEEP_LINKS["intervention"],
        )

    def build_weekly_summary(
        self,
        user_id: str,
        weekly_km: float,
        sessions: int,
        projection_change_s: float,
        event: str = "5000",
    ) -> NotificationPayload:
        direction = (
            "faster"
            if projection_change_s > 0
            else "slower" if projection_change_s < 0 else "unchanged"
        )
        return NotificationPayload(
            notification_type="weekly_summary",
            title="Weekly Summary",
            body=f"{sessions} sessions, {weekly_km:.0f}km — projection {direction}",
            deep_link=DEEP_LINKS["weekly_summary"],
        )

    def build_race_approaching(
        self,
        user_id: str,
        event: str,
        days_until: int,
    ) -> NotificationPayload:
        return NotificationPayload(
            notification_type="race_approaching",
            title="Race Approaching",
            body=f"Your {event}m race is {days_until} days away",
            deep_link=DEEP_LINKS["race_approaching"].format(event=event),
        )

    def dispatch(self, user_id: str, payload: NotificationPayload) -> dict:
        """Store notification in log and (future) trigger push delivery."""
        result = self.db.insert_notification(
            user_id=user_id,
            notification_type=payload.notification_type,
            title=payload.title,
            body=payload.body,
            deep_link=payload.deep_link,
        )
        # TODO: Trigger actual push notification via web-push
        return result

    def get_user_notifications(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get recent notifications for a user."""
        result = (
            self.db.client.table("notification_log")
            .select("*")
            .eq("user_id", user_id)
            .order("delivered_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
