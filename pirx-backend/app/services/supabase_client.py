"""Supabase client singleton for backend database operations."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get or create the Supabase client singleton.

    Uses the service role key for server-side operations (bypasses RLS).
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class SupabaseService:
    """Database operations wrapper for PIRX."""

    def __init__(self):
        self.client = get_supabase_client()

    # --- Users ---

    def get_user(self, user_id: str) -> dict | None:
        result = (
            self.client.table("users")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def upsert_user(self, user_id: str, email: str, **kwargs) -> dict:
        data = {"user_id": user_id, "email": email, **kwargs}
        result = (
            self.client.table("users")
            .upsert(data, on_conflict="user_id")
            .execute()
        )
        return result.data[0] if result.data else data

    # --- Activities ---

    def insert_activity(self, user_id: str, activity_data: dict) -> dict:
        data = {"user_id": user_id, **activity_data}
        result = self.client.table("activities").insert(data).execute()
        return result.data[0] if result.data else data

    def get_activities(
        self, user_id: str, limit: int = 200, days: int = 90
    ) -> list[dict]:
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            self.client.table("activities")
            .select("*")
            .eq("user_id", user_id)
            .gte("timestamp", cutoff)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    def get_recent_activities(self, user_id: str, days: int = 90) -> list[dict]:
        from datetime import datetime, timezone, timedelta

        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            self.client.table("activities")
            .select("*")
            .eq("user_id", user_id)
            .gte("started_at", since)
            .order("started_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_race_activities(self, user_id: str) -> list[dict]:
        result = (
            self.client.table("activities")
            .select("*")
            .eq("user_id", user_id)
            .eq("activity_type", "race")
            .order("timestamp", desc=True)
            .limit(20)
            .execute()
        )
        return result.data

    # --- Projection State ---

    def get_latest_projection(self, user_id: str, event: str) -> dict | None:
        result = (
            self.client.table("projection_state")
            .select("*")
            .eq("user_id", user_id)
            .eq("event", event)
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_projection_history(
        self, user_id: str, event: str, days: int = 90
    ) -> list[dict]:
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            self.client.table("projection_state")
            .select("*")
            .eq("user_id", user_id)
            .eq("event", event)
            .gte("computed_at", cutoff)
            .order("computed_at", desc=True)
            .execute()
        )
        return result.data

    def insert_projection(self, data: dict) -> dict:
        result = self.client.table("projection_state").insert(data).execute()
        return result.data[0] if result.data else data

    # --- Driver State ---

    def get_latest_drivers(self, user_id: str) -> list[dict]:
        """Get the most recent driver state row for a user.

        All 5 drivers are stored in one row, so we just need the latest.
        """
        result = (
            self.client.table("driver_state")
            .select("*")
            .eq("user_id", user_id)
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data

    def get_driver_history(self, user_id: str, days: int = 42) -> list[dict]:
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            self.client.table("driver_state")
            .select("*")
            .eq("user_id", user_id)
            .gte("computed_at", cutoff)
            .order("computed_at", desc=True)
            .execute()
        )
        return result.data

    def insert_driver_state(self, data: dict) -> dict:
        result = self.client.table("driver_state").insert(data).execute()
        return result.data[0] if result.data else data

    # --- Wearable Connections ---

    def get_wearable_connections(self, user_id: str) -> list[dict]:
        result = (
            self.client.table("wearable_connections")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data

    def upsert_wearable_connection(
        self, user_id: str, provider: str, **kwargs
    ) -> dict:
        data = {"user_id": user_id, "provider": provider, **kwargs}
        result = (
            self.client.table("wearable_connections")
            .upsert(data, on_conflict="user_id,provider")
            .execute()
        )
        return result.data[0] if result.data else data

    # --- Physiology ---

    def get_recent_physiology(self, user_id: str, limit: int = 30) -> list[dict]:
        result = (
            self.client.table("physiology")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # --- Notification Log ---

    def insert_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        deep_link: str = None,
    ) -> dict:
        data = {
            "user_id": user_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "deep_link": deep_link,
        }
        result = self.client.table("notification_log").insert(data).execute()
        return result.data[0] if result.data else data

    # --- Task Registry ---

    def register_task(self, user_id: str, task_name: str, task_id: str) -> dict:
        data = {
            "user_id": user_id,
            "task_name": task_name,
            "task_id": task_id,
            "status": "queued",
        }
        result = self.client.table("task_registry").insert(data).execute()
        return result.data[0] if result.data else data

    def update_task_status(
        self, task_id: str, status: str, error_message: str = None
    ) -> dict:
        from datetime import datetime, timezone

        data = {"status": status}
        if status == "running":
            data["started_at"] = datetime.now(timezone.utc).isoformat()
        elif status in ("completed", "failed"):
            data["completed_at"] = datetime.now(timezone.utc).isoformat()
        if error_message:
            data["error_message"] = error_message
        result = (
            self.client.table("task_registry")
            .update(data)
            .eq("task_id", task_id)
            .execute()
        )
        return result.data[0] if result.data else data
