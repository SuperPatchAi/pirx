import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.terra_service import (
    TerraService,
    classify_terra_type,
    classify_terra_activity,
    extract_hr_zones,
)


class TestClassifyTerraType:
    """Legacy wrapper tests — classify_terra_type delegates to classify_terra_activity
    without HR/pace data, so running codes default to 'easy'.
    """

    def test_running_maps_to_easy(self):
        assert classify_terra_type(8) == "easy"

    def test_jogging_maps_to_easy(self):
        assert classify_terra_type(56) == "easy"

    def test_treadmill_running_maps_to_easy(self):
        assert classify_terra_type(58) == "easy"

    def test_indoor_running_maps_to_easy(self):
        assert classify_terra_type(133) == "easy"

    def test_running_on_sand_maps_to_easy(self):
        assert classify_terra_type(57) == "easy"

    def test_biking_maps_to_cross_training(self):
        assert classify_terra_type(1) == "cross-training"

    def test_swimming_maps_to_cross_training(self):
        assert classify_terra_type(82) == "cross-training"

    def test_swimming_in_pool_maps_to_cross_training(self):
        assert classify_terra_type(83) == "cross-training"

    def test_walking_maps_to_cross_training(self):
        assert classify_terra_type(7) == "cross-training"

    def test_hiking_maps_to_cross_training(self):
        assert classify_terra_type(35) == "cross-training"

    def test_yoga_maps_to_cross_training(self):
        assert classify_terra_type(100) == "cross-training"

    def test_strength_maps_to_cross_training(self):
        assert classify_terra_type(80) == "cross-training"

    def test_race_keyword_overrides_type(self):
        assert classify_terra_type(8, "Morning parkrun") == "race"

    def test_competition_keyword(self):
        assert classify_terra_type(8, "10K Competition") == "race"

    def test_interval_keyword_overrides_type(self):
        assert classify_terra_type(8, "Tempo Thursday") == "interval"

    def test_fartlek_keyword(self):
        assert classify_terra_type(8, "Fartlek session") == "interval"

    def test_in_vehicle_defaults_to_cross_training(self):
        assert classify_terra_type(0) == "cross-training"

    def test_unknown_code_with_running_name_maps_to_easy(self):
        assert classify_terra_type(0, "Morning Run") == "easy"

    def test_unknown_code_with_jog_name_maps_to_easy(self):
        assert classify_terra_type(4, "Easy Jog") == "easy"

    def test_unknown_code_no_name_maps_to_cross_training(self):
        assert classify_terra_type(4) == "cross-training"


