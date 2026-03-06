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
    async def _mock_user():
        return {"user_id": "test-user"}

    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def mock_supabase():
    with patch("app.services.supabase_client.get_supabase_client") as mock_fn:
        mock_client = MagicMock()
        mock_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        yield mock_client


class TestZoneDistribution:
    def test_get_zones_returns_five_zones(self, client):
        r = client.get("/features/zones")
        assert r.status_code == 200
        data = r.json()
        assert len(data["zones"]) == 5

    def test_zone_names_and_order(self, client):
        r = client.get("/features/zones")
        zones = r.json()["zones"]
        expected = ["Z1", "Z2", "Z3", "Z4", "Z5"]
        assert [z["zone"] for z in zones] == expected

    def test_zone_fields_present(self, client):
        r = client.get("/features/zones")
        for zone in r.json()["zones"]:
            assert "zone" in zone
            assert "name" in zone
            assert "hr_range" in zone
            assert "pace_range" in zone
            assert "time_pct" in zone

    def test_distribution_21d_present(self, client):
        r = client.get("/features/zones")
        dist = r.json()["distribution_21d"]
        assert "z1" in dist
        assert "z2" in dist
        assert "z3" in dist
        assert "z4" in dist
        assert "z5" in dist

    def test_methodology_computed(self, client):
        r = client.get("/features/zones")
        data = r.json()
        assert data["methodology"] in ("Pyramidal", "Polarized", "Mixed")

    def test_z2_efficiency_gain_present(self, client):
        r = client.get("/features/zones")
        assert "z2_efficiency_gain_sec_per_km" in r.json()

    def test_methodology_pyramidal_when_low_intensity_dominant(self):
        from app.routers.features import _compute_methodology
        assert _compute_methodology({"z1": 0.40, "z2": 0.40, "z4": 0.05, "z5": 0.02}) == "Pyramidal"

    def test_methodology_polarized(self):
        from app.routers.features import _compute_methodology
        assert _compute_methodology({"z1": 0.25, "z2": 0.25, "z4": 0.20, "z5": 0.10}) == "Polarized"

    def test_methodology_mixed(self):
        from app.routers.features import _compute_methodology
        assert _compute_methodology({"z1": 0.30, "z2": 0.35, "z4": 0.10, "z5": 0.05}) == "Mixed"


class TestRunningEconomy:
    def test_get_economy_200(self, client):
        r = client.get("/features/economy")
        assert r.status_code == 200

    def test_matched_hr_band_fields(self, client):
        r = client.get("/features/economy")
        band = r.json()["matched_hr_band"]
        assert "hr_range" in band
        assert "baseline_pace_sec_km" in band
        assert "current_pace_sec_km" in band
        assert "efficiency_gain_sec_km" in band
        assert band["efficiency_gain_sec_km"] == band["baseline_pace_sec_km"] - band["current_pace_sec_km"]

    def test_hr_cost_change(self, client):
        r = client.get("/features/economy")
        assert "hr_cost_change_bpm" in r.json()

    def test_intensity_levels(self, client):
        r = client.get("/features/economy")
        levels = r.json()["intensity_levels"]
        assert len(levels) == 3
        labels = [lv["level"] for lv in levels]
        assert labels == ["Easy", "Threshold", "Race"]
        for lv in levels:
            assert "baseline_pace_sec_km" in lv
            assert "current_pace_sec_km" in lv
            assert "delta_sec_km" in lv


class TestLearningInsights:
    def test_get_learning_200(self, client):
        r = client.get("/features/learning")
        assert r.status_code == 200

    def test_insights_are_list(self, client):
        r = client.get("/features/learning")
        data = r.json()
        assert isinstance(data["insights"], list)

    def test_insight_fields(self, client):
        r = client.get("/features/learning")
        for insight in r.json()["insights"]:
            assert "category" in insight
            assert "title" in insight
            assert "body" in insight
            assert "status" in insight
            assert "confidence" in insight
            assert insight["category"] in ("consistency", "response", "trend", "risk")

    def test_summary_sections(self, client):
        r = client.get("/features/learning")
        summary = r.json()["summary"]
        assert "what_today_supports" in summary
        assert "what_is_defensible" in summary
        assert "what_needs_development" in summary

    def test_structural_identity(self, client):
        r = client.get("/features/learning")
        assert "structural_identity" in r.json()


class TestAdjunctAnalysis:
    def test_get_adjuncts_200(self, client):
        r = client.get("/features/adjuncts")
        assert r.status_code == 200

    def test_adjuncts_list(self, client):
        r = client.get("/features/adjuncts")
        assert isinstance(r.json()["adjuncts"], list)


class TestHonestState:
    def test_get_honest_state_200(self, client):
        r = client.get("/features/honest-state")
        assert r.status_code == 200

    def test_three_sections_present(self, client):
        r = client.get("/features/honest-state")
        data = r.json()
        assert "what_today_supports" in data
        assert "what_is_defensible" in data
        assert "what_needs_development" in data

    def test_sections_are_non_empty_lists(self, client):
        r = client.get("/features/honest-state")
        data = r.json()
        for key in ("what_today_supports", "what_is_defensible", "what_needs_development"):
            assert isinstance(data[key], list)
            assert len(data[key]) > 0

    def test_section_item_fields(self, client):
        r = client.get("/features/honest-state")
        data = r.json()
        for key in ("what_today_supports", "what_is_defensible", "what_needs_development"):
            for item in data[key]:
                assert "title" in item
                assert "body" in item
                assert "confidence" in item


