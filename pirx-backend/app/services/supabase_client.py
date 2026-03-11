"""Supabase client singleton for backend database operations."""

from functools import lru_cache
from datetime import datetime, timezone

from supabase import Client, create_client

from app.config import settings
from app.services.crypto import encrypt_token, decrypt_token


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
        result = (
            self.client.table("activities")
            .upsert(data, on_conflict="user_id,external_id,source")
            .execute()
        )
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
            .gte("timestamp", since)
            .order("timestamp", desc=True)
            .limit(1000)
            .execute()
        )
        return result.data or []

    def get_activities_since(self, user_id: str, since_iso: str) -> list[dict]:
        result = (
            self.client.table("activities")
            .select("*")
            .eq("user_id", user_id)
            .gte("timestamp", since_iso)
            .order("timestamp", desc=True)
            .limit(1000)
            .execute()
        )
        return result.data or []

    def get_activities_range(
        self, user_id: str, from_iso: str, to_iso: str
    ) -> list[dict]:
        """Get activities between from_iso and to_iso (inclusive)."""
        result = (
            self.client.table("activities")
            .select("*")
            .eq("user_id", user_id)
            .gte("timestamp", from_iso)
            .lte("timestamp", to_iso)
            .order("timestamp", desc=True)
            .limit(1000)
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
            .limit(500)
            .execute()
        )
        return result.data

    def insert_projection(self, data: dict) -> dict:
        result = self.client.table("projection_state").insert(data).execute()
        return result.data[0] if result.data else data

    # --- Driver State ---

    def get_latest_drivers(self, user_id: str, event: str = "5000") -> list[dict]:
        """Get the most recent driver state row for a user and event."""
        query = (
            self.client.table("driver_state")
            .select("*")
            .eq("user_id", user_id)
        )
        if event:
            query = query.eq("event", event)
        result = query.order("computed_at", desc=True).limit(1).execute()
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
            .limit(500)
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
        conns = result.data or []
        for conn in conns:
            if settings.token_encryption_key and conn.get("access_token"):
                conn["access_token"] = decrypt_token(conn["access_token"], settings.token_encryption_key)
            if settings.token_encryption_key and conn.get("refresh_token"):
                conn["refresh_token"] = decrypt_token(conn["refresh_token"], settings.token_encryption_key)
        return conns

    def upsert_wearable_connection(
        self, user_id: str, provider: str, **kwargs
    ) -> dict:
        data = {"user_id": user_id, "provider": provider, **kwargs}
        if settings.token_encryption_key:
            if data.get("access_token"):
                data["access_token"] = encrypt_token(data["access_token"], settings.token_encryption_key)
            if data.get("refresh_token"):
                data["refresh_token"] = encrypt_token(data["refresh_token"], settings.token_encryption_key)
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

    # --- Users (bulk queries) ---

    def get_onboarded_users(self) -> list[dict]:
        result = (
            self.client.table("users")
            .select("user_id, primary_event, baseline_race_date")
            .eq("onboarding_completed", True)
            .limit(5000)
            .execute()
        )
        return result.data or []

    # --- Adjunct State ---

    def get_adjunct_state(self, user_id: str) -> list[dict]:
        result = (
            self.client.table("adjunct_state")
            .select("*")
            .eq("user_id", user_id)
            .order("computed_at", desc=True)
            .limit(200)
            .execute()
        )
        return result.data or []

    # --- Feature History (projection_state + driver_state snapshots) ---

    def get_feature_history(self, user_id: str, limit: int = 6) -> list[dict]:
        """Get recent projection_state rows as feature snapshot proxies."""
        result = (
            self.client.table("projection_state")
            .select("*")
            .eq("user_id", user_id)
            .order("computed_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    # --- Model Metrics ---

    def insert_model_metric(self, data: dict) -> dict:
        result = self.client.table("model_metrics").insert(data).execute()
        return result.data[0] if result.data else data

    # --- Model Lifecycle ---

    def create_model_registry(self, data: dict) -> dict:
        result = self.client.table("model_registry").insert(data).execute()
        return result.data[0] if result.data else data

    def update_model_registry_status(self, model_id: str, status: str) -> dict:
        result = (
            self.client.table("model_registry")
            .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("model_id", model_id)
            .execute()
        )
        return result.data[0] if result.data else {"model_id": model_id, "status": status}

    def get_active_model(self, user_id: str, event: str | None = None) -> dict | None:
        query = (
            self.client.table("model_registry")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "active")
        )
        if event:
            query = query.eq("event", event)
        result = query.order("created_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    def create_model_training_job(self, data: dict) -> dict:
        result = self.client.table("model_training_jobs").insert(data).execute()
        return result.data[0] if result.data else data

    def update_model_training_job(self, job_id: str, status: str, error_message: str | None = None) -> dict:
        payload: dict = {"status": status}
        if status == "running":
            payload["started_at"] = datetime.now(timezone.utc).isoformat()
        elif status in ("completed", "failed", "cancelled"):
            payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        if error_message:
            payload["error_message"] = error_message
        result = (
            self.client.table("model_training_jobs")
            .update(payload)
            .eq("job_id", job_id)
            .execute()
        )
        return result.data[0] if result.data else {"job_id": job_id, **payload}

    def create_optuna_study(self, data: dict) -> dict:
        result = self.client.table("optuna_studies").insert(data).execute()
        return result.data[0] if result.data else data

    def create_optuna_trial(self, data: dict) -> dict:
        result = self.client.table("optuna_trials").insert(data).execute()
        return result.data[0] if result.data else data

    def add_model_artifact(self, data: dict) -> dict:
        result = self.client.table("model_artifacts").insert(data).execute()
        return result.data[0] if result.data else data

    def get_latest_model_artifact(self, model_id: str) -> dict | None:
        result = (
            self.client.table("model_artifacts")
            .select("*")
            .eq("model_id", model_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def insert_injury_risk_assessment(self, data: dict) -> dict:
        result = self.client.table("injury_risk_assessments").insert(data).execute()
        return result.data[0] if result.data else data

    # --- Chat Threads ---

    def create_chat_thread(self, user_id: str, thread_id: str, title: str | None = None) -> dict:
        data = {"thread_id": thread_id, "user_id": user_id, "title": title}
        result = self.client.table("chat_threads").insert(data).execute()
        return result.data[0] if result.data else data

    def get_chat_threads(self, user_id: str) -> list[dict]:
        result = (
            self.client.table("chat_threads")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        )
        return result.data or []

    def get_chat_thread(self, thread_id: str, user_id: str = None) -> dict | None:
        query = (
            self.client.table("chat_threads")
            .select("*")
            .eq("thread_id", thread_id)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        result = query.limit(1).execute()
        return result.data[0] if result.data else None

    def delete_chat_thread(self, thread_id: str, user_id: str = None) -> None:
        query = self.client.table("chat_threads").delete().eq("thread_id", thread_id)
        if user_id:
            query = query.eq("user_id", user_id)
        query.execute()

    def insert_chat_message(self, thread_id: str, role: str, content: str) -> dict:
        data = {"thread_id": thread_id, "role": role, "content": content}
        result = self.client.table("chat_messages").insert(data).execute()
        return result.data[0] if result.data else data

    def get_chat_messages(self, thread_id: str, limit: int = 200) -> list[dict]:
        result = (
            self.client.table("chat_messages")
            .select("*")
            .eq("thread_id", thread_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []
