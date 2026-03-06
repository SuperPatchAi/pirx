import pytest

from app.services.terra_service import (
    TerraService,
    classify_terra_type,
    extract_hr_zones,
)


class TestClassifyTerraType:
    def test_running_maps_to_easy(self):
        assert classify_terra_type(1) == "easy"

    def test_trail_running_maps_to_easy(self):
        assert classify_terra_type(12) == "easy"

    def test_virtual_run_maps_to_easy(self):
        assert classify_terra_type(83) == "easy"

    def test_cycling_maps_to_cross_training(self):
        assert classify_terra_type(2) == "cross-training"

    def test_race_keyword_overrides_type(self):
        assert classify_terra_type(1, "Morning parkrun") == "race"

    def test_competition_keyword(self):
        assert classify_terra_type(1, "10K Competition") == "race"

    def test_interval_keyword_overrides_type(self):
        assert classify_terra_type(1, "Tempo Thursday") == "interval"

    def test_fartlek_keyword(self):
        assert classify_terra_type(1, "Fartlek session") == "interval"

    def test_unknown_type_cross_training(self):
        assert classify_terra_type(0) == "cross-training"


SAMPLE_TERRA_ACTIVITY = {
    "start_time": "2026-03-01T08:00:00+00:00",
    "metadata": {"type": 1, "name": "Morning Run", "provider": "GARMIN"},
    "active_durations_data": {"activity_seconds": 2400},
    "distance_data": {
        "summary": {"distance_meters": 8000.0},
    },
    "heart_rate_data": {
        "summary": {"avg_hr_bpm": 148, "max_hr_bpm": 172},
        "hr_zones": [
            {"zone": 1, "duration_seconds": 120},
            {"zone": 2, "duration_seconds": 1200},
            {"zone": 3, "duration_seconds": 600},
            {"zone": 4, "duration_seconds": 360},
            {"zone": 5, "duration_seconds": 120},
        ],
    },
    "calories_data": {"total_burned_calories": 520},
}


class TestTerraServiceNormalize:
    def test_normalizes_terra_activity(self):
        result = TerraService.normalize_activity(SAMPLE_TERRA_ACTIVITY)
        assert result.source == "garmin"
        assert result.duration_seconds == 2400
        assert result.distance_meters == 8000.0
        assert result.avg_hr == 148
        assert result.max_hr == 172
        assert result.activity_type == "easy"
        assert result.avg_pace_sec_per_km == 300.0
        assert result.calories == 520

    def test_extracts_hr_zones(self):
        result = TerraService.normalize_activity(SAMPLE_TERRA_ACTIVITY)
        assert result.hr_zones is not None
        assert len(result.hr_zones) == 5
        assert result.hr_zones[1] == 1200.0

    def test_race_from_name(self):
        activity = {
            **SAMPLE_TERRA_ACTIVITY,
            "metadata": {**SAMPLE_TERRA_ACTIVITY["metadata"], "name": "Parkrun Race"},
        }
        result = TerraService.normalize_activity(activity)
        assert result.activity_type == "race"

    def test_zero_distance_no_crash(self):
        activity = {**SAMPLE_TERRA_ACTIVITY}
        activity["distance_data"] = {"summary": {"distance_meters": 0}}
        result = TerraService.normalize_activity(activity)
        assert result.avg_pace_sec_per_km is None

    def test_missing_hr_data(self):
        activity = {**SAMPLE_TERRA_ACTIVITY}
        activity["heart_rate_data"] = {}
        result = TerraService.normalize_activity(activity)
        assert result.avg_hr is None
        assert result.max_hr is None
        assert result.hr_zones is None


class TestExtractHrZones:
    def test_extracts_zones(self):
        zones = extract_hr_zones(SAMPLE_TERRA_ACTIVITY)
        assert zones is not None
        assert len(zones) == 5

    def test_none_when_missing(self):
        assert extract_hr_zones({}) is None

    def test_none_when_empty(self):
        assert extract_hr_zones({"heart_rate_data": {"hr_zones": []}}) is None


class TestWebhookSignatureVerification:
    def test_verify_returns_true_when_no_secret(self):
        """In dev mode with no secret configured, always returns True."""
        assert TerraService.verify_webhook_signature(b"test", "any") is True


class TestTerraWebhookEndpoint:
    def test_terra_webhook_activity(self, client):
        payload = {
            "type": "activity",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "data": [SAMPLE_TERRA_ACTIVITY],
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_terra_webhook_auth(self, client):
        payload = {
            "type": "auth",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_terra_webhook_unknown_type(self, client):
        payload = {
            "type": "sleep",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "data": [{}],
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
