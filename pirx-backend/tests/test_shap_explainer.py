import pytest
from app.ml.shap_explainer import SHAPExplainer, DriverExplanation, DRIVER_DISPLAY_NAMES


SAMPLE_FEATURES = {
    "rolling_distance_7d": 35000,
    "rolling_distance_21d": 100000,
    "rolling_distance_42d": 180000,
    "z1_pct": 0.42, "z2_pct": 0.32,
    "z4_pct": 0.14, "z5_pct": 0.06,
    "threshold_density_min_week": 20,
    "speed_exposure_min_week": 8,
    "hr_drift_sustained": 0.04,
    "late_session_pace_decay": 0.03,
    "matched_hr_band_pace": 270,
    "weekly_load_stddev": 3500,
    "block_variance": 3000,
    "session_density_stability": 0.7,
    "acwr_4w": 1.1,
}

PREVIOUS_FEATURES = {
    "rolling_distance_7d": 28000,
    "rolling_distance_21d": 80000,
    "rolling_distance_42d": 150000,
    "z1_pct": 0.38, "z2_pct": 0.28,
    "z4_pct": 0.10, "z5_pct": 0.04,
    "threshold_density_min_week": 12,
    "speed_exposure_min_week": 4,
    "hr_drift_sustained": 0.06,
    "late_session_pace_decay": 0.05,
    "matched_hr_band_pace": 285,
    "weekly_load_stddev": 5000,
    "block_variance": 4500,
    "session_density_stability": 1.2,
    "acwr_4w": 0.9,
}


class TestExplainChange:
    def test_returns_explanation(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES, PREVIOUS_FEATURES)
        assert isinstance(result, DriverExplanation)
        assert result.driver_name == "aerobic_base"
        assert result.display_name == "Aerobic Base"

    def test_has_narrative(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES, PREVIOUS_FEATURES)
        assert len(result.narrative) > 0

    def test_improving_direction(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES, PREVIOUS_FEATURES)
        assert result.overall_direction == "improving"

    def test_top_features_limited(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES, PREVIOUS_FEATURES)
        assert len(result.top_features) <= 3

    def test_all_drivers(self):
        for driver in DRIVER_DISPLAY_NAMES:
            result = SHAPExplainer.explain_driver(driver, SAMPLE_FEATURES, PREVIOUS_FEATURES)
            assert result.display_name == DRIVER_DISPLAY_NAMES[driver]

    def test_consistency_improves_with_lower_stddev(self):
        result = SHAPExplainer.explain_driver("load_consistency", SAMPLE_FEATURES, PREVIOUS_FEATURES)
        assert result.overall_direction == "improving"

    def test_no_previous_features(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES, None)
        assert result.overall_direction in ("improving", "stable", "declining")

    def test_empty_features(self):
        result = SHAPExplainer.explain_driver("aerobic_base", {}, {})
        assert result.overall_direction == "stable"
        assert "stable" in result.narrative.lower() or "collected" in result.narrative.lower()


class TestExplainState:
    def test_returns_explanation(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES)
        assert isinstance(result, DriverExplanation)

    def test_above_average_detection(self):
        high_features = dict(SAMPLE_FEATURES)
        high_features["rolling_distance_7d"] = 60000
        result = SHAPExplainer.explain_driver("aerobic_base", high_features)
        top_directions = [f["direction"] for f in result.top_features]
        assert "above average" in top_directions

    def test_confidence_level(self):
        result = SHAPExplainer.explain_driver("aerobic_base", SAMPLE_FEATURES)
        assert result.confidence in ("high", "medium", "low")


class TestLearningModule:
    pass  # Separate test file
