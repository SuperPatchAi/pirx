import pytest
from unittest.mock import patch, MagicMock
from app.tasks.feature_engineering import compute_features
from app.tasks.sync_tasks import process_activity
from app.tasks.projection_tasks import (
    recompute_projection,
    recompute_all_events,
    structural_decay_check,
    weekly_summary,
    bias_correction,
)


class TestComputeFeaturesTask:
    @patch("app.services.supabase_client.SupabaseService")
    def test_no_activities_returns_no_activities(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db.get_recent_activities.return_value = []
        mock_db_cls.return_value = mock_db
        result = compute_features("user-123")
        assert result["status"] == "no_activities"
        assert result["user_id"] == "user-123"

    @patch("app.tasks.projection_tasks.recompute_all_events")
    def test_with_activity_data(self, mock_recompute_all):
        mock_recompute_all.delay = MagicMock()
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
        assert result["projection_recompute_triggered"] is True
        mock_recompute_all.delay.assert_called_once_with("user-123")

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

    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_all_events_covers_six_events(self, mock_sb):
        mock_sb.return_value = MagicMock()
        result = recompute_all_events("user-test")
        assert len(result["events"]) == 6
        for ev in ("1500", "3000", "5000", "10000", "21097", "42195"):
            assert ev in result["events"]


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
            "metadata": {"type": 8, "name": "Morning Run", "provider": "GARMIN"},
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
    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_no_data(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])
        result = recompute_projection("user-123", "3000")
        assert result["status"] in ("no_data", "error")

    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_all_events(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])
        result = recompute_all_events("user-123")
        assert "1500" in result["events"]
        assert "10000" in result["events"]

    @patch("app.services.supabase_client.get_supabase_client")
    def test_structural_decay_check(self, mock_sb):
        mock_sb.return_value = MagicMock()
        result = structural_decay_check()
        assert result["status"] == "completed"

    @patch("app.services.supabase_client.get_supabase_client")
    def test_weekly_summary(self, mock_sb):
        mock_sb.return_value = MagicMock()
        result = weekly_summary()
        assert result["status"] == "completed"

    @patch("app.services.supabase_client.get_supabase_client")
    def test_bias_correction(self, mock_sb):
        mock_sb.return_value = MagicMock()
        result = bias_correction()
        assert result["status"] == "completed"


