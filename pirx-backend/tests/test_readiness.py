import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user
from app.ml.readiness_engine import ReadinessEngine, READINESS_WEIGHTS


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
    def test_endpoint_returns_200(self, client):
        r = client.get("/readiness")
        assert r.status_code == 200
        data = r.json()
        assert "score" in data
        assert "label" in data
        assert "components" in data
        assert "factors" in data
