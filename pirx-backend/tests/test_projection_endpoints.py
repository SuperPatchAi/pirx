import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth():
    """Override auth so tests don't need real JWT."""
    async def _mock_user():
        return {"user_id": "test-user"}

    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class TestProjectionEndpoints:
    def test_get_projection(self, client):
        r = client.get("/projection?event=5000")
        assert r.status_code == 200
        data = r.json()
        assert data["event"] == "5000"
        assert "projected_time_seconds" in data
        assert "projected_time_display" in data
        assert "supported_range_low" in data
        assert "supported_range_high" in data
        assert "supported_range_display" in data
        assert isinstance(data["projected_time_seconds"], (int, float))

    def test_get_projection_default_event(self, client):
        r = client.get("/projection")
        assert r.status_code == 200
        assert r.json()["event"] == "5000"

    def test_get_projection_history(self, client):
        r = client.get("/projection/history?event=5000&days=30")
        assert r.status_code == 200
        data = r.json()
        assert data["event"] == "5000"
        assert data["days"] == 30
        assert isinstance(data["history"], list)

    def test_get_trajectory_empty_when_no_data(self, client):
        r = client.get("/projection/trajectory?event=5000")
        assert r.status_code == 200
        data = r.json()
        assert data["event"] == "5000"
        assert isinstance(data["scenarios"], list)
        assert len(data["scenarios"]) == 0


class TestDriverEndpoints:
    def test_get_drivers(self, client):
        r = client.get("/drivers?event=5000")
        assert r.status_code == 200
        data = r.json()
        assert data["event"] == "5000"
        assert isinstance(data["drivers"], list)

    def test_get_driver_detail(self, client):
        r = client.get("/drivers/aerobic_base?days=30")
        assert r.status_code == 200
        data = r.json()
        assert data["driver_name"] == "aerobic_base"
        assert data["display_name"] == "Aerobic Base"
        assert isinstance(data["history"], list)
        assert "score" in data
        assert "trend" in data

    def test_explain_driver(self, client):
        r = client.get("/drivers/aerobic_base/explain")
        assert r.status_code == 200
        data = r.json()
        assert data["driver_name"] == "aerobic_base"
        assert isinstance(data["top_factors"], list)
        assert "summary" in data

    def test_all_drivers_have_display_names(self, client):
        r = client.get("/drivers")
        for driver in r.json()["drivers"]:
            assert driver["display_name"] != ""
            assert driver["trend"] in ("improving", "stable", "declining")
            assert driver["trend_emoji"] in ("↑", "→", "↓")