class TestBackfillTask:
    @patch("httpx.Client")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_backfill_strava(self, mock_sb, mock_httpx_cls):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"provider": "strava", "is_active": True, "access_token": "fake"}
        ]
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{}]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = mock_resp
        mock_httpx_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_httpx_cls.return_value.__exit__ = MagicMock(return_value=False)
        from app.tasks.sync_tasks import backfill_history
        result = backfill_history("user-123", "strava")
        assert result["status"] == "completed"
        assert result["provider"] == "strava"

    @patch("httpx.Client")
    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_backfill_history_strava_with_activities(self, mock_sb, mock_svc_cls, mock_httpx_cls):
        """Mock Strava API returning activities; verify they are stored."""
        mock_sb.return_value = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get_wearable_connections.return_value = [
            {"provider": "strava", "is_active": True, "access_token": "tok-123"},
        ]
        mock_svc.insert_activity.return_value = {}
        mock_svc.register_task.return_value = {}
        mock_svc.update_task_status.return_value = {}
        mock_svc_cls.return_value = mock_svc

        mock_http_instance = MagicMock()
        mock_httpx_cls.return_value.__enter__ = MagicMock(return_value=mock_http_instance)
        mock_httpx_cls.return_value.__exit__ = MagicMock(return_value=False)

        strava_activities = [
            {
                "id": 1001,
                "type": "Run",
                "start_date": "2026-02-15T08:00:00Z",
                "moving_time": 1800,
                "distance": 5000.0,
                "average_heartrate": 150,
                "max_heartrate": 175,
                "total_elevation_gain": 30.0,
            },
            {
                "id": 1002,
                "type": "Run",
                "start_date": "2026-02-16T08:00:00Z",
                "moving_time": 2400,
                "distance": 8000.0,
                "average_heartrate": 148,
                "max_heartrate": 170,
                "total_elevation_gain": 45.0,
            },
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = strava_activities
        mock_http_instance.get.return_value = mock_resp

        from app.tasks.sync_tasks import backfill_history
        result = backfill_history("user-123", "strava")
        assert result["status"] == "completed"
        assert result["activities_imported"] == 2
        assert result["activities_valid"] >= 0


class TestStructuralDecayDetailed:
    """G5: Test structural_decay_check with inactive user scenarios."""

    @patch("app.services.notification_service.NotificationService")
    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_structural_decay_check_inactive_user(self, mock_sb, mock_svc_cls, mock_ns_cls):
        """Mock inactive user (21+ days); verify notification dispatched."""
        mock_sb.return_value = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [
            {"user_id": "inactive-user-1"},
        ]
        mock_svc.get_recent_activities.return_value = []
        mock_svc.get_latest_projection.return_value = {
            "midpoint_seconds": 1200,
            "range_lower": 1150,
            "range_upper": 1250,
            "range_low_seconds": 1150,
            "range_high_seconds": 1250,
            "confidence_score": 0.7,
            "volatility_score": 0,
            "status": "Holding",
        }
        mock_svc.insert_projection.return_value = {}
        mock_svc_cls.return_value = mock_svc

        mock_ns = MagicMock()
        mock_ns.dispatch.return_value = {}
        mock_ns_cls.return_value = mock_ns

        from app.tasks.projection_tasks import structural_decay_check
        result = structural_decay_check()
        assert result["status"] == "completed"
        assert result["users_checked"] == 1
        assert result["users_decayed"] >= 1
        assert result["users_stale"] >= 1

        mock_ns.dispatch.assert_called_once()
        call_args = mock_ns.dispatch.call_args
        assert call_args[0][0] == "inactive-user-1"
        payload = call_args[0][1]
        assert payload.notification_type == "intervention"
        assert "Declining" in payload.title


class TestWeeklySummaryDetailed:
    """G5: Test weekly_summary with active user."""

    @patch("app.services.notification_service.NotificationService")
    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_weekly_summary_generates_notification(self, mock_sb, mock_svc_cls, mock_ns_cls):
        """Mock user with activities; verify summary notification dispatched."""
        mock_sb.return_value = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [
            {"user_id": "active-user-1"},
        ]
        mock_svc.get_activities_since.return_value = [
            {"distance_meters": 5000, "duration_seconds": 1800},
            {"distance_meters": 8000, "duration_seconds": 2700},
            {"distance_meters": 12000, "duration_seconds": 4200},
        ]
        mock_svc.get_latest_projection.return_value = {
            "midpoint_seconds": 1200,
            "status": "Holding",
        }
        mock_svc.get_latest_drivers.return_value = [
            {"aerobic_base_seconds": 7.5, "threshold_density_seconds": 6.2, "speed_exposure_seconds": 8.0, "load_consistency_seconds": 4.1, "running_economy_seconds": 5.5},
        ]
        mock_svc.get_feature_history.return_value = []
        mock_svc_cls.return_value = mock_svc

        mock_ns = MagicMock()
        mock_ns.dispatch.return_value = {}
        mock_ns.build_weekly_summary.return_value = MagicMock(notification_type="weekly_summary", title="Weekly Summary", body="3 sessions", deep_link="/performance")
        mock_ns_cls.return_value = mock_ns

        from app.tasks.projection_tasks import weekly_summary
        result = weekly_summary()
        assert result["status"] == "completed"
        assert result["summaries_sent"] == 1

        mock_ns.dispatch.assert_called_once()
        call_args = mock_ns.dispatch.call_args
        assert call_args[0][0] == "active-user-1"

    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_weekly_summary_skips_inactive_users(self, mock_sb, mock_svc_cls):
        """Users with no activities in last 7 days should be skipped."""
        mock_sb.return_value = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [
            {"user_id": "inactive-user"},
        ]
        mock_svc.get_activities_since.return_value = []
        mock_svc_cls.return_value = mock_svc

        from app.tasks.projection_tasks import weekly_summary
        result = weekly_summary()
        assert result["status"] == "completed"
        assert result["summaries_sent"] == 0
        mock_svc.insert_notification.assert_not_called()


class TestBiasCorrectionDetailed:
    """G5: Test bias_correction with race + projection."""

    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_bias_correction_logs_metric(self, mock_sb, mock_svc_cls):
        """Mock race + projection; verify model_metrics logged when bias > 10s."""
        mock_sb.return_value = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [
            {"user_id": "racer-1"},
        ]
        mock_svc.get_race_activities.return_value = [
            {
                "distance_meters": 5050,
                "duration_seconds": 1250,
                "timestamp": "2026-02-20T09:00:00Z",
            },
        ]
        mock_svc.get_latest_projection.return_value = {
            "midpoint_seconds": 1200,
        }
        mock_svc.insert_model_metric.return_value = {}
        mock_svc_cls.return_value = mock_svc

        from app.tasks.projection_tasks import bias_correction
        result = bias_correction()
        assert result["status"] == "completed"
        assert result["users_corrected"] == 1
        assert result["biases_logged"] == 1

        mock_svc.insert_model_metric.assert_called_once()
        metric_data = mock_svc.insert_model_metric.call_args[0][0]
        assert metric_data["metric_type"] == "bias_correction"
        assert metric_data["event"] == "5000"
        assert metric_data["actual_seconds"] == 1250
        assert metric_data["projected_seconds"] == 1200
        assert metric_data["bias_seconds"] == 50

    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_bias_correction_half_marathon(self, mock_sb, mock_svc_cls):
        """Half-marathon race distances should map to event 21097."""
        mock_sb.return_value = MagicMock()
        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [{"user_id": "hm-racer"}]
        mock_svc.get_race_activities.return_value = [
            {"distance_meters": 21100, "duration_seconds": 5400, "timestamp": "2026-02-20T09:00:00Z"},
        ]
        mock_svc.get_latest_projection.return_value = {"midpoint_seconds": 5200}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc_cls.return_value = mock_svc

        result = bias_correction()
        assert result["users_corrected"] == 1
        assert result["biases_logged"] == 1
        metric_data = mock_svc.insert_model_metric.call_args[0][0]
        assert metric_data["event"] == "21097"

    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_bias_correction_marathon(self, mock_sb, mock_svc_cls):
        """Marathon race distances should map to event 42195."""
        mock_sb.return_value = MagicMock()
        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [{"user_id": "marathon-racer"}]
        mock_svc.get_race_activities.return_value = [
            {"distance_meters": 42200, "duration_seconds": 12600, "timestamp": "2026-02-20T09:00:00Z"},
        ]
        mock_svc.get_latest_projection.return_value = {"midpoint_seconds": 12000}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc_cls.return_value = mock_svc

        result = bias_correction()
        assert result["users_corrected"] == 1
        assert result["biases_logged"] == 1
        metric_data = mock_svc.insert_model_metric.call_args[0][0]
        assert metric_data["event"] == "42195"

    @patch("app.services.supabase_client.SupabaseService")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_bias_correction_skips_small_bias(self, mock_sb, mock_svc_cls):
        """If bias < 10s, no model_metric should be logged."""
        mock_sb.return_value = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get_onboarded_users.return_value = [
            {"user_id": "racer-2"},
        ]
        mock_svc.get_race_activities.return_value = [
            {
                "distance_meters": 5000,
                "duration_seconds": 1205,
                "timestamp": "2026-02-20T09:00:00Z",
            },
        ]
        mock_svc.get_latest_projection.return_value = {
            "midpoint_seconds": 1200,
        }
        mock_svc_cls.return_value = mock_svc

        from app.tasks.projection_tasks import bias_correction
        result = bias_correction()
        assert result["status"] == "completed"
        assert result["users_corrected"] == 1
        assert result["biases_logged"] == 0
        mock_svc.insert_model_metric.assert_not_called()
