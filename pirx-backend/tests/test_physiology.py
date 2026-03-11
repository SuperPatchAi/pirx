import pytest
from unittest.mock import MagicMock, patch

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


class TestPhysiologyEndpoints:
    def test_get_trends(self, client):
        with patch("app.routers.physiology.SupabaseService") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.get_recent_physiology.return_value = []
            mock_cls.return_value = mock_instance
            r = client.get("/physiology/trends?days=7")
            assert r.status_code == 200
            data = r.json()
            assert "entries" in data
            assert "period_days" in data
            assert data["period_days"] == 7
            assert isinstance(data["entries"], list)

    def test_get_trends_with_real_data(self, client):
        fake_entries = [
            {
                "entry_id": "e1",
                "timestamp": "2026-01-01T00:00:00Z",
                "resting_hr": 50,
                "custom_fields": {"weight_kg": 70.1, "body_fat_percentage": 14.0},
            }
        ]
        with patch("app.routers.physiology.SupabaseService") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.get_recent_physiology.return_value = fake_entries
            mock_cls.return_value = mock_instance
            r = client.get("/physiology/trends?days=30")
            assert r.status_code == 200
            data = r.json()
            assert data["entries"] == fake_entries
            assert data["entries"][0]["custom_fields"]["weight_kg"] == 70.1

    def test_get_latest(self, client):
        with patch("app.routers.physiology.SupabaseService") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.get_recent_physiology.return_value = []
            mock_cls.return_value = mock_instance
            r = client.get("/physiology/latest")
            assert r.status_code == 200
            data = r.json()
            assert "resting_hr" in data

    def test_create_entry(self, client):
        with patch("app.routers.physiology.SupabaseService") as mock_cls:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.data = [{"entry_id": "new-id"}]
            mock_instance.client.table.return_value.insert.return_value.execute.return_value = (
                mock_result
            )
            mock_cls.return_value = mock_instance
            r = client.post(
                "/physiology",
                json={
                    "resting_hr": 52,
                    "hrv": 45.0,
                    "sleep_score": 80.0,
                },
            )
            assert r.status_code == 200
            assert r.json()["status"] == "created"

    def test_create_entry_validation(self, client):
        r = client.post(
            "/physiology",
            json={"confidence_score": 15},
        )
        assert r.status_code == 422

    def test_create_entry_minimal(self, client):
        with patch("app.routers.physiology.SupabaseService") as mock_cls:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.data = [{"entry_id": "new-id"}]
            mock_instance.client.table.return_value.insert.return_value.execute.return_value = (
                mock_result
            )
            mock_cls.return_value = mock_instance
            r = client.post(
                "/physiology",
                json={"notes": "Feeling good today"},
            )
            assert r.status_code == 200

    def test_create_entry_boundary_scores(self, client):
        """Scores at exact boundaries (1 and 10) should pass validation."""
        with patch("app.routers.physiology.SupabaseService") as mock_cls:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.data = [{"entry_id": "new-id"}]
            mock_instance.client.table.return_value.insert.return_value.execute.return_value = (
                mock_result
            )
            mock_cls.return_value = mock_instance
            r = client.post(
                "/physiology",
                json={
                    "confidence_score": 1,
                    "fatigue_score": 10,
                    "focus_score": 5,
                },
            )
            assert r.status_code == 200

    def test_create_entry_score_below_min(self, client):
        r = client.post(
            "/physiology",
            json={"fatigue_score": 0},
        )
        assert r.status_code == 422