class TestClassifyTerraActivity:
    """Full classifier tests with HR, pace, and distance data.

    These mirror real Garmin data arriving via Terra webhooks.
    """

    # --- Name-based overrides still take priority ---
    def test_race_name_overrides_all(self):
        assert classify_terra_activity(8, "Morning parkrun", avg_hr=130, max_hr=180) == "race"

    def test_interval_name_overrides_all(self):
        assert classify_terra_activity(8, "Track Repeats", avg_hr=130, max_hr=180) == "interval"

    def test_tempo_name_overrides_all(self):
        assert classify_terra_activity(8, "Tempo Thursday", avg_hr=130, max_hr=180) == "interval"

    def test_recovery_name_maps_to_easy(self):
        assert classify_terra_activity(8, "Recovery Run", avg_hr=130, max_hr=180) == "easy"

    def test_vo2_name_maps_to_interval(self):
        assert classify_terra_activity(8, "VO2 Max Session", avg_hr=130, max_hr=180) == "interval"

    # --- HR-based intensity detection ---
    def test_high_hr_race_distance_is_race(self):
        """1500m at HR 172 (91% of 190) on a standard race distance → race"""
        result = classify_terra_activity(
            133, "Indoor Running",
            pace_sec_per_km=205, avg_hr=172, max_hr=190,
            distance_meters=1500, duration_seconds=308,
        )
        assert result == "race"

    def test_very_high_hr_3k_race_distance_is_race(self):
        """3000m at HR 175 (92% of 190) on a standard race distance → race"""
        result = classify_terra_activity(
            133, "Indoor Running",
            pace_sec_per_km=224, avg_hr=175, max_hr=190,
            distance_meters=3000, duration_seconds=673,
        )
        assert result == "race"

    def test_high_hr_non_race_distance_is_interval(self):
        """2000m at HR 172 (91% of 190) NOT a race distance → interval"""
        result = classify_terra_activity(
            133, "Indoor Running",
            pace_sec_per_km=210, avg_hr=172, max_hr=190,
            distance_meters=2000, duration_seconds=420,
        )
        assert result == "interval"

    def test_labelled_repeats_overrides_race_distance(self):
        """1500m repeats labelled as intervals → interval (name wins)"""
        result = classify_terra_activity(
            133, "1500m Repeats",
            pace_sec_per_km=205, avg_hr=172, max_hr=190,
            distance_meters=1500, duration_seconds=308,
        )
        assert result == "interval"

    def test_threshold_hr_is_threshold(self):
        """5250m at HR 156 (82% of 190) → threshold"""
        result = classify_terra_activity(
            58, "Treadmill Running",
            pace_sec_per_km=274, avg_hr=156, max_hr=190,
            distance_meters=5250, duration_seconds=1440,
        )
        assert result == "threshold"

    def test_easy_hr_is_easy(self):
        """8000m at HR 134 (70% of 190) → easy"""
        result = classify_terra_activity(
            58, "Treadmill Running",
            pace_sec_per_km=320, avg_hr=134, max_hr=190,
            distance_meters=8000, duration_seconds=2559,
        )
        assert result == "easy"

    def test_moderate_hr_12k_is_easy(self):
        """12000m at HR 148 (78% of 190) → easy (below threshold cutoff)"""
        result = classify_terra_activity(
            58, "Treadmill Running",
            pace_sec_per_km=286, avg_hr=148, max_hr=190,
            distance_meters=12000, duration_seconds=3432,
        )
        assert result == "easy"

    # --- Race detection: standard distance + high HR ---
    def test_5k_race_distance_high_hr(self):
        """5000m at HR 170 (89% of 190) on a race distance → race"""
        result = classify_terra_activity(
            8, "Toronto Running",
            pace_sec_per_km=240, avg_hr=170, max_hr=190,
            distance_meters=5000, duration_seconds=1200,
        )
        assert result == "race"

    def test_10k_race_distance_high_hr(self):
        """10000m at HR 172 (91% of 190) on a race distance → race"""
        result = classify_terra_activity(
            8, "Toronto Running",
            pace_sec_per_km=270, avg_hr=172, max_hr=190,
            distance_meters=10000, duration_seconds=2700,
        )
        assert result == "race"

    # --- Cross-training is unaffected by HR ---
    def test_cycling_stays_cross_training(self):
        result = classify_terra_activity(
            1, "Cycling", avg_hr=160, max_hr=190,
            distance_meters=20000, duration_seconds=3600,
        )
        assert result == "cross-training"

    def test_strength_stays_cross_training(self):
        result = classify_terra_activity(
            80, "Strength Training", avg_hr=140, max_hr=190,
        )
        assert result == "cross-training"

    # --- No HR: pace-based fallback ---
    def test_very_fast_short_no_hr_is_interval(self):
        """Short distance, fast pace, no HR → interval"""
        result = classify_terra_activity(
            8, "Running",
            pace_sec_per_km=210, avg_hr=None, max_hr=None,
            distance_meters=1500, duration_seconds=315,
        )
        assert result == "interval"

    def test_no_hr_moderate_pace_is_easy(self):
        """No HR data, moderate pace → defaults to easy"""
        result = classify_terra_activity(
            8, "Running",
            pace_sec_per_km=320, avg_hr=None, max_hr=None,
            distance_meters=8000, duration_seconds=2560,
        )
        assert result == "easy"


