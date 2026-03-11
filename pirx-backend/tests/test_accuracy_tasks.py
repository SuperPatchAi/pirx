from unittest.mock import MagicMock, patch

import pytest

from app.tasks.accuracy_tasks import compute_model_accuracy


class TestAccuracyTasks:
    @patch("app.services.supabase_client.SupabaseService")
    def test_compute_model_accuracy_keeps_event_biases_separate(self, mock_svc_cls):
        """Event-level bias must only use biases from that event."""
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        mock_svc.get_onboarded_users.return_value = [{"user_id": "u1"}]
        mock_svc.get_race_activities.return_value = [
            # 5K races -> positive biases (+10, +20) vs projection=1000
            {"distance_meters": 5000, "duration_seconds": 1010},
            {"distance_meters": 5000, "duration_seconds": 1020},
            # 10K races -> negative biases (-10, -20) vs projection=1000
            {"distance_meters": 10000, "duration_seconds": 990},
            {"distance_meters": 10000, "duration_seconds": 980},
        ]
        mock_svc.get_latest_projection.return_value = {"midpoint_seconds": 1000}
        mock_svc.insert_model_metric.return_value = {}

        result = compute_model_accuracy()

        assert result["status"] == "completed"
        metric_rows = [c.args[0] for c in mock_svc.insert_model_metric.call_args_list]
        by_type = {row["model_type"]: row for row in metric_rows}

        assert "event_5000" in by_type
        assert "event_10000" in by_type
        # If event biases are mixed globally, these collapse toward 0 and fail.
        assert by_type["event_5000"]["bias_seconds"] == pytest.approx(15.0, abs=0.01)
        assert by_type["event_10000"]["bias_seconds"] == pytest.approx(-15.0, abs=0.01)
