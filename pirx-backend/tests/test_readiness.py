import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user
from app.ml.readiness_engine import ReadinessEngine, READINESS_WEIGHTS
from app.ml.injury_risk_model import InjuryRiskModel


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


def make_features(**overrides):
    base = {
        "acwr_4w": 1.1,
        "weekly_load_stddev": 4000,
        "session_density_stability": 0.8,
    }
    base.update(overrides)
    return base


class TestReadinessScore:
    def test_returns_0_to_100(self):
        result = ReadinessEngine.compute_readiness(make_features())
        assert 0 <= result.score <= 100

    def test_has_label(self):
        result = ReadinessEngine.compute_readiness(make_features())
        assert result.label in ("Peak", "Good", "Moderate", "Low", "Very Low")

    def test_has_components(self):
        result = ReadinessEngine.compute_readiness(make_features())
        for key in READINESS_WEIGHTS:
            assert key in result.components


class TestInjuryRiskCalibration:
    def test_risk_band_thresholds(self):
        assert InjuryRiskModel.get_risk_band(0.10) == "low"
        assert InjuryRiskModel.get_risk_band(0.40) == "moderate"
        assert InjuryRiskModel.get_risk_band(0.75) == "high"


class TestACWRComponent:
    def test_optimal_acwr_high_score(self):
        result = ReadinessEngine.compute_readiness(make_features(acwr_4w=1.05))
        assert result.components["acwr_balance"] > 80

    def test_high_acwr_low_score(self):
        result = ReadinessEngine.compute_readiness(make_features(acwr_4w=1.8))
        assert result.components["acwr_balance"] < 30

    def test_low_acwr_low_score(self):
        result = ReadinessEngine.compute_readiness(make_features(acwr_4w=0.4))
        assert result.components["acwr_balance"] < 50

    def test_no_acwr_defaults_50(self):
        result = ReadinessEngine.compute_readiness(make_features(acwr_4w=None))
        assert result.components["acwr_balance"] == 50


class TestFreshness:
    def test_one_day_rest_high(self):
        result = ReadinessEngine.compute_readiness(
            make_features(), days_since_last_activity=1
        )
        assert result.components["fatigue_freshness"] > 70

    def test_ran_today_moderate(self):
        result = ReadinessEngine.compute_readiness(
            make_features(), days_since_last_activity=0
        )
        assert result.components["fatigue_freshness"] < 70

    def test_long_rest_low(self):
        result = ReadinessEngine.compute_readiness(
            make_features(), days_since_last_activity=14
        )
        assert result.components["fatigue_freshness"] < 40

    def test_recent_race_penalty(self):
        no_race = ReadinessEngine.compute_readiness(
            make_features(), days_since_last_activity=2
        )
        with_race = ReadinessEngine.compute_readiness(
            make_features(), days_since_last_activity=2, days_since_last_race=2
        )
        assert with_race.components["fatigue_freshness"] < no_race.components["fatigue_freshness"]


class TestRecency:
    def test_recent_threshold_high(self):
        result = ReadinessEngine.compute_readiness(
            make_features(), days_since_last_threshold=2
        )
        assert result.components["training_recency"] > 70

    def test_stale_threshold_low(self):
        result = ReadinessEngine.compute_readiness(
            make_features(),
            days_since_last_threshold=30,
            days_since_last_long_run=30,
        )
        assert result.components["training_recency"] < 30


class TestPhysiological:
    def test_good_sleep_helps(self):
        good = ReadinessEngine.compute_readiness(make_features(), sleep_score=90)
        bad = ReadinessEngine.compute_readiness(make_features(), sleep_score=30)
        assert good.components["physiological"] > bad.components["physiological"]

    def test_no_data_defaults_50(self):
        result = ReadinessEngine.compute_readiness(make_features())
        assert result.components["physiological"] == 50.0


class TestFactors:
    def test_high_acwr_warns(self):
        result = ReadinessEngine.compute_readiness(make_features(acwr_4w=1.8))
        factor_texts = [f["factor"] for f in result.factors]
        assert any("High" in t or "load" in t.lower() for t in factor_texts)

    def test_good_sleep_noted(self):
        result = ReadinessEngine.compute_readiness(make_features(), sleep_score=85)
        factor_texts = [f["factor"] for f in result.factors]
        assert any("sleep" in t.lower() for t in factor_texts)


class TestReadinessEndpoint:
    @patch("app.routers.readiness.SupabaseService")
    def test_endpoint_returns_200(self, mock_svc_cls, client):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = []
        mock_svc.get_recent_physiology.return_value = []
        r = client.get("/readiness")
        assert r.status_code == 200
        data = r.json()
        assert "score" in data
        assert "label" in data
        assert "components" in data
        assert "factors" in data


# ---------------------------------------------------------------------------
# D9: Real data vs fallback tests for readiness endpoint
# ---------------------------------------------------------------------------


