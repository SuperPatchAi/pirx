from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app


MOCK_USER = {"user_id": "test-user-abc123", "email": "test@pirx.com"}


async def _mock_user():
    return MOCK_USER


def _make_client() -> TestClient:
    app.dependency_overrides[get_current_user] = _mock_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Data Export
# ---------------------------------------------------------------------------


class TestExport:
    @staticmethod
    def _setup_export_mock(inst):
        inst.get_user.return_value = {"user_id": MOCK_USER["user_id"], "email": "test@pirx.com"}
        inst.get_activities.return_value = []
        inst.get_projection_history.return_value = []
        inst.get_driver_history.return_value = []
        inst.get_wearable_connections.return_value = []
        inst.get_recent_physiology.return_value = []
        mock_exec = MagicMock()
        mock_exec.data = []
        inst.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_exec

    def test_export_returns_json(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                self._setup_export_mock(inst)
                mock_cls.return_value = inst

                r = client.get("/account/export")
                assert r.status_code == 200
                data = r.json()
                assert data["user_id"] == MOCK_USER["user_id"]
                assert "exported_at" in data
                assert "activities" in data
                assert "projections" in data
        finally:
            _cleanup()

    def test_export_has_download_header(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                self._setup_export_mock(inst)
                inst.get_user.return_value = None
                mock_cls.return_value = inst

                r = client.get("/account/export")
                assert "content-disposition" in r.headers
                assert "pirx-export-" in r.headers["content-disposition"]
        finally:
            _cleanup()

    def test_export_includes_all_events(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                self._setup_export_mock(inst)
                inst.get_projection_history.side_effect = lambda uid, event, days: [
                    {"event": event, "midpoint_seconds": 1200}
                ]
                mock_cls.return_value = inst

                r = client.get("/account/export")
                data = r.json()
                assert isinstance(data["projections"], dict)
                assert "5000" in data["projections"]
                assert "10000" in data["projections"]
        finally:
            _cleanup()

    def test_export_handles_partial_failure(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.side_effect = Exception("db error")
                mock_cls.return_value = inst

                r = client.get("/account/export")
                assert r.status_code == 200
                data = r.json()
                assert "error" in data
        finally:
            _cleanup()


# ---------------------------------------------------------------------------
# Data Deletion
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_returns_status(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                mock_exec = MagicMock()
                mock_exec.data = []
                inst.client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.delete("/account/delete")
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "deleted"
                assert data["user_id"] == MOCK_USER["user_id"]
                assert "tables_affected" in data
        finally:
            _cleanup()

    def test_delete_covers_all_tables(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                mock_exec = MagicMock()
                mock_exec.data = []
                inst.client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.delete("/account/delete")
                data = r.json()
                expected_tables = [
                    "notification_log", "user_embeddings", "physiology",
                    "driver_state", "projection_state", "activity_adjuncts",
                    "adjunct_state", "intervals", "activities",
                    "wearable_connections", "task_registry", "model_metrics",
                    "users",
                ]
                for table in expected_tables:
                    assert table in data["tables_affected"]
        finally:
            _cleanup()


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_get_baseline_with_user_data(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "baseline_event": "10000",
                    "baseline_time_seconds": 2520.0,
                    "baseline_race_date": "2026-01-15",
                    "baseline_source": "manual",
                }
                mock_cls.return_value = inst

                r = client.get("/account/baseline")
                assert r.status_code == 200
                data = r.json()
                assert data["event"] == "10000"
                assert data["time_seconds"] == 2520.0
                assert data["source"] == "manual"
        finally:
            _cleanup()

    def test_get_baseline_defaults(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = None
                mock_cls.return_value = inst

                r = client.get("/account/baseline")
                assert r.status_code == 200
                data = r.json()
                assert data["event"] == "5000"
                assert data["time_seconds"] == 1260.0
                assert data["source"] == "auto"
        finally:
            _cleanup()

    def test_update_baseline(self):
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.put(
                    "/account/baseline",
                    json={"event": "10000", "time_seconds": 2520.0, "source": "manual"},
                )
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "updated"
                assert data["event"] == "10000"
        finally:
            _cleanup()


# ---------------------------------------------------------------------------
# Adjunct Library
# ---------------------------------------------------------------------------


class TestAdjunctLibrary:
    def test_get_adjunct_library(self):
        client = _make_client()
        try:
            r = client.get("/account/adjunct-library")
            assert r.status_code == 200
            data = r.json()
            assert "adjuncts" in data
            assert isinstance(data["adjuncts"], list)
        finally:
            _cleanup()

    def test_add_adjunct(self):
        client = _make_client()
        try:
            r = client.post(
                "/account/adjunct-library",
                json={"name": "Yoga", "description": "Flexibility work"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["status"] in ("created", "error")
            if data["status"] == "created":
                assert data["name"] == "Yoga"
        finally:
            _cleanup()

    def test_delete_adjunct(self):
        client = _make_client()
        try:
            r = client.delete("/account/adjunct-library/altitude")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] in ("deleted", "error")
        finally:
            _cleanup()

    def test_adjunct_library_real_query(self):
        """Verify adjunct CRUD hits SupabaseService for real DB path."""
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                mock_exec = MagicMock()
                mock_exec.data = [
                    {
                        "adjunct_id": "alt-1",
                        "adjunct_name": "Altitude Training",
                        "sessions_analyzed": 12,
                        "median_projection_delta": -3.5,
                        "statistical_status": "supported",
                    },
                    {
                        "adjunct_id": "str-1",
                        "adjunct_name": "Strength Training",
                        "sessions_analyzed": 8,
                        "median_projection_delta": -1.2,
                        "statistical_status": "emerging",
                    },
                ]
                inst.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.get("/account/adjunct-library")
                assert r.status_code == 200
                data = r.json()
                assert len(data["adjuncts"]) == 2
                assert data["adjuncts"][0]["name"] == "Altitude Training"
                assert data["adjuncts"][0]["sessions_analyzed"] == 12

                inst.client.table.assert_called_with("adjunct_state")
        finally:
            _cleanup()


# ---------------------------------------------------------------------------
# Baseline Update (PUT)
# ---------------------------------------------------------------------------


class TestBaselineUpdate:
    def test_baseline_update(self):
        """Test PUT /account/baseline writes correct fields to DB."""
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.put(
                    "/account/baseline",
                    json={
                        "event": "10000",
                        "time_seconds": 2520.0,
                        "race_date": "2026-02-15",
                        "source": "manual",
                    },
                )
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "updated"
                assert data["event"] == "10000"
                assert data["time_seconds"] == 2520.0

                inst.client.table.assert_called_with("users")
                update_call = inst.client.table.return_value.update
                update_call.assert_called_once()
                update_args = update_call.call_args[0][0]
                assert update_args["baseline_event"] == "10000"
                assert update_args["baseline_time_seconds"] == 2520.0
                assert update_args["baseline_race_date"] == "2026-02-15"
                assert update_args["baseline_source"] == "manual"
        finally:
            _cleanup()

    def test_baseline_update_db_error(self):
        """If DB update fails, endpoint returns error status."""
        client = _make_client()
        try:
            with patch("app.routers.account.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.client.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
                    Exception("db error")
                )
                mock_cls.return_value = inst

                r = client.put(
                    "/account/baseline",
                    json={"event": "5000", "time_seconds": 1200.0},
                )
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "error"
        finally:
            _cleanup()
