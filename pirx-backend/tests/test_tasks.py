import pytest
from unittest.mock import patch, MagicMock
from app.tasks.feature_engineering import compute_features, STRUCTURAL_SHIFT_THRESHOLD_SECONDS
from app.tasks.sync_tasks import process_activity
from app.tasks.projection_tasks import (
    recompute_projection,
    recompute_all_events,
    structural_decay_check,
    weekly_summary,
    bias_correction,
)


class TestComputeFeaturesTask:
    def test_no_activities_returns_no_activities(self):
        result = compute_features("user-123")
        assert result["status"] == "no_activities"
        assert result["user_id"] == "user-123"

    def test_with_activity_data(self):
        activity_data = {
            "source": "strava",
            "timestamp": "2026-03-01T08:00:00",
            "duration_seconds": 1800,
            "distance_meters": 5000.0,
            "avg_hr": 150,
            "activity_type": "easy",
        }
        result = compute_features("user-123", activity_data=activity_data)
        assert result["status"] == "completed"
        assert result["activities_cleaned"] >= 1
        assert result["features_computed"] > 0

    def test_cross_training_filtered_out(self):
        activity_data = {
            "source": "strava",
            "timestamp": "2026-03-01T08:00:00",
            "duration_seconds": 3600,
            "distance_meters": 20000.0,
            "activity_type": "cross-training",
        }
        result = compute_features("user-123", activity_data=activity_data)
        assert result["status"] == "all_filtered"

    def test_structural_shift_threshold_constant(self):
        assert STRUCTURAL_SHIFT_THRESHOLD_SECONDS == 2.0


class TestProcessActivityTask:
    @patch("app.tasks.feature_engineering.compute_features")
    def test_strava_activity_processed(self, mock_compute):
        mock_compute.delay = MagicMock()
        raw = {
            "id": 12345,
            "type": "Run",
            "start_date": "2026-03-01T08:00:00Z",
            "moving_time": 1800,
            "distance": 5000.0,
            "average_heartrate": 150,
            "max_heartrate": 175,
            "total_elevation_gain": 45.0,
        }
        result = process_activity("user-123", raw, source="strava")
        assert result["status"] == "processed"
        assert result["activity_type"] == "easy"
        mock_compute.delay.assert_called_once_with("user-123")

    @patch("app.tasks.feature_engineering.compute_features")
    def test_terra_activity_processed(self, mock_compute):
        mock_compute.delay = MagicMock()
        raw = {
            "start_time": "2026-03-01T08:00:00+00:00",
            "metadata": {"type": 1, "name": "Morning Run", "provider": "GARMIN"},
            "active_durations_data": {"activity_seconds": 2400},
            "distance_data": {"summary": {"distance_meters": 8000.0}},
            "heart_rate_data": {"summary": {"avg_hr_bpm": 148, "max_hr_bpm": 172}},
            "calories_data": {"total_burned_calories": 520},
        }
        result = process_activity("user-123", raw, source="terra")
        assert result["status"] == "processed"
        mock_compute.delay.assert_called_once()

    @patch("app.tasks.feature_engineering.compute_features")
    def test_cycling_filtered_out(self, mock_compute):
        mock_compute.delay = MagicMock()
        raw = {
            "id": 99,
            "type": "Ride",
            "start_date": "2026-03-01T08:00:00Z",
            "moving_time": 3600,
            "distance": 30000.0,
        }
        result = process_activity("user-123", raw, source="strava")
        assert result["status"] == "filtered_out"
        mock_compute.delay.assert_not_called()


class TestProjectionTasks:
    def test_recompute_returns_not_implemented(self):
        result = recompute_projection("user-123", "3000")
        assert result["status"] == "not_implemented"

    def test_recompute_all_events(self):
        result = recompute_all_events("user-123")
        assert "1500" in result["events"]
        assert "10000" in result["events"]

    def test_structural_decay_check(self):
        result = structural_decay_check()
        assert result["task"] == "structural_decay_check"

    def test_weekly_summary(self):
        result = weekly_summary()
        assert result["task"] == "weekly_summary"

    def test_bias_correction(self):
        result = bias_correction()
        assert result["task"] == "bias_correction"


class TestBackfillTask:
    def test_returns_not_implemented(self):
        from app.tasks.sync_tasks import backfill_history
        result = backfill_history("user-123", "strava")
        assert result["status"] == "not_implemented"
        assert result["provider"] == "strava"
