import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.models.activities import NormalizedActivity

logger = logging.getLogger(__name__)

TERRA_API_BASE = "https://api.tryterra.co/v2"


class TerraService:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    @property
    def headers(self) -> dict:
        return {
            "x-api-key": settings.terra_api_key,
            "dev-id": settings.terra_dev_id,
            "Content-Type": "application/json",
        }

    async def generate_widget_session(
        self,
        user_id: str,
        redirect_url: str,
        failure_redirect_url: Optional[str] = None,
    ) -> dict:
        """Generate a Terra widget session for user to connect their wearable."""
        body = {
            "reference_id": user_id,
            "providers": "GARMIN,FITBIT,SUUNTO,COROS,WHOOP,OURA,POLAR",
            "auth_success_redirect_url": redirect_url,
            "auth_failure_redirect_url": failure_redirect_url or redirect_url,
            "language": "en",
        }
        response = await self.client.post(
            f"{TERRA_API_BASE}/auth/generateWidgetSession",
            headers=self.headers,
            json=body,
        )
        response.raise_for_status()
        return response.json()

    async def get_activity_data(
        self,
        terra_user_id: str,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """Fetch historical activity data for a Terra user."""
        params = {"user_id": terra_user_id, "start_date": start_date}
        if end_date:
            params["end_date"] = end_date
        response = await self.client.get(
            f"{TERRA_API_BASE}/activity",
            headers=self.headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def deauthenticate_user(self, terra_user_id: str) -> bool:
        """Remove a user's wearable connection via Terra."""
        response = await self.client.delete(
            f"{TERRA_API_BASE}/auth/deauthenticateUser",
            headers=self.headers,
            params={"user_id": terra_user_id},
        )
        return response.status_code == 200

    @staticmethod
    def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
        """Verify Terra webhook signature using HMAC-SHA256.

        Terra sends signatures in the format: t=<timestamp>,v1=<hex_hash>
        The signed payload is: <raw_body>.<timestamp>
        """
        if not settings.terra_webhook_secret:
            logger.warning("TERRA_WEBHOOK_SECRET not set — skipping signature check")
            return True
        try:
            parts = dict(p.split("=", 1) for p in signature.split(",") if "=" in p)
            timestamp = parts.get("t", "")
            v1_hash = parts.get("v1", "")
            if not timestamp or not v1_hash:
                logger.warning(
                    "Webhook signature missing t or v1: sig=%s",
                    signature[:80],
                )
                return False
            signed_payload = payload_body + b"." + timestamp.encode()
            expected = hmac.new(
                settings.terra_webhook_secret.encode(),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()
            match = hmac.compare_digest(expected, v1_hash)
            if not match:
                logger.warning(
                    "Webhook signature mismatch: expected=%s got=%s secret_len=%d body_len=%d",
                    expected[:16] + "...",
                    v1_hash[:16] + "...",
                    len(settings.terra_webhook_secret),
                    len(payload_body),
                )
            return match
        except Exception:
            logger.exception("Failed to verify Terra webhook signature")
            return False

    @staticmethod
    def normalize_activity(terra_activity: dict) -> NormalizedActivity:
        """Convert a Terra activity to PIRX normalized format."""
        metadata = terra_activity.get("metadata", {})
        duration_data = terra_activity.get("active_durations_data", {})
        distance_data = terra_activity.get("distance_data", {}).get("summary", {})
        hr_data = terra_activity.get("heart_rate_data", {}).get("summary", {})
        calories_data = terra_activity.get("calories_data", {})

        duration = int(duration_data.get("activity_seconds", 0))
        distance = float(distance_data.get("distance_meters", 0))
        pace = (duration / (distance / 1000)) if distance > 0 else None

        activity_type = classify_terra_type(
            metadata.get("type", 0), metadata.get("name", "")
        )
        provider = metadata.get("provider", "unknown").lower()

        start_time = terra_activity.get("start_time") or metadata.get("start_time")

        return NormalizedActivity(
            source=provider,
            timestamp=(
                datetime.fromisoformat(start_time)
                if start_time
                else datetime.now(timezone.utc)
            ),
            duration_seconds=duration,
            distance_meters=distance,
            avg_hr=hr_data.get("avg_hr_bpm"),
            max_hr=hr_data.get("max_hr_bpm"),
            avg_pace_sec_per_km=pace,
            elevation_gain_m=(
                distance_data.get("elevation", {}).get("gain_actual_meters")
                if isinstance(distance_data.get("elevation"), dict)
                else None
            ),
            calories=(
                int(calories_data.get("total_burned_calories", 0))
                if calories_data.get("total_burned_calories")
                else None
            ),
            activity_type=activity_type,
            hr_zones=extract_hr_zones(terra_activity),
            laps=None,
            fit_file_url=None,
        )


def classify_terra_type(type_code: int, name: str = "") -> str:
    """Map Terra activity type code to PIRX activity type.

    Terra type codes: 0=unknown, 1=running, 2=cycling, 4=swimming,
    8=walking, 9=hiking, 12=trail_running, 83=virtual_run, etc.
    """
    running_types = {1, 12, 83}
    race_keywords = ["race", "competition", "parkrun"]
    interval_keywords = ["interval", "tempo", "threshold", "speed", "fartlek", "track"]

    name_lower = name.lower()

    if any(kw in name_lower for kw in race_keywords):
        return "race"
    if any(kw in name_lower for kw in interval_keywords):
        return "interval"
    if type_code in running_types:
        return "easy"
    return "cross-training"


def extract_hr_zones(terra_activity: dict) -> Optional[list[float]]:
    """Extract HR zone distribution from Terra activity data."""
    hr_data = terra_activity.get("heart_rate_data", {})
    hr_zones = hr_data.get("hr_zones")
    if not hr_zones:
        return None
    if isinstance(hr_zones, list) and len(hr_zones) > 0:
        return [float(z.get("duration_seconds", 0)) for z in hr_zones]
    return None
