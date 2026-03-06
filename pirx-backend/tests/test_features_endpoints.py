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
        assert len(data["insights"]) > 0

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

    def test_adjuncts_count(self, client):
        r = client.get("/features/adjuncts")
        assert len(r.json()["adjuncts"]) == 3

    def test_adjunct_fields(self, client):
        r = client.get("/features/adjuncts")
        for adj in r.json()["adjuncts"]:
            assert "name" in adj
            assert "sessions_analyzed" in adj
            assert "median_projection_delta_seconds" in adj
            assert "hr_drift_change_pct" in adj
            assert "volatility_change" in adj
            assert "status" in adj
            assert "confidence" in adj

    def test_adjunct_status_values(self, client):
        r = client.get("/features/adjuncts")
        for adj in r.json()["adjuncts"]:
            assert adj["status"] in ("observational", "emerging", "supported")

    def test_adjunct_names(self, client):
        r = client.get("/features/adjuncts")
        names = [a["name"] for a in r.json()["adjuncts"]]
        assert "Altitude Training" in names
        assert "Strength Training" in names
        assert "Heat Acclimation" in names


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
        assert "events" in data
        for event in ["1500", "3000", "5000", "10000"]:
            assert event in data["events"]


class TestSyncStatusEndpoint:
    def test_get_sync_status(self, client):
        r = client.get("/sync/status")
        assert r.status_code == 200
        data = r.json()
        assert "connections" in data
        assert isinstance(data["connections"], list)
