import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_verify_returns_true_when_no_secret(self, monkeypatch):
        """In dev mode with no secret configured, always returns True."""
        monkeypatch.setattr("app.services.terra_service.settings", type("S", (), {"terra_webhook_secret": ""})())
        assert TerraService.verify_webhook_signature(b"test", "any") is True

    def test_verify_valid_signature(self):
        """Correctly verifies a valid Terra t=,v1= signature."""
        secret = "test-secret-key"
        body = b'{"type":"activity"}'
        timestamp = "1723808700"
        signed_payload = body + b"." + timestamp.encode()
        expected_hash = hmac.new(
            secret.encode(), signed_payload, hashlib.sha256
        ).hexdigest()
        signature = f"t={timestamp},v1={expected_hash}"

        with patch("app.services.terra_service.settings") as mock_settings:
            mock_settings.terra_webhook_secret = secret
            assert TerraService.verify_webhook_signature(body, signature) is True

    def test_verify_rejects_invalid_signature(self):
        """Rejects a tampered signature."""
        secret = "test-secret-key"
        body = b'{"type":"activity"}'
        signature = "t=1723808700,v1=deadbeefdeadbeefdeadbeefdeadbeef"

        with patch("app.services.terra_service.settings") as mock_settings:
            mock_settings.terra_webhook_secret = secret
            assert TerraService.verify_webhook_signature(body, signature) is False

    def test_verify_rejects_malformed_signature(self):
        """Rejects a signature without the expected t= and v1= fields."""
        secret = "test-secret-key"
        with patch("app.services.terra_service.settings") as mock_settings:
            mock_settings.terra_webhook_secret = secret
            assert TerraService.verify_webhook_signature(b"test", "garbage") is False

    def test_verify_rejects_empty_signature(self):
        """Rejects an empty signature string."""
        with patch("app.services.terra_service.settings") as mock_settings:
            mock_settings.terra_webhook_secret = "secret"
            assert TerraService.verify_webhook_signature(b"test", "") is False


class TestTerraDeauthentication:
    @pytest.mark.asyncio
    async def test_deauthenticate_calls_terra_api(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)

        service = TerraService(http_client=mock_client)
        result = await service.deauthenticate_user("terra-user-123")

        assert result is True
        mock_client.delete.assert_called_once()
        call_kwargs = mock_client.delete.call_args
        assert "terra-user-123" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_deauthenticate_returns_false_on_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)

        service = TerraService(http_client=mock_client)
        result = await service.deauthenticate_user("terra-user-missing")

        assert result is False


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


class TestBackfillTerraUserIdLookup:
    """Verify that backfill_history uses terra_user_id from wearable_connections."""

    def _run_backfill(self, mock_db, mock_http_client=None, settings_overrides=None):
        """Call the raw backfill function bypassing Celery task binding."""
        from app.tasks.sync_tasks import backfill_history

        mock_task_self = MagicMock()
        mock_task_self.request.id = "task-test"

        patches = [
            patch("app.services.supabase_client.SupabaseService", return_value=mock_db),
            patch("app.config.settings"),
        ]
        if mock_http_client is not None:
            patches.append(patch("httpx.Client", return_value=mock_http_client))

        with patches[0], patches[1] as mock_settings:
            mock_settings.terra_api_key = "test-key"
            mock_settings.terra_dev_id = "test-dev"
            if settings_overrides:
                for k, v in settings_overrides.items():
                    setattr(mock_settings, k, v)

            if len(patches) > 2:
                with patches[2]:
                    return backfill_history.__wrapped__("pirx-user-1", "garmin")
            return backfill_history.__wrapped__("pirx-user-1", "garmin")

    def test_backfill_looks_up_terra_user_id(self):
        mock_db = MagicMock()
        mock_db.get_wearable_connections.return_value = [
            {
                "provider": "garmin",
                "is_active": True,
                "terra_user_id": "terra-garmin-abc",
            }
        ]
        mock_db.register_task.return_value = None
        mock_db.update_task_status.return_value = None

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = mock_resp

        result = self._run_backfill(mock_db, mock_http_client=mock_http)

        call_args = mock_http.get.call_args
        assert call_args is not None
        params = call_args.kwargs.get("params", {})
        assert params.get("user_id") == "terra-garmin-abc"

    def test_backfill_fails_without_terra_user_id(self):
        mock_db = MagicMock()
        mock_db.get_wearable_connections.return_value = [
            {
                "provider": "garmin",
                "is_active": True,
                "terra_user_id": None,
            }
        ]
        mock_db.register_task.return_value = None
        mock_db.update_task_status.return_value = None

        result = self._run_backfill(mock_db)
        assert result["status"] == "error"
        assert "terra_user_id" in result["error"]
