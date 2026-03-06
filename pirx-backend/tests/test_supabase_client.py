"""Tests for SupabaseService — all Supabase calls are mocked."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.supabase_client import SupabaseService, get_supabase_client


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear the singleton cache between tests so the mock is picked up."""
    get_supabase_client.cache_clear()
    yield
    get_supabase_client.cache_clear()


@pytest.fixture
def mock_supabase():
    with patch("app.services.supabase_client.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestUserOperations:
    def test_get_user_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"user_id": "u1", "email": "a@b.com"}
        ]
        svc = SupabaseService()
        user = svc.get_user("u1")
        assert user["user_id"] == "u1"
        assert user["email"] == "a@b.com"

    def test_get_user_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        svc = SupabaseService()
        assert svc.get_user("unknown") is None

    def test_upsert_user(self, mock_supabase):
        mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [
            {"user_id": "u1", "email": "a@b.com"}
        ]
        svc = SupabaseService()
        result = svc.upsert_user("u1", "a@b.com")
        assert result["user_id"] == "u1"

    def test_upsert_user_fallback_when_empty(self, mock_supabase):
        mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = []
        svc = SupabaseService()
        result = svc.upsert_user("u1", "a@b.com")
        assert result["user_id"] == "u1"
        assert result["email"] == "a@b.com"


class TestActivityOperations:
    def test_insert_activity(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"activity_id": "a1", "user_id": "u1", "distance_meters": 5000}
        ]
        svc = SupabaseService()
        result = svc.insert_activity("u1", {"distance_meters": 5000})
        assert result["activity_id"] == "a1"

    def test_insert_activity_fallback(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = []
        svc = SupabaseService()
        result = svc.insert_activity("u1", {"distance_meters": 5000})
        assert result["user_id"] == "u1"
        assert result["distance_meters"] == 5000

    def test_get_activities(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.gte.return_value.order.return_value
            .limit.return_value.execute
        )
        chain.return_value.data = [
            {"activity_id": "a1", "timestamp": "2026-03-01T10:00:00Z"},
            {"activity_id": "a2", "timestamp": "2026-02-28T10:00:00Z"},
        ]
        svc = SupabaseService()
        results = svc.get_activities("u1", limit=50, days=30)
        assert len(results) == 2

    def test_get_race_activities(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.eq.return_value.order.return_value
            .limit.return_value.execute
        )
        chain.return_value.data = [{"activity_type": "race", "distance_meters": 5000}]
        svc = SupabaseService()
        races = svc.get_race_activities("u1")
        assert len(races) == 1
        assert races[0]["activity_type"] == "race"


class TestProjectionOperations:
    def test_get_latest_projection_found(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.eq.return_value.order.return_value
            .limit.return_value.execute
        )
        chain.return_value.data = [{"midpoint_seconds": 1182, "event": "5000"}]
        svc = SupabaseService()
        proj = svc.get_latest_projection("u1", "5000")
        assert proj["midpoint_seconds"] == 1182

    def test_get_latest_projection_not_found(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.eq.return_value.order.return_value
            .limit.return_value.execute
        )
        chain.return_value.data = []
        svc = SupabaseService()
        assert svc.get_latest_projection("u1", "5000") is None

    def test_get_projection_history(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.eq.return_value.gte.return_value
            .order.return_value.execute
        )
        chain.return_value.data = [
            {"midpoint_seconds": 1182, "computed_at": "2026-03-05T00:00:00Z"},
            {"midpoint_seconds": 1200, "computed_at": "2026-03-01T00:00:00Z"},
        ]
        svc = SupabaseService()
        history = svc.get_projection_history("u1", "5000", days=30)
        assert len(history) == 2

    def test_insert_projection(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"midpoint_seconds": 1182}
        ]
        svc = SupabaseService()
        result = svc.insert_projection({"user_id": "u1", "event": "5000", "midpoint_seconds": 1182})
        assert result["midpoint_seconds"] == 1182