class TestReadinessWithRealData:
    """Verify readiness endpoint with mocked real activities from DB."""

    @patch("app.services.feature_service.FeatureService.compute_all_features")
    @patch("app.routers.readiness.SupabaseService")
    def test_readiness_with_activities(self, mock_db_cls, mock_feat_fn, client):
        mock_db = MagicMock()
        mock_db.get_recent_activities.return_value = [
            {
                "timestamp": "2026-03-05T08:00:00+00:00",
                "duration_seconds": 2400,
                "distance_meters": 8000,
                "avg_hr": 148,
                "activity_type": "easy",
            },
            {
                "timestamp": "2026-03-03T08:00:00+00:00",
                "duration_seconds": 3000,
                "distance_meters": 10000,
                "avg_hr": 165,
                "activity_type": "threshold",
            },
            {
                "timestamp": "2026-02-28T08:00:00+00:00",
                "duration_seconds": 5400,
                "distance_meters": 18000,
                "avg_hr": 140,
                "activity_type": "long_run",
            },
        ]
        mock_db.get_recent_physiology.return_value = [{"sleep_score": 82}]
        mock_db_cls.return_value = mock_db

        mock_feat_fn.return_value = {
            "acwr_4w": 1.1,
            "weekly_load_stddev": 3500,
            "session_density_stability": 0.85,
        }

        r = client.get("/readiness")
        assert r.status_code == 200
        data = r.json()
        assert 0 <= data["score"] <= 100
        assert data["label"] in ("Peak", "Good", "Moderate", "Low", "Very Low")
        assert "acwr_balance" in data["components"]
        assert "fatigue_freshness" in data["components"]
        assert "injury_risk" in data["components"]
        mock_db.insert_injury_risk_assessment.assert_called_once()
        persisted = mock_db.insert_injury_risk_assessment.call_args[0][0]
        assert persisted["user_id"] == "test-user"
        assert persisted["event"] == "5000"
        assert persisted["risk_band"] in {"low", "moderate", "high"}

    @patch("app.services.feature_service.FeatureService.compute_all_features")
    @patch("app.routers.readiness.SupabaseService")
    def test_readiness_enriches_sleep_and_body_factors(self, mock_db_cls, mock_feat_fn, client):
        mock_db = MagicMock()
        mock_db.get_recent_activities.return_value = [
            {
                "timestamp": "2026-03-05T08:00:00+00:00",
                "duration_seconds": 2400,
                "distance_meters": 8000,
                "avg_hr": 148,
                "activity_type": "easy",
            }
        ]
        mock_db.get_recent_physiology.return_value = [
            {
                "sleep_score": 83,
                "custom_fields": {"weight_kg": 70.0, "body_fat_percentage": 14.2, "bmi": 22.1},
            }
        ]
        mock_db_cls.return_value = mock_db
        mock_feat_fn.return_value = {
            "acwr_4w": 1.1,
            "weekly_load_stddev": 3500,
            "session_density_stability": 0.85,
        }

        r = client.get("/readiness")
        assert r.status_code == 200
        factors = r.json()["factors"]
        factor_names = [f.get("factor", "") for f in factors]
        assert "Sleep recovery signal" in factor_names
        assert "Body composition signal" in factor_names

        persisted = mock_db.insert_injury_risk_assessment.call_args[0][0]
        contributions = persisted["feature_contributions"]
        assert contributions["sleep_score"] == 83
        assert contributions["weight_kg"] == 70.0

    @patch("app.routers.readiness.SupabaseService")
    def test_readiness_returns_insufficient_data_when_no_activities(self, mock_cls, client):
        inst = MagicMock()
        inst.get_recent_activities.return_value = []
        mock_cls.return_value = inst

        r = client.get("/readiness")
        assert r.status_code == 200
        data = r.json()
        assert data["score"] == 0
        assert data["label"] == "Insufficient Data"

    @patch("app.services.feature_service.FeatureService.compute_all_features")
    @patch("app.routers.readiness.SupabaseService")
    def test_readiness_no_physiology_data(self, mock_db_cls, mock_feat_fn, client):
        mock_db = MagicMock()
        mock_db.get_recent_activities.return_value = [
            {
                "timestamp": "2026-03-04T08:00:00+00:00",
                "duration_seconds": 1800,
                "distance_meters": 5000,
                "avg_hr": 150,
                "activity_type": "easy",
            },
            {
                "timestamp": "2026-03-02T08:00:00+00:00",
                "duration_seconds": 2400,
                "distance_meters": 8000,
                "avg_hr": 165,
                "activity_type": "threshold",
            },
            {
                "timestamp": "2026-02-28T08:00:00+00:00",
                "duration_seconds": 5400,
                "distance_meters": 18000,
                "avg_hr": 140,
                "activity_type": "long_run",
            },
        ]
        mock_db.get_recent_physiology.return_value = []
        mock_db_cls.return_value = mock_db

        mock_feat_fn.return_value = {
            "acwr_4w": 1.0,
            "weekly_load_stddev": 2000,
            "session_density_stability": 0.7,
        }

        r = client.get("/readiness")
        assert r.status_code == 200
        data = r.json()
        assert 0 <= data["score"] <= 100

    @patch("app.services.feature_service.FeatureService.compute_all_features")
    @patch("app.routers.readiness.InjuryRiskModel.predict_probability", return_value=0.72)
    @patch("app.routers.readiness.SupabaseService")
    def test_readiness_persists_high_risk_band(self, mock_db_cls, _mock_prob, mock_feat_fn, client):
        mock_db = MagicMock()
        mock_db.get_recent_activities.return_value = [
            {
                "timestamp": "2026-03-05T08:00:00+00:00",
                "duration_seconds": 2400,
                "distance_meters": 8000,
                "avg_hr": 148,
                "activity_type": "easy",
            }
        ]
        mock_db.get_recent_physiology.return_value = [{"sleep_score": 60}]
        mock_db_cls.return_value = mock_db
        mock_feat_fn.return_value = {
            "acwr_4w": 1.5,
            "weekly_load_stddev": 9000,
            "session_density_stability": 1.6,
        }

        r = client.get("/readiness")
        assert r.status_code == 200
        persisted = mock_db.insert_injury_risk_assessment.call_args[0][0]
        assert persisted["risk_band"] == "high"
