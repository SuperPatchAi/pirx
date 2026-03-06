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
        assert data["projected_time_seconds"] > 0

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
        assert len(data["history"]) > 0
        assert "date" in data["history"][0]
        assert "projected_time_seconds" in data["history"][0]

    def test_get_trajectory(self, client):
        r = client.get("/projection/trajectory?event=5000")
        assert r.status_code == 200
        data = r.json()
        assert len(data["scenarios"]) == 3
        labels = [s["label"] for s in data["scenarios"]]
        assert labels == ["Maintain", "Push", "Ease Off"]
        for s in data["scenarios"]:
            assert "confidence" in s
            assert "delta_seconds" in s


class TestDriverEndpoints:
    def test_get_drivers(self, client):
        r = client.get("/drivers?event=5000")
        assert r.status_code == 200
        data = r.json()
        assert data["event"] == "5000"
        assert len(data["drivers"]) == 5
        names = {d["driver_name"] for d in data["drivers"]}
        assert names == {
            "aerobic_base",
            "threshold_density",
            "speed_exposure",
            "running_economy",
            "load_consistency",
        }
        # Verify drivers sum to total
        total = sum(d["contribution_seconds"] for d in data["drivers"])
        assert total == pytest.approx(data["total_improvement_seconds"], abs=0.1)

    def test_get_driver_detail(self, client):
        r = client.get("/drivers/aerobic_base?days=30")
        assert r.status_code == 200
        data = r.json()
        assert data["driver_name"] == "aerobic_base"
        assert data["display_name"] == "Aerobic Base"
        assert len(data["history"]) > 0
        assert "score" in data
        assert "trend" in data

    def test_explain_driver(self, client):
        r = client.get("/drivers/aerobic_base/explain")
        assert r.status_code == 200
        data = r.json()
        assert data["driver_name"] == "aerobic_base"
        assert len(data["top_factors"]) > 0
        assert "summary" in data

    def test_all_drivers_have_display_names(self, client):
        r = client.get("/drivers")
        for driver in r.json()["drivers"]:
            assert driver["display_name"] != ""
            assert driver["trend"] in ("improving", "stable", "declining")
            assert driver["trend_emoji"] in ("↑", "→", "↓")