class TestDriverExplainEndpoint:
    """Verify the SHAP-wired explain endpoint works."""

    def test_explain_aerobic_base(self, client):
        r = client.get("/drivers/aerobic_base/explain")
        assert r.status_code == 200
        data = r.json()
        assert data["driver_name"] == "aerobic_base"
        assert data["display_name"] == "Aerobic Base"
        assert "overall_direction" in data
        assert "top_factors" in data
        assert "summary" in data
        assert "confidence" in data

    def test_explain_all_drivers(self, client):
        drivers = ["aerobic_base", "threshold_density", "speed_exposure", "running_economy", "load_consistency"]
        for driver in drivers:
            r = client.get(f"/drivers/{driver}/explain")
            assert r.status_code == 200
            assert r.json()["driver_name"] == driver


class TestAllProjectionsEndpoint:
    def test_get_all_projections(self, client):
        r = client.get("/projection/all")
        assert r.status_code == 200
        data = r.json()
        assert "projections" in data
        assert isinstance(data["projections"], list)


class TestSyncStatusEndpoint:
    def test_get_sync_status(self, client):
        r = client.get("/sync/status")
        assert r.status_code == 200
        data = r.json()
        assert "connections" in data
        assert isinstance(data["connections"], list)


# ---------------------------------------------------------------------------
# D9: Real data vs fallback tests
# ---------------------------------------------------------------------------


class TestZoneDistributionWithRealData:
    """Verify zone endpoint works with mocked real activities (with hr_zones)."""

    @patch("app.routers.features.SupabaseService")
    def test_zones_with_activity_data(self, mock_cls, client):
        inst = MagicMock()
        inst.get_recent_activities.return_value = [
            {"hr_zones": [600, 1200, 300, 180, 120], "timestamp": "2026-03-01T08:00:00Z"},
            {"hr_zones": [400, 900, 200, 150, 50], "timestamp": "2026-02-28T08:00:00Z"},
        ]
        mock_cls.return_value = inst

        r = client.get("/features/zones")
        assert r.status_code == 200
        data = r.json()
        assert len(data["zones"]) == 5

        total = sum(z["time_pct"] for z in data["zones"])
        assert abs(total - 1.0) < 0.01

        z1_pct = data["distribution_21d"]["z1"]
        z2_pct = data["distribution_21d"]["z2"]
        assert z1_pct > 0
        assert z2_pct > 0

    @patch("app.routers.features.SupabaseService")
    def test_zones_fallback_no_activities(self, mock_cls, client):
        inst = MagicMock()
        inst.get_recent_activities.return_value = []
        mock_cls.return_value = inst

        r = client.get("/features/zones")
        assert r.status_code == 200
        data = r.json()
        assert data["distribution_21d"]["z2"] == 0.35
        assert data["methodology"] in ("Pyramidal", "Polarized", "Mixed")


class TestRunningEconomyWithRealData:
    """Verify economy endpoint with mocked real activities (matched HR band)."""

    @patch("app.routers.features.SupabaseService")
    def test_economy_with_matched_activities(self, mock_cls, client):
        inst = MagicMock()
        inst.get_recent_activities.return_value = [
            {"avg_hr": 148, "avg_pace_sec_per_km": 290, "timestamp": "2026-03-01"},
            {"avg_hr": 150, "avg_pace_sec_per_km": 295, "timestamp": "2026-02-28"},
            {"avg_hr": 152, "avg_pace_sec_per_km": 300, "timestamp": "2026-02-27"},
            {"avg_hr": 149, "avg_pace_sec_per_km": 305, "timestamp": "2026-02-26"},
            {"avg_hr": 151, "avg_pace_sec_per_km": 310, "timestamp": "2026-02-25"},
            {"avg_hr": 147, "avg_pace_sec_per_km": 308, "timestamp": "2026-02-24"},
        ]
        mock_cls.return_value = inst

        r = client.get("/features/economy")
        assert r.status_code == 200
        data = r.json()
        band = data["matched_hr_band"]
        assert "hr_range" in band
        expected_gain = band["baseline_pace_sec_km"] - band["current_pace_sec_km"]
        assert abs(band["efficiency_gain_sec_km"] - expected_gain) < 0.2

    @patch("app.routers.features.SupabaseService")
    def test_economy_fallback_no_matching_activities(self, mock_cls, client):
        inst = MagicMock()
        inst.get_recent_activities.return_value = [
            {"avg_hr": 120, "avg_pace_sec_per_km": 400, "timestamp": "2026-03-01"},
        ]
        mock_cls.return_value = inst

        r = client.get("/features/economy")
        assert r.status_code == 200
        data = r.json()
        assert data["matched_hr_band"]["baseline_pace_sec_km"] == 310
        assert len(data["intensity_levels"]) == 3


class TestAdjunctAnalysisWithRealData:
    """Verify adjunct endpoint with real DB rows vs mock fallback."""

    @patch("app.routers.features.SupabaseService")
    def test_adjuncts_with_db_rows(self, mock_cls, client):
        inst = MagicMock()
        inst.get_adjunct_state.return_value = [
            {
                "adjunct_name": "Ice Baths",
                "sessions_analyzed": 5,
                "median_projection_delta_seconds": -2.0,
                "hr_drift_change_pct": -0.5,
                "volatility_change": 0.1,
                "status": "observational",
                "confidence": 0.4,
            },
        ]
        mock_cls.return_value = inst

        r = client.get("/features/adjuncts")
        assert r.status_code == 200
        data = r.json()
        assert len(data["adjuncts"]) == 1
        assert data["adjuncts"][0]["name"] == "Ice Baths"

    @patch("app.routers.features.SupabaseService")
    def test_adjuncts_fallback_empty_db(self, mock_cls, client):
        inst = MagicMock()
        inst.get_adjunct_state.return_value = []
        mock_cls.return_value = inst

        r = client.get("/features/adjuncts")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["adjuncts"], list)
        assert len(data["adjuncts"]) == 0