class TestDriverOperations:
    def test_get_latest_drivers(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.order.return_value.limit.return_value.execute
        )
        chain.return_value.data = [
            {
                "aerobic_base_seconds": 23.4,
                "threshold_density_seconds": 19.5,
                "speed_exposure_seconds": 11.7,
                "running_economy_seconds": 12.2,
                "load_consistency_seconds": 11.2,
            }
        ]
        svc = SupabaseService()
        drivers = svc.get_latest_drivers("u1")
        assert len(drivers) == 1
        assert drivers[0]["aerobic_base_seconds"] == 23.4

    def test_get_latest_drivers_empty(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.order.return_value.limit.return_value.execute
        )
        chain.return_value.data = []
        svc = SupabaseService()
        assert svc.get_latest_drivers("u1") == []

    def test_get_driver_history(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.gte.return_value.order.return_value.execute
        )
        chain.return_value.data = [
            {"computed_at": "2026-03-05T00:00:00Z", "aerobic_base_seconds": 23.4},
            {"computed_at": "2026-03-01T00:00:00Z", "aerobic_base_seconds": 20.0},
        ]
        svc = SupabaseService()
        history = svc.get_driver_history("u1", days=30)
        assert len(history) == 2

    def test_insert_driver_state(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"aerobic_base_seconds": 23.4}
        ]
        svc = SupabaseService()
        result = svc.insert_driver_state({"user_id": "u1", "aerobic_base_seconds": 23.4})
        assert result["aerobic_base_seconds"] == 23.4


class TestWearableOperations:
    def test_get_wearable_connections(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"provider": "strava", "sync_status": "connected"}
        ]
        svc = SupabaseService()
        conns = svc.get_wearable_connections("u1")
        assert len(conns) == 1
        assert conns[0]["provider"] == "strava"

    def test_get_wearable_connections_empty(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        svc = SupabaseService()
        assert svc.get_wearable_connections("u1") == []

    def test_upsert_wearable_connection(self, mock_supabase):
        mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [
            {"provider": "strava", "sync_status": "connected"}
        ]
        svc = SupabaseService()
        result = svc.upsert_wearable_connection("u1", "strava", sync_status="connected")
        assert result["provider"] == "strava"


class TestPhysiologyOperations:
    def test_get_recent_physiology(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.order.return_value.limit.return_value.execute
        )
        chain.return_value.data = [
            {"resting_hr": 52, "hrv_ms": 65},
        ]
        svc = SupabaseService()
        phys = svc.get_recent_physiology("u1", limit=10)
        assert len(phys) == 1
        assert phys[0]["resting_hr"] == 52

    def test_get_recent_physiology_empty(self, mock_supabase):
        chain = (
            mock_supabase.table.return_value.select.return_value
            .eq.return_value.order.return_value.limit.return_value.execute
        )
        chain.return_value.data = []
        svc = SupabaseService()
        assert svc.get_recent_physiology("u1") == []


class TestNotificationOperations:
    def test_insert_notification(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"notification_type": "projection_shift", "title": "Projection Update"}
        ]
        svc = SupabaseService()
        result = svc.insert_notification("u1", "projection_shift", "Projection Update", "Your 5K improved")
        assert result["notification_type"] == "projection_shift"

    def test_insert_notification_with_deep_link(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"deep_link": "/projection?event=5000"}
        ]
        svc = SupabaseService()
        result = svc.insert_notification(
            "u1", "projection_shift", "Update", "Body", deep_link="/projection?event=5000"
        )
        assert result["deep_link"] == "/projection?event=5000"


class TestTaskRegistryOperations:
    def test_register_task(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"task_id": "t1", "status": "queued"}
        ]
        svc = SupabaseService()
        result = svc.register_task("u1", "compute_projection", "t1")
        assert result["task_id"] == "t1"
        assert result["status"] == "queued"

    def test_update_task_status_running(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"task_id": "t1", "status": "running"}
        ]
        svc = SupabaseService()
        result = svc.update_task_status("t1", "running")
        assert result["status"] == "running"

    def test_update_task_status_failed(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"task_id": "t1", "status": "failed", "error_message": "timeout"}
        ]
        svc = SupabaseService()
        result = svc.update_task_status("t1", "failed", error_message="timeout")
        assert result["status"] == "failed"

    def test_update_task_status_completed(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"task_id": "t1", "status": "completed"}
        ]
        svc = SupabaseService()
        result = svc.update_task_status("t1", "completed")
        assert result["status"] == "completed"
