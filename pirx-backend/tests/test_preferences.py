from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app


MOCK_USER = {"user_id": "test-user-prefs", "email": "prefs@pirx.com"}


async def _mock_user():
    return MOCK_USER


def _make_client() -> TestClient:
    app.dependency_overrides[get_current_user] = _mock_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


class TestGetPreferences:
    def test_get_preferences_default(self):
        """When user has no custom_fields, return all defaults (True)."""
        client = _make_client()
        try:
            with patch("app.routers.preferences.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = None
                mock_cls.return_value = inst

                r = client.get("/preferences")
                assert r.status_code == 200
                data = r.json()
                assert data["projection_shifts"] is True
                assert data["readiness_changes"] is True
                assert data["intervention_alerts"] is True
                assert data["weekly_summary"] is True
                assert data["race_reminders"] is True
                assert data["new_insights"] is True
        finally:
            _cleanup()

    def test_get_preferences_from_db(self):
        """When user has stored preferences, return those values."""
        client = _make_client()
        try:
            with patch("app.routers.preferences.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "custom_fields": {
                        "notification_preferences": {
                            "projection_shifts": False,
                            "readiness_changes": True,
                            "intervention_alerts": False,
                            "weekly_summary": True,
                            "race_reminders": False,
                            "new_insights": True,
                        }
                    },
                }
                mock_cls.return_value = inst

                r = client.get("/preferences")
                assert r.status_code == 200
                data = r.json()
                assert data["projection_shifts"] is False
                assert data["readiness_changes"] is True
                assert data["intervention_alerts"] is False
                assert data["race_reminders"] is False
        finally:
            _cleanup()

    def test_get_preferences_empty_custom_fields(self):
        """User exists but custom_fields is None — returns defaults."""
        client = _make_client()
        try:
            with patch("app.routers.preferences.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "custom_fields": None,
                }
                mock_cls.return_value = inst

                r = client.get("/preferences")
                assert r.status_code == 200
                data = r.json()
                assert data["projection_shifts"] is True
        finally:
            _cleanup()


class TestUpdatePreferences:
    def test_update_preferences(self):
        """PUT /preferences writes to DB and returns updated values."""
        client = _make_client()
        try:
            with patch("app.routers.preferences.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "custom_fields": {},
                }
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                payload = {
                    "projection_shifts": False,
                    "readiness_changes": False,
                    "intervention_alerts": True,
                    "weekly_summary": False,
                    "race_reminders": True,
                    "new_insights": False,
                }
                r = client.put("/preferences", json=payload)
                assert r.status_code == 200
                data = r.json()
                assert data["projection_shifts"] is False
                assert data["readiness_changes"] is False
                assert data["intervention_alerts"] is True
                assert data["weekly_summary"] is False

                inst.client.table.assert_called_with("users")
                update_call = inst.client.table.return_value.update
                update_call.assert_called_once()
                update_args = update_call.call_args[0][0]
                assert "custom_fields" in update_args
                prefs = update_args["custom_fields"]["notification_preferences"]
                assert prefs["projection_shifts"] is False
                assert prefs["race_reminders"] is True
        finally:
            _cleanup()

    def test_update_preferences_preserves_existing_custom_fields(self):
        """Existing custom_fields keys outside notification_preferences are preserved."""
        client = _make_client()
        try:
            with patch("app.routers.preferences.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "custom_fields": {
                        "theme": "dark",
                        "notification_preferences": {"projection_shifts": True},
                    },
                }
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.put(
                    "/preferences",
                    json={"projection_shifts": False},
                )
                assert r.status_code == 200

                update_args = inst.client.table.return_value.update.call_args[0][0]
                assert update_args["custom_fields"]["theme"] == "dark"
                assert update_args["custom_fields"]["notification_preferences"]["projection_shifts"] is False
        finally:
            _cleanup()

    def test_update_preferences_db_error_still_returns(self):
        """Even if DB write fails, endpoint still returns the body (exception swallowed)."""
        client = _make_client()
        try:
            with patch("app.routers.preferences.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {"user_id": MOCK_USER["user_id"], "custom_fields": {}}
                inst.client.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("db")
                mock_cls.return_value = inst

                r = client.put(
                    "/preferences",
                    json={"projection_shifts": True, "weekly_summary": False},
                )
                assert r.status_code == 200
                data = r.json()
                assert data["projection_shifts"] is True
                assert data["weekly_summary"] is False
        finally:
            _cleanup()
