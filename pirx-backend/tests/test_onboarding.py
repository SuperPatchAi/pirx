from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app


MOCK_USER = {"user_id": "test-user-onboard", "email": "onboard@pirx.com"}


async def _mock_user():
    return MOCK_USER


def _make_client() -> TestClient:
    app.dependency_overrides[get_current_user] = _mock_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Detect Baseline
# ---------------------------------------------------------------------------


class TestDetectBaseline:
    def test_detect_baseline_with_races(self):
        """Mock get_race_activities to return races; verify best race is returned."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_race_activities.return_value = [
                    {
                        "distance_meters": 5000,
                        "elapsed_time_seconds": 1200,
                        "timestamp": "2026-02-01T08:00:00Z",
                    },
                    {
                        "distance_meters": 10000,
                        "elapsed_time_seconds": 2700,
                        "timestamp": "2026-01-15T09:00:00Z",
                    },
                ]
                mock_cls.return_value = inst

                r = client.post("/onboarding/detect-baseline")
                assert r.status_code == 200
                data = r.json()
                assert data["baseline_source"] == "race_history"
                assert data["baseline_time_seconds"] == 1200
                assert data["baseline_event"] == "5000"
                assert len(data["detected_races"]) == 2
        finally:
            _cleanup()

    def test_detect_baseline_no_races(self):
        """Mock empty races; verify cold-start default (5K 1500s)."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_race_activities.return_value = []
                mock_cls.return_value = inst

                r = client.post("/onboarding/detect-baseline")
                assert r.status_code == 200
                data = r.json()
                assert data["baseline_source"] == "cold_start"
                assert data["baseline_event"] == "5000"
                assert data["baseline_time_seconds"] == 1500.0
                assert data["detected_races"] == []
        finally:
            _cleanup()

    def test_detect_baseline_db_error_fallback(self):
        """If DB throws, should still return cold-start default."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_race_activities.side_effect = Exception("db down")
                mock_cls.return_value = inst

                r = client.post("/onboarding/detect-baseline")
                assert r.status_code == 200
                data = r.json()
                assert data["baseline_source"] == "cold_start"
        finally:
            _cleanup()

    def test_detect_baseline_picks_fastest(self):
        """When multiple races exist, the fastest (lowest time) is chosen."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_race_activities.return_value = [
                    {"distance_meters": 5000, "elapsed_time_seconds": 1400, "timestamp": "2026-01-01"},
                    {"distance_meters": 5000, "elapsed_time_seconds": 1100, "timestamp": "2026-02-01"},
                    {"distance_meters": 5000, "elapsed_time_seconds": 1300, "timestamp": "2026-03-01"},
                ]
                mock_cls.return_value = inst

                r = client.post("/onboarding/detect-baseline")
                data = r.json()
                assert data["baseline_time_seconds"] == 1100
        finally:
            _cleanup()


# ---------------------------------------------------------------------------
# Set Baseline
# ---------------------------------------------------------------------------


class TestSetBaseline:
    def test_set_baseline_writes_to_db(self):
        """Verify the endpoint calls the DB update."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.post(
                    "/onboarding/set-baseline",
                    json={"event": "10000", "time_seconds": 2520.0, "source": "manual"},
                )
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "ok"
                assert data["baseline_event"] == "10000"
                assert data["baseline_time_seconds"] == 2520.0

                inst.client.table.assert_called_with("users")
        finally:
            _cleanup()

    def test_set_baseline_db_failure_returns_500(self):
        """If DB update throws, endpoint should return 500."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.client.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
                    Exception("db error")
                )
                mock_cls.return_value = inst

                r = client.post(
                    "/onboarding/set-baseline",
                    json={"event": "5000", "time_seconds": 1200.0},
                )
                assert r.status_code == 500
        finally:
            _cleanup()


# ---------------------------------------------------------------------------
# Generate Projection
# ---------------------------------------------------------------------------


class TestGenerateProjection:
    def test_generate_projection_creates_states(self):
        """Mock user with baseline; verify projections and drivers are created."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "baseline_event": "5000",
                    "baseline_time_seconds": 1200.0,
                }
                inst.insert_projection.side_effect = lambda data: data
                inst.insert_driver_state.return_value = {}
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                r = client.post(
                    "/onboarding/generate-projection",
                    json={"primary_event": "5000"},
                )
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "ok"
                assert data["primary_event"] == "5000"
                assert "all_projections" in data

                for event in ("1500", "3000", "5000", "10000", "21097", "42195"):
                    assert event in data["all_projections"]

                assert inst.insert_projection.call_count == 6
                inst.insert_driver_state.assert_called_once()

        finally:
            _cleanup()

    def test_generate_projection_user_not_found(self):
        """If user doesn't exist, should return 404."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = None
                mock_cls.return_value = inst

                r = client.post(
                    "/onboarding/generate-projection",
                    json={"primary_event": "5000"},
                )
                assert r.status_code == 404
        finally:
            _cleanup()

    def test_generate_projection_no_baseline_set(self):
        """If baseline not set, should return 400."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "baseline_event": None,
                    "baseline_time_seconds": None,
                }
                mock_cls.return_value = inst

                r = client.post(
                    "/onboarding/generate-projection",
                    json={"primary_event": "5000"},
                )
                assert r.status_code == 400
        finally:
            _cleanup()

    def test_generate_projection_riegel_scaling(self):
        """Verify projected times use Riegel scaling from the baseline event."""
        client = _make_client()
        try:
            with patch("app.routers.onboarding.SupabaseService") as mock_cls:
                inst = MagicMock()
                inst.get_user.return_value = {
                    "user_id": MOCK_USER["user_id"],
                    "baseline_event": "5000",
                    "baseline_time_seconds": 1200.0,
                }
                captured_projections = {}

                def capture_insert(data):
                    captured_projections[data["event"]] = data
                    return data

                inst.insert_projection.side_effect = capture_insert
                inst.insert_driver_state.return_value = {}
                mock_exec = MagicMock()
                mock_exec.data = [{}]
                inst.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_exec
                mock_cls.return_value = inst

                client.post(
                    "/onboarding/generate-projection",
                    json={"primary_event": "5000"},
                )

                assert captured_projections["5000"]["midpoint_seconds"] == 1200.0

                ten_k = captured_projections["10000"]["midpoint_seconds"]
                assert ten_k > 1200.0
                assert ten_k < 3000.0

                fifteen = captured_projections["1500"]["midpoint_seconds"]
                assert fifteen < 1200.0
        finally:
            _cleanup()
