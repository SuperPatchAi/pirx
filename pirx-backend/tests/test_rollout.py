from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth():
    async def _mock_user():
        return {"user_id": "test-user"}

    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class TestRolloutConfigEndpoint:
    @patch("app.routers.rollout.settings")
    def test_get_rollout_config(self, mock_settings, client):
        mock_settings.enable_lstm_serving = True
        mock_settings.enable_knn_serving = False
        mock_settings.lstm_serving_rollout_percentage = 35

        r = client.get("/rollout/config")
        assert r.status_code == 200
        data = r.json()
        assert data["enable_lstm_serving"] is True
        assert data["enable_knn_serving"] is False
        assert data["lstm_serving_rollout_percentage"] == 35


class TestServingMetricsEndpoint:
    @patch("app.routers.rollout.SupabaseService")
    def test_get_serving_metrics_aggregates_counts(self, mock_svc_cls, client):
        mock_db = MagicMock()
        mock_svc_cls.return_value = mock_db
        mock_result = MagicMock()
        mock_result.data = [
            {"model_type": "event_5000", "metric_type": "model_serving_decision", "event": "5000", "sample_size": None},
            {"model_type": "event_5000", "metric_type": "model_serving_decision", "event": "5000", "sample_size": None},
            {"model_type": "event_10000", "metric_type": "model_serving_decision", "event": "10000", "sample_size": None},
            {"model_type": "event_5000", "metric_type": "model_serving_decision", "event": "5000", "sample_size": None},
        ]
        (
            mock_db.client.table.return_value.select.return_value
            .eq.return_value.gte.return_value.order.return_value
            .limit.return_value.execute.return_value
        ) = mock_result

        r = client.get("/rollout/metrics")
        assert r.status_code == 200
        data = r.json()
        assert data["total_decisions"] == 4
        assert data["event_counts"]["5000"] == 3
        assert data["event_counts"]["10000"] == 1
