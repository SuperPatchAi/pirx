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

        avg_hr = hr_data.get("avg_hr_bpm")
        max_hr = hr_data.get("max_hr_bpm")

        activity_type = classify_terra_activity(
            type_code=metadata.get("type", 0),
            name=metadata.get("name", ""),
            pace_sec_per_km=pace,
            avg_hr=avg_hr,
            max_hr=max_hr,
            distance_meters=distance,
            duration_seconds=duration,
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
            avg_hr=avg_hr,
            max_hr=max_hr,
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

    @staticmethod
    def normalize_sleep_entry(terra_sleep: dict) -> dict:
        """Normalize Terra sleep payload into physiology-compatible fields."""
        metadata = terra_sleep.get("metadata", {}) if isinstance(terra_sleep, dict) else {}
        sleep_data = terra_sleep.get("sleep_durations_data", {}) if isinstance(terra_sleep, dict) else {}
        readiness_data = terra_sleep.get("readiness_data", {}) if isinstance(terra_sleep, dict) else {}
        hr_summary = (
            terra_sleep.get("heart_rate_data", {}).get("summary", {})
            if isinstance(terra_sleep.get("heart_rate_data"), dict)
            else {}
        )

        timestamp_raw = (
            terra_sleep.get("end_time")
            or terra_sleep.get("start_time")
            or metadata.get("end_time")
            or metadata.get("start_time")
        )
        try:
            ts = datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00")) if timestamp_raw else datetime.now(timezone.utc)
        except Exception:
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        sleep_score = _first_number(
            terra_sleep,
            [
                ("data_enrichment", "sleep_score"),
                ("sleep_score",),
                ("sleep_data", "sleep_score"),
                ("sleep_data", "score"),
                ("readiness_data", "sleep_score"),
                ("readiness_data", "score"),
                ("scores", "sleep"),
                ("scores", "overall"),
            ],
        )
        resting_hr = _first_number(
            terra_sleep,
            [
                ("heart_rate_data", "summary", "resting_hr_bpm"),
                ("heart_rate_data", "summary", "resting_heart_rate"),
                ("readiness_data", "resting_heart_rate"),
            ],
        )
        hrv = _first_number(
            terra_sleep,
            [
                ("heart_rate_data", "summary", "avg_hrv_sdnn"),
                ("heart_rate_data", "summary", "avg_hrv_rmssd"),
                ("readiness_data", "hrv"),
            ],
        )

        custom_fields = {
            "terra_type": "sleep",
            "summary_id": metadata.get("summary_id"),
            "sleep_total_seconds": _first_number(
                terra_sleep,
                [
                    ("sleep_durations_data", "asleep", "duration_asleep_state_seconds"),
                    ("sleep_durations_data", "total_sleep_duration_seconds"),
                    ("sleep_durations_data", "total_sleep_seconds"),
                ],
            ),
            "sleep_deep_seconds": _first_number(
                terra_sleep,
                [
                    ("sleep_durations_data", "asleep", "duration_deep_sleep_state_seconds"),
                    ("sleep_durations_data", "deep_sleep_duration_seconds"),
                    ("sleep_durations_data", "deep_sleep_seconds"),
                ],
            ),
            "sleep_light_seconds": _first_number(
                terra_sleep,
                [
                    ("sleep_durations_data", "asleep", "duration_light_sleep_state_seconds"),
                    ("sleep_durations_data", "light_sleep_duration_seconds"),
                    ("sleep_durations_data", "light_sleep_seconds"),
                ],
            ),
            "sleep_rem_seconds": _first_number(
                terra_sleep,
                [
                    ("sleep_durations_data", "asleep", "duration_REM_sleep_state_seconds"),
                    ("sleep_durations_data", "rem_sleep_duration_seconds"),
                    ("sleep_durations_data", "rem_sleep_seconds"),
                ],
            ),
            "sleep_awake_seconds": _first_number(
                terra_sleep,
                [
                    ("sleep_durations_data", "awake", "duration_awake_state_seconds"),
                    ("sleep_durations_data", "awake_duration_seconds"),
                    ("sleep_durations_data", "awake_seconds"),
                ],
            ),
            "sleep_efficiency": _first_number(terra_sleep, [("sleep_durations_data", "sleep_efficiency"), ("sleep_data", "efficiency")]),
            "source_provider": (metadata.get("provider") or "terra").lower(),
            "raw_sleep_payload": {
                "sleep_durations_data": sleep_data if isinstance(sleep_data, dict) else {},
                "readiness_data": readiness_data if isinstance(readiness_data, dict) else {},
                "heart_rate_summary": hr_summary if isinstance(hr_summary, dict) else {},
            },
        }

        return {
            "timestamp": ts.isoformat(),
            "source": "wearable",
            "resting_hr": int(resting_hr) if resting_hr is not None else None,
            "hrv": float(hrv) if hrv is not None else None,
            "sleep_score": float(sleep_score) if sleep_score is not None else None,
            "custom_fields": custom_fields,
        }

    @staticmethod
    def normalize_body_entry(terra_body: dict) -> dict:
        """Normalize Terra body payload into physiology-compatible fields."""
        metadata = terra_body.get("metadata", {}) if isinstance(terra_body, dict) else {}
        timestamp_raw = (
            terra_body.get("timestamp")
            or terra_body.get("measurement_time")
            or metadata.get("end_time")
            or metadata.get("start_time")
            or metadata.get("timestamp")
            or metadata.get("measurement_time")
        )
        try:
            ts = datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00")) if timestamp_raw else datetime.now(timezone.utc)
        except Exception:
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        weight_kg = _first_number(
            terra_body,
            [
                ("measurements_data", "weight_kg"),
                ("weight_data", "weight_kg"),
                ("weight_data", "summary", "weight_kg"),
                ("weight",),
            ],
        )
        if weight_kg is None:
            weight_kg = _extract_measurement_value(terra_body, {"weight_kg", "weight"})
        body_fat_pct = _first_number(
            terra_body,
            [
                ("measurements_data", "body_fat_percentage"),
                ("body_composition_data", "body_fat_percentage"),
                ("body_data", "body_fat_percentage"),
            ],
        )
        if body_fat_pct is None:
            body_fat_pct = _extract_measurement_value(
                terra_body,
                {"body_fat_percentage", "body_fat", "body_fat_pct"},
            )
        bmi = _first_number(
            terra_body,
            [
                ("measurements_data", "bmi"),
                ("body_composition_data", "bmi"),
                ("body_data", "bmi"),
            ],
        )
        if bmi is None:
            bmi = _extract_measurement_value(terra_body, {"bmi"})

        custom_fields = {
            "terra_type": "body",
            "weight_kg": float(weight_kg) if weight_kg is not None else None,
            "body_fat_percentage": float(body_fat_pct) if body_fat_pct is not None else None,
            "bmi": float(bmi) if bmi is not None else None,
            "source_provider": (metadata.get("provider") or "terra").lower(),
            "metadata_start_time": metadata.get("start_time"),
            "metadata_end_time": metadata.get("end_time"),
            "raw_body_payload": terra_body,
        }

        return {
            "timestamp": ts.isoformat(),
            "source": "wearable",
            "custom_fields": custom_fields,
        }

    @staticmethod
    def normalize_daily_entry(terra_daily: dict) -> dict:
        """Normalize Terra daily payload into physiology-compatible fields."""
        metadata = terra_daily.get("metadata", {}) if isinstance(terra_daily, dict) else {}
        hr_summary = (
            terra_daily.get("heart_rate_data", {}).get("summary", {})
            if isinstance(terra_daily.get("heart_rate_data"), dict)
            else {}
        )
        scores = terra_daily.get("scores", {}) if isinstance(terra_daily.get("scores"), dict) else {}
        enrichment = (
            terra_daily.get("data_enrichment", {})
            if isinstance(terra_daily.get("data_enrichment"), dict)
            else {}
        )

        timestamp_raw = (
            metadata.get("end_time")
            or metadata.get("start_time")
            or terra_daily.get("timestamp")
        )
        try:
            ts = (
                datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00"))
                if timestamp_raw
                else datetime.now(timezone.utc)
            )
        except Exception:
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        sleep_score = _first_number(
            terra_daily,
            [
                ("scores", "sleep"),
                ("data_enrichment", "readiness_score"),
                ("data_enrichment", "sleep_score"),
            ],
        )
        resting_hr = _first_number(
            terra_daily,
            [
                ("heart_rate_data", "summary", "resting_hr_bpm"),
                ("heart_rate_data", "summary", "min_hr_bpm"),
            ],
        )
        hrv = _first_number(
            terra_daily,
            [
                ("heart_rate_data", "summary", "avg_hrv_sdnn"),
                ("heart_rate_data", "summary", "avg_hrv_rmssd"),
            ],
        )

        # Daily payloads are uniquely keyed by metadata start/end window in Terra docs.
        start_time = metadata.get("start_time")
        end_time = metadata.get("end_time")
        window_key = f"{start_time}|{end_time}" if start_time and end_time else None

        custom_fields = {
            "terra_type": "daily",
            "daily_window_key": window_key,
            "daily_sleep_score": _first_number({"scores": scores}, [("scores", "sleep")]),
            "daily_recovery_score": _first_number(
                {"data_enrichment": enrichment},
                [("data_enrichment", "readiness_score")],
            ),
            "source_provider": (metadata.get("provider") or "terra").lower(),
            "metadata_start_time": start_time,
            "metadata_end_time": end_time,
            "raw_daily_payload": {
                "scores": scores,
                "heart_rate_summary": hr_summary,
                "data_enrichment": enrichment,
            },
        }

        return {
            "timestamp": ts.isoformat(),
            "source": "wearable",
            "resting_hr": int(resting_hr) if resting_hr is not None else None,
            "hrv": float(hrv) if hrv is not None else None,
            "sleep_score": float(sleep_score) if sleep_score is not None else None,
            "custom_fields": custom_fields,
        }


# ---------------------------------------------------------------------------
# Stage 1: Terra type code → sport category (running vs not-running)
# Official Terra ActivityType enum
# Source: https://docs.tryterra.co/reference/health-and-fitness-api/data-models#activitytype
# ---------------------------------------------------------------------------
TERRA_RUNNING_CODES = {8, 56, 57, 58, 133}  # Running, Jogging, Running On Sand, Treadmill Running, Indoor Running
TERRA_CROSS_TRAINING_CODES = {
    1, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44,
    45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 59, 60, 61, 62, 63, 64, 65,
    66, 67, 68, 69, 70, 71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
    85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
    102, 103, 104, 105, 106, 108, 113, 114, 115, 116, 117, 118, 119, 120,
    122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136,
    137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148,
}
TERRA_WALK_HIKE_CODES = {7, 35}  # Walking, Hiking


def _is_running_sport(type_code: int, name: str) -> bool:
    """Determine if the Terra type code represents a running sport."""
    if type_code in TERRA_RUNNING_CODES:
        return True
    if type_code in TERRA_CROSS_TRAINING_CODES or type_code in TERRA_WALK_HIKE_CODES:
        return False
    name_lower = name.lower()
    return any(kw in name_lower for kw in ("run", "running", "jog", "jogging"))


# ---------------------------------------------------------------------------
# Stage 2: Intensity classification for running activities
#
# Terra type codes don't distinguish easy/threshold/interval/race.
# Garmin labels (e.g. "Interval", "Tempo") get flattened by Terra into
# generic type=8 "Running". We classify intensity using:
#   1. Activity name keywords (user-labelled workouts)
#   2. HR intensity (avg_hr as % of estimated max_hr)
#   3. Pace relative to runner profile (short + fast = interval/race)
#   4. Standard race distance matching
# ---------------------------------------------------------------------------

# Distances (meters) that match standard race events (±5% tolerance)
_RACE_DISTANCES = [
    (1400, 1600),    # 1500m / mile
    (2900, 3200),    # 3000m / 2-mile
    (4750, 5250),    # 5K
    (9500, 10500),   # 10K
    (20500, 21700),  # Half marathon
    (41000, 43000),  # Marathon
]


def classify_terra_activity(
    type_code: int,
    name: str = "",
    pace_sec_per_km: float | None = None,
    avg_hr: int | None = None,
    max_hr: int | None = None,
    distance_meters: float = 0,
    duration_seconds: int = 0,
) -> str:
    """Two-stage classifier: sport detection then intensity classification.

    Stage 1 uses Terra type codes to separate running from cross-training.
    Stage 2 uses name keywords, HR, pace, and distance to classify running
    intensity into easy / threshold / interval / race.
    """
    if not _is_running_sport(type_code, name):
        return "cross-training"

    # --- Name-based overrides (highest priority for labelled workouts) ---
    name_lower = name.lower()

    race_keywords = [
        "race", "competition", "parkrun", "park run",
        "5k race", "10k race", "half marathon", "marathon",
        "garmin race", "time trial",
    ]
    if any(kw in name_lower for kw in race_keywords):
        return "race"

    interval_keywords = [
        "interval", "tempo", "threshold", "speed", "fartlek", "track",
        "repeat", "vo2", "v02",
    ]
    if any(kw in name_lower for kw in interval_keywords):
        return "interval"

    recovery_keywords = ["recovery", "warm up", "warmup", "cool down", "cooldown", "shake"]
    if any(kw in name_lower for kw in recovery_keywords):
        return "easy"

    # --- HR-based intensity detection ---
    # Estimate max HR if not provided (220 - age fallback: assume ~190 for adult runner)
    estimated_max = max_hr if max_hr and max_hr > 150 else 190
    hr_pct = (avg_hr / estimated_max) if avg_hr and estimated_max > 0 else None

    # --- Race detection: standard distance + high intensity ---
    if distance_meters > 0 and hr_pct is not None:
        is_race_distance = any(lo <= distance_meters <= hi for lo, hi in _RACE_DISTANCES)
        if is_race_distance and hr_pct >= 0.83:
            return "race"

    # --- Intensity zones based on HR percentage of max ---
    # Zone 5 (>90%): interval / race-pace
    # Zone 4 (82-90%): threshold / tempo
    # Zone 3 (72-82%): moderate / steady
    # Zone 1-2 (<72%): easy
    if hr_pct is not None:
        if hr_pct >= 0.90:
            if distance_meters > 0 and distance_meters <= 3200 and (duration_seconds or 0) < 1200:
                return "interval"
            return "interval"
        if hr_pct >= 0.82:
            return "threshold"

    # --- Pace-based fallback when HR is unavailable ---
    # Short + fast relative to what would be sustainable = likely interval
    if pace_sec_per_km and pace_sec_per_km < 240 and distance_meters <= 5000:
        return "interval"

    return "easy"


def classify_terra_type(type_code: int, name: str = "") -> str:
    """Legacy wrapper — delegates to classify_terra_activity without HR/pace data.

    Kept for backward compatibility with existing callers and tests.
    """
    return classify_terra_activity(type_code=type_code, name=name)


def extract_hr_zones(terra_activity: dict) -> Optional[list[float]]:
    """Extract HR zone distribution from Terra activity data."""
    hr_data = terra_activity.get("heart_rate_data", {})
    hr_zones = hr_data.get("hr_zones")
    if not hr_zones:
        return None
    if isinstance(hr_zones, list) and len(hr_zones) > 0:
        return [float(z.get("duration_seconds", 0)) for z in hr_zones]
    return None


def _first_number(payload: dict, paths: list[tuple[str, ...]]) -> Optional[float]:
    """Return first numeric value found at any nested key path."""
    for path in paths:
        cursor = payload
        try:
            for key in path:
                if not isinstance(cursor, dict):
                    cursor = None
                    break
                cursor = cursor.get(key)
            if isinstance(cursor, (int, float)):
                return float(cursor)
            if isinstance(cursor, str):
                value = float(cursor)
                return value
        except Exception:
            continue
    return None


def _extract_measurement_value(payload: dict, keys: set[str]) -> Optional[float]:
    """Extract metric from Terra measurements arrays using flexible shapes."""
    measurements_data = payload.get("measurements_data")
    if not isinstance(measurements_data, dict):
        return None
    measurements = measurements_data.get("measurements")
    if not isinstance(measurements, list):
        return None

    normalized_keys = {k.lower() for k in keys}
    for row in measurements:
        if not isinstance(row, dict):
            continue

        # Pattern A: {"measurement_type": "weight_kg", "value": 70.2}
        m_type = row.get("measurement_type")
        if isinstance(m_type, str) and m_type.lower() in normalized_keys:
            value = row.get("value")
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except Exception:
                    pass

        # Pattern B: {"weight_kg": 70.2} or similar key-value rows
        for key in normalized_keys:
            value = row.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except Exception:
                    pass
    return None
