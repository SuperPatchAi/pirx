import httpx
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models.activities import NormalizedActivity

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaService:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Build Strava OAuth authorization URL."""
        params = {
            "client_id": settings.strava_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "activity:read_all",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{STRAVA_AUTH_URL}?{query}"

    async def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access + refresh tokens."""
        response = await self.client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        response = await self.client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_activity(self, access_token: str, activity_id: int) -> dict:
        """Fetch a single activity from Strava API."""
        response = await self.client.get(
            f"{STRAVA_API_BASE}/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def get_activities(
        self,
        access_token: str,
        after: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[dict]:
        """Fetch multiple activities for backfill."""
        params: dict = {"page": page, "per_page": per_page}
        if after:
            params["after"] = after
        response = await self.client.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def normalize_activity(strava_activity: dict) -> NormalizedActivity:
        """Convert a Strava activity to PIRX normalized format."""
        activity_type = classify_strava_type(strava_activity.get("type", "Run"))

        distance = strava_activity.get("distance", 0)
        duration = strava_activity.get("moving_time", 0)
        pace = (duration / (distance / 1000)) if distance > 0 else None

        return NormalizedActivity(
            source="strava",
            timestamp=datetime.fromisoformat(
                strava_activity["start_date"].replace("Z", "+00:00")
            ),
            duration_seconds=duration,
            distance_meters=distance,
            avg_hr=strava_activity.get("average_heartrate"),
            max_hr=strava_activity.get("max_heartrate"),
            avg_pace_sec_per_km=pace,
            elevation_gain_m=strava_activity.get("total_elevation_gain"),
            calories=strava_activity.get("calories"),
            activity_type=activity_type,
            hr_zones=None,
            laps=normalize_strava_laps(strava_activity.get("laps")),
            fit_file_url=None,
        )


def classify_strava_type(strava_type: str) -> str:
    """Map Strava activity type to PIRX activity type."""
    type_map = {
        "Run": "easy",
        "TrailRun": "easy",
        "VirtualRun": "easy",
        "Race": "race",
        "Workout": "interval",
        "Walk": "cross-training",
        "Hike": "cross-training",
        "Ride": "cross-training",
        "VirtualRide": "cross-training",
        "Swim": "cross-training",
        "WeightTraining": "cross-training",
        "Yoga": "cross-training",
    }
    return type_map.get(strava_type, "cross-training")


def normalize_strava_laps(laps: Optional[list]) -> Optional[list[dict]]:
    """Normalize Strava lap data."""
    if not laps:
        return None
    return [
        {
            "duration_seconds": lap.get("moving_time", 0),
            "distance_meters": lap.get("distance", 0),
            "avg_pace_sec_per_km": (
                (lap.get("moving_time", 0) / (lap.get("distance", 0) / 1000))
                if lap.get("distance", 0) > 0
                else None
            ),
            "avg_hr": lap.get("average_heartrate"),
        }
        for lap in laps
    ]
