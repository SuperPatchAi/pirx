import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from app.services.strava_service import (
    StravaService,
    classify_strava_type,
    normalize_strava_laps,
)


# ---------------------------------------------------------------------------
# Unit Tests — classify_strava_type
# ---------------------------------------------------------------------------


class TestClassifyStravaType:
    def test_run_maps_to_easy(self):
        assert classify_strava_type("Run") == "easy"

    def test_trail_run_maps_to_easy(self):
        assert classify_strava_type("TrailRun") == "easy"

    def test_virtual_run_maps_to_easy(self):
        assert classify_strava_type("VirtualRun") == "easy"

    def test_race_maps_to_race(self):
        assert classify_strava_type("Race") == "race"

    def test_workout_maps_to_interval(self):
        assert classify_strava_type("Workout") == "interval"

    def test_ride_maps_to_cross_training(self):
        assert classify_strava_type("Ride") == "cross-training"

    def test_swim_maps_to_cross_training(self):
        assert classify_strava_type("Swim") == "cross-training"

    def test_unknown_maps_to_cross_training(self):
        assert classify_strava_type("Snowboard") == "cross-training"


# ---------------------------------------------------------------------------
# Unit Tests — normalize_strava_laps
# ---------------------------------------------------------------------------


class TestNormalizeStravaLaps:
    def test_none_returns_none(self):
        assert normalize_strava_laps(None) is None

    def test_empty_returns_none(self):
        assert normalize_strava_laps([]) is None

    def test_normalizes_lap_data(self):
        laps = [{"moving_time": 300, "distance": 1000, "average_heartrate": 155}]
        result = normalize_strava_laps(laps)
        assert len(result) == 1
        assert result[0]["duration_seconds"] == 300
        assert result[0]["distance_meters"] == 1000
        assert result[0]["avg_hr"] == 155
        assert result[0]["avg_pace_sec_per_km"] == 300.0

    def test_zero_distance_lap(self):
        laps = [{"moving_time": 60, "distance": 0}]
        result = normalize_strava_laps(laps)
        assert result[0]["avg_pace_sec_per_km"] is None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_STRAVA_ACTIVITY = {
    "id": 12345,
    "type": "Run",
    "start_date": "2026-03-01T08:00:00Z",
    "moving_time": 1800,
    "distance": 5000.0,
    "average_heartrate": 150,
    "max_heartrate": 175,
    "total_elevation_gain": 45.0,
    "calories": 350,
    "laps": [
        {"moving_time": 900, "distance": 2500, "average_heartrate": 148},
        {"moving_time": 900, "distance": 2500, "average_heartrate": 152},
    ],
}


# ---------------------------------------------------------------------------
# Unit Tests — StravaService.normalize_activity
# ---------------------------------------------------------------------------


class TestNormalizeActivity:
    def test_normalizes_strava_activity(self):
        result = StravaService.normalize_activity(SAMPLE_STRAVA_ACTIVITY)
        assert result.source == "strava"
        assert result.duration_seconds == 1800
        assert result.distance_meters == 5000.0
        assert result.avg_hr == 150
        assert result.max_hr == 175
        assert result.activity_type == "easy"
        assert result.avg_pace_sec_per_km == 360.0
        assert result.elevation_gain_m == 45.0
        assert result.calories == 350
        assert len(result.laps) == 2

    def test_race_type_normalized(self):
        activity = {**SAMPLE_STRAVA_ACTIVITY, "type": "Race"}
        result = StravaService.normalize_activity(activity)
        assert result.activity_type == "race"

    def test_zero_distance_no_crash(self):
        activity = {**SAMPLE_STRAVA_ACTIVITY, "distance": 0}
        result = StravaService.normalize_activity(activity)
        assert result.avg_pace_sec_per_km is None

    def test_missing_optional_fields(self):
        activity = {
            "id": 99,
            "type": "Run",
            "start_date": "2026-03-01T08:00:00Z",
            "moving_time": 600,
            "distance": 2000.0,
        }
        result = StravaService.normalize_activity(activity)
        assert result.avg_hr is None
        assert result.max_hr is None
        assert result.elevation_gain_m is None
        assert result.calories is None
        assert result.laps is None


# ---------------------------------------------------------------------------
# Unit Tests — StravaService async methods (mocked HTTP)
# ---------------------------------------------------------------------------


class TestStravaServiceAsync:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def service(self, mock_client):
        return StravaService(http_client=mock_client)

    def test_get_authorization_url(self, service):
        url = service.get_authorization_url(
            redirect_uri="http://localhost:3000/callback", state="user-123"
        )
        assert "https://www.strava.com/oauth/authorize" in url
        assert "activity:read_all" in url
        assert "state=user-123" in url
        assert "redirect_uri=http://localhost:3000/callback" in url

    @pytest.mark.asyncio
    async def test_exchange_token(self, service, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "abc",
            "refresh_token": "def",
            "expires_at": 9999999999,
            "athlete": {"id": 1, "firstname": "Test"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await service.exchange_token("test-code")
        assert result["access_token"] == "abc"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, service, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_at": 9999999999,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await service.refresh_access_token("old-refresh")
        assert result["access_token"] == "new-token"

    @pytest.mark.asyncio
    async def test_get_activity(self, service, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_STRAVA_ACTIVITY
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        result = await service.get_activity("token", 12345)
        assert result["id"] == 12345
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activities(self, service, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = [SAMPLE_STRAVA_ACTIVITY]
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        result = await service.get_activities("token", page=1, per_page=10)
        assert len(result) == 1
        assert result[0]["id"] == 12345


# ---------------------------------------------------------------------------
# Endpoint Tests — Strava Webhook Verification (GET, no auth)
# ---------------------------------------------------------------------------


class TestStravaWebhookVerify:
    def test_valid_verification(self, client):
        response = client.get(
            "/sync/webhook/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test-challenge-123",
                "hub.verify_token": "pirx-strava-verify",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"hub.challenge": "test-challenge-123"}

    def test_invalid_verify_token(self, client):
        response = client.get(
            "/sync/webhook/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test-challenge",
                "hub.verify_token": "wrong-token",
            },
        )
        assert response.status_code == 403

    def test_missing_mode(self, client):
        response = client.get(
            "/sync/webhook/strava",
            params={
                "hub.challenge": "test-challenge",
                "hub.verify_token": "pirx-strava-verify",
            },
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Endpoint Tests — Strava Webhook Receive (POST, no auth)
# ---------------------------------------------------------------------------


class TestStravaWebhookReceive:
    def test_activity_create_event(self, client):
        response = client.post(
            "/sync/webhook/strava",
            json={
                "object_type": "activity",
                "object_id": 12345,
                "aspect_type": "create",
                "owner_id": 67890,
                "subscription_id": 1,
                "event_time": 1709280000,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_athlete_update_event(self, client):
        response = client.post(
            "/sync/webhook/strava",
            json={
                "object_type": "athlete",
                "object_id": 67890,
                "aspect_type": "update",
                "owner_id": 67890,
                "subscription_id": 1,
                "event_time": 1709280000,
            },
        )
        assert response.status_code == 200

    def test_activity_delete_event(self, client):
        response = client.post(
            "/sync/webhook/strava",
            json={
                "object_type": "activity",
                "object_id": 12345,
                "aspect_type": "delete",
                "owner_id": 67890,
                "subscription_id": 1,
                "event_time": 1709280000,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
