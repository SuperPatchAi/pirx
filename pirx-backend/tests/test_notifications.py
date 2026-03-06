import pytest
from unittest.mock import MagicMock, patch

from app.services.notification_service import (
    NotificationPayload,
    NotificationService,
    TRIGGER_THRESHOLDS,
    TRIGGER_TYPES,
)


class TestProjectionUpdateTrigger:
    def test_triggers_on_large_delta(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_projection_update("u1", "5000", 1200, 1195)
        assert result is not None
        assert result.notification_type == "projection_update"
        assert "faster" in result.body

    def test_no_trigger_on_small_delta(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_projection_update("u1", "5000", 1200, 1199)
        assert result is None

    def test_slower_direction(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_projection_update("u1", "5000", 1195, 1200)
        assert result is not None
        assert "slower" in result.body


class TestReadinessShift:
    def test_triggers_on_large_shift(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_readiness_shift("u1", 70, 80)
        assert result is not None
        assert "improved" in result.body

    def test_no_trigger_on_small_shift(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_readiness_shift("u1", 70, 73)
        assert result is None

    def test_decline_direction(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_readiness_shift("u1", 80, 70)
        assert result is not None
        assert "declined" in result.body


class TestIntervention:
    def test_triggers_high_acwr(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_intervention("u1", 1.8)
        assert result is not None
        assert "ACWR" in result.body

    def test_no_trigger_normal_acwr(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.check_intervention("u1", 1.1)
        assert result is None


class TestWeeklySummary:
    def test_builds_summary(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.build_weekly_summary("u1", 45.0, 5, 3.0)
        assert result.notification_type == "weekly_summary"
        assert "45km" in result.body
        assert "5 sessions" in result.body


class TestRaceApproaching:
    def test_builds_race_notification(self):
        svc = NotificationService.__new__(NotificationService)
        result = svc.build_race_approaching("u1", "5000", 7)
        assert result.notification_type == "race_approaching"
        assert "7 days" in result.body


class TestTriggerTypes:
    def test_all_types_defined(self):
        assert len(TRIGGER_TYPES) == 6
        assert "projection_update" in TRIGGER_TYPES
        assert "new_insight" in TRIGGER_TYPES


class TestNotificationEndpoint:
    def test_get_notifications_endpoint(self):
        from fastapi.testclient import TestClient

        from app.dependencies import get_current_user
        from app.main import app

        async def mock_user():
            return {"user_id": "test", "email": "test@pirx.com"}

        app.dependency_overrides[get_current_user] = mock_user
        try:
            client = TestClient(app)
            with patch(
                "app.services.notification_service.SupabaseService"
            ) as mock_db:
                mock_instance = MagicMock()
                mock_instance.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = (
                    []
                )
                mock_db.return_value = mock_instance

                r = client.get("/notifications")
                assert r.status_code == 200
                data = r.json()
                assert "notifications" in data
                assert "unread_count" in data
        finally:
            app.dependency_overrides.clear()