SAMPLE_TERRA_ACTIVITY = {
    "start_time": "2026-03-01T08:00:00+00:00",
    "metadata": {"type": 8, "name": "Morning Run", "provider": "GARMIN"},
    "active_durations_data": {"activity_seconds": 2400},
    "distance_data": {
        "summary": {"distance_meters": 8000.0},
    },
    "heart_rate_data": {
        "summary": {"avg_hr_bpm": 138, "max_hr_bpm": 172},
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

SAMPLE_TERRA_SLEEP = {
    "metadata": {
        "provider": "GARMIN",
        "start_time": "2026-03-08T23:15:00+00:00",
        "end_time": "2026-03-09T07:00:00+00:00",
        "summary_id": "sleep-summary-123",
    },
    "data_enrichment": {"sleep_score": 86},
    "scores": {"sleep": 84},
    "sleep_durations_data": {
        "asleep": {
            "duration_asleep_state_seconds": 27000,
            "duration_deep_sleep_state_seconds": 4200,
            "duration_light_sleep_state_seconds": 16000,
            "duration_REM_sleep_state_seconds": 5400,
        },
        "awake": {
            "duration_awake_state_seconds": 1200,
        },
        "sleep_efficiency": 0.91,
    },
    "heart_rate_data": {"summary": {"resting_hr_bpm": 48, "avg_hrv_sdnn": 61}},
}

SAMPLE_TERRA_BODY = {
    "metadata": {
        "provider": "GARMIN",
        "start_time": "2026-03-09T07:30:00+00:00",
        "end_time": "2026-03-09T07:31:00+00:00",
    },
    "measurements_data": {
        "measurements": [
            {
                "measurement_time": "2026-03-09T07:30:00+00:00",
                "weight_kg": 70.2,
                "bodyfat_percentage": 13.8,
                "BMI": 22.1,
                "BMR": 1750,
            },
        ]
    },
    "heart_data": {
        "heart_rate_data": {
            "summary": {
                "resting_hr_bpm": 52,
                "avg_hrv_sdnn": 58,
            }
        }
    },
    "oxygen_data": {
        "vo2max_ml_per_min_per_kg": 52.3,
    },
}

SAMPLE_TERRA_BODY_LEGACY = {
    "metadata": {
        "provider": "GARMIN",
        "start_time": "2026-03-09T07:30:00+00:00",
        "end_time": "2026-03-09T07:31:00+00:00",
    },
    "measurements_data": {
        "measurements": [
            {"measurement_type": "weight_kg", "value": 70.2},
            {"measurement_type": "body_fat_percentage", "value": 13.8},
            {"measurement_type": "bmi", "value": 22.1},
        ]
    },
}

SAMPLE_TERRA_DAILY = {
    "metadata": {
        "provider": "GARMIN",
        "start_time": "2026-03-09T00:00:00+00:00",
        "end_time": "2026-03-09T23:59:59+00:00",
    },
    "scores": {"sleep": 79, "recovery": 74, "activity": 82},
    "heart_rate_data": {
        "summary": {
            "resting_hr_bpm": 47,
            "avg_hrv_sdnn": 63,
            "avg_hrv_rmssd": 52,
        }
    },
    "data_enrichment": {
        "readiness_score": 76,
    },
    "oxygen_data": {
        "vo2max_ml_per_min_per_kg": 51.8,
    },
    "stress_data": {
        "avg_stress_level": 42,
    },
    "strain_data": {
        "strain_level": 6.5,
    },
}


class TestTerraServiceNormalize:
    def test_normalizes_terra_activity(self):
        result = TerraService.normalize_activity(SAMPLE_TERRA_ACTIVITY)
        assert result.source == "garmin"
        assert result.duration_seconds == 2400
        assert result.distance_meters == 8000.0
        assert result.avg_hr == 138
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

    def test_normalizes_sleep_entry(self):
        result = TerraService.normalize_sleep_entry(SAMPLE_TERRA_SLEEP)
        assert result["sleep_score"] == 86.0
        assert result["resting_hr"] == 48
        assert result["hrv"] == 61.0
        assert result["custom_fields"]["terra_type"] == "sleep"
        assert result["custom_fields"]["summary_id"] == "sleep-summary-123"
        assert result["custom_fields"]["sleep_total_seconds"] == 27000.0
        assert result["custom_fields"]["sleep_efficiency"] == 0.91

    def test_normalizes_body_entry(self):
        result = TerraService.normalize_body_entry(SAMPLE_TERRA_BODY)
        assert result["source"] == "wearable"
        assert result["custom_fields"]["terra_type"] == "body"
        assert result["custom_fields"]["weight_kg"] == 70.2
        assert result["custom_fields"]["body_fat_percentage"] == 13.8
        assert result["custom_fields"]["bmi"] == 22.1

    def test_body_extracts_heart_data(self):
        """Gap 6: Body heart data lives under heart_data.heart_rate_data.summary."""
        result = TerraService.normalize_body_entry(SAMPLE_TERRA_BODY)
        assert result["resting_hr"] == 52
        assert result["hrv"] == 58.0

    def test_body_extracts_vo2max(self):
        """Gap 5: VO2max from oxygen_data."""
        result = TerraService.normalize_body_entry(SAMPLE_TERRA_BODY)
        assert result["custom_fields"]["vo2max_ml_per_min_per_kg"] == 52.3

    def test_body_legacy_measurement_type_format(self):
        """Legacy measurement_type+value pattern still works."""
        result = TerraService.normalize_body_entry(SAMPLE_TERRA_BODY_LEGACY)
        assert result["custom_fields"]["weight_kg"] == 70.2
        assert result["custom_fields"]["body_fat_percentage"] == 13.8
        assert result["custom_fields"]["bmi"] == 22.1

    def test_body_real_terra_flat_keys(self):
        """Gap 1+2: Real Terra MeasurementDataSample uses flat keys with bodyfat_percentage and BMI."""
        body = {
            "metadata": {"provider": "GARMIN", "start_time": "2026-03-09T00:00:00+00:00", "end_time": "2026-03-09T23:59:59+00:00"},
            "measurements_data": {
                "measurements": [
                    {"measurement_time": "2026-03-09T07:00:00+00:00", "weight_kg": 72.5, "bodyfat_percentage": 15.2, "BMI": 23.1},
                ]
            },
        }
        result = TerraService.normalize_body_entry(body)
        assert result["custom_fields"]["weight_kg"] == 72.5
        assert result["custom_fields"]["body_fat_percentage"] == 15.2
        assert result["custom_fields"]["bmi"] == 23.1

    def test_normalizes_daily_entry(self):
        result = TerraService.normalize_daily_entry(SAMPLE_TERRA_DAILY)
        assert result["sleep_score"] == 79.0
        assert result["resting_hr"] == 47
        assert result["hrv"] == 63.0
        assert result["custom_fields"]["terra_type"] == "daily"
        assert result["custom_fields"]["daily_window_key"] == "2026-03-09T00:00:00+00:00|2026-03-09T23:59:59+00:00"

    def test_daily_extracts_recovery_and_activity_scores(self):
        """Gap 8: scores.recovery and scores.activity from Daily."""
        result = TerraService.normalize_daily_entry(SAMPLE_TERRA_DAILY)
        assert result["custom_fields"]["daily_recovery_score_from_scores"] == 74.0
        assert result["custom_fields"]["daily_activity_score"] == 82.0

    def test_daily_extracts_vo2max(self):
        """Gap 5: VO2max from Daily oxygen_data."""
        result = TerraService.normalize_daily_entry(SAMPLE_TERRA_DAILY)
        assert result["custom_fields"]["vo2max_ml_per_min_per_kg"] == 51.8

    def test_daily_extracts_stress_and_strain(self):
        """Gap 9: stress and strain from Daily."""
        result = TerraService.normalize_daily_entry(SAMPLE_TERRA_DAILY)
        assert result["custom_fields"]["avg_stress_level"] == 42.0
        assert result["custom_fields"]["strain_level"] == 6.5

    def test_sleep_readiness_data_readiness_field(self):
        """Gap 7: readiness_data.readiness is the correct Terra field."""
        sleep_payload = {
            "metadata": {"provider": "GARMIN", "start_time": "2026-03-08T23:00:00+00:00", "end_time": "2026-03-09T06:30:00+00:00"},
            "readiness_data": {"readiness": 88, "recovery_level": 3},
        }
        result = TerraService.normalize_sleep_entry(sleep_payload)
        assert result["sleep_score"] == 88.0


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
    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_activity(self, mock_sig, client):
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

    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_auth(self, mock_sig, client):
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

    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_unknown_type(self, mock_sig, client):
        payload = {
            "type": "unknown_type",
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

    @patch("app.routers.sync.SupabaseService")
    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_sleep_persists_physiology(self, _mock_sig, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        payload = {
            "type": "sleep",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "data": [SAMPLE_TERRA_SLEEP],
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        mock_db.insert_wearable_physiology.assert_called_once()

    @patch("app.routers.sync.SupabaseService")
    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_body_persists_physiology(self, _mock_sig, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        payload = {
            "type": "body",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "data": [SAMPLE_TERRA_BODY],
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        mock_db.insert_wearable_physiology.assert_called_once()

    @patch("app.routers.sync.SupabaseService")
    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_daily_persists_physiology(self, _mock_sig, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        payload = {
            "type": "daily",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "data": [SAMPLE_TERRA_DAILY],
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        mock_db.insert_wearable_physiology.assert_called_once()

    @patch("app.routers.sync.SupabaseService")
    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_deauth_deactivates_connection(self, _mock_sig, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_update_chain = MagicMock()
        mock_db.client.table.return_value.update.return_value = mock_update_chain
        mock_update_chain.eq.return_value = mock_update_chain
        mock_update_chain.execute.return_value = MagicMock(data=[])
        payload = {
            "type": "deauth",
            "user": {
                "user_id": "terra-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        mock_db.client.table.assert_called_with("wearable_connections")

    @patch("app.routers.sync.SupabaseService")
    @patch("app.routers.sync.TerraService.verify_webhook_signature", return_value=True)
    def test_terra_webhook_user_reauth_updates_connection(self, _mock_sig, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        payload = {
            "type": "user_reauth",
            "old_user": {
                "user_id": "terra-old-123",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "new_user": {
                "user_id": "terra-new-789",
                "provider": "GARMIN",
                "reference_id": "pirx-user-456",
            },
            "status": "warning",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 200
        mock_db.client.table.assert_called_with("wearable_connections")

    def test_terra_webhook_rejects_invalid_signature(self, client):
        payload = {
            "type": "activity",
            "user": {"user_id": "terra-123", "provider": "GARMIN", "reference_id": "pirx-user-456"},
            "data": [SAMPLE_TERRA_ACTIVITY],
            "status": "success",
        }
        response = client.post("/sync/webhook/terra", json=payload)
        assert response.status_code == 403


class TestBackfillTerraUserIdLookup:
    """Verify that backfill_history uses terra_user_id from wearable_connections."""

    def _run_backfill(self, mock_db, mock_http_client=None, settings_overrides=None):
        """Call the raw backfill function bypassing Celery task binding."""
        from app.tasks.sync_tasks import backfill_history

        mock_task_self = MagicMock()
        mock_task_self.request.id = "task-test"

        mock_redis = MagicMock()
        mock_redis.set.return_value = True

        patches = [
            patch("app.services.supabase_client.SupabaseService", return_value=mock_db),
            patch("app.config.settings"),
            patch("redis.from_url", return_value=mock_redis),
        ]
        if mock_http_client is not None:
            patches.append(patch("httpx.Client", return_value=mock_http_client))

        with patches[0], patches[1] as mock_settings, patches[2]:
            mock_settings.terra_api_key = "test-key"
            mock_settings.terra_dev_id = "test-dev"
            mock_settings.redis_url = "redis://localhost:6379/0"
            if settings_overrides:
                for k, v in settings_overrides.items():
                    setattr(mock_settings, k, v)

            if len(patches) > 3:
                with patches[3]:
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
