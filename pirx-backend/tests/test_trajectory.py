import pytest
from app.ml.trajectory_engine import (
    TrajectoryEngine, TrajectoryScenario, SCENARIO_CONFIGS,
)
from app.ml.projection_engine import ProjectionState


SAMPLE_FEATURES = {
    "rolling_distance_7d": 35000,
    "rolling_distance_21d": 30000,
    "rolling_distance_42d": 28000,
    "rolling_distance_90d": 25000,
    "threshold_density_min_week": 20,
    "speed_exposure_min_week": 8,
    "z1_pct": 0.40,
    "z2_pct": 0.30,
    "z4_pct": 0.12,
    "z5_pct": 0.05,
    "weekly_load_stddev": 4000,
    "block_variance": 3000,
    "session_density_stability": 0.8,
    "acwr_4w": 1.1,
    "hr_drift_sustained": 0.04,
    "late_session_pace_decay": 0.03,
    "matched_hr_band_pace": 270,
}


class TestTrajectoryEngine:
    def test_returns_three_scenarios(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        assert len(scenarios) == 3

    def test_scenario_labels(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        labels = [s.label for s in scenarios]
        assert "Maintain" in labels
        assert "Push" in labels
        assert "Ease Off" in labels

    def test_scenario_order(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        assert scenarios[0].label == "Maintain"
        assert scenarios[1].label == "Push"
        assert scenarios[2].label == "Ease Off"

    def test_push_faster_than_maintain(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        maintain = next(s for s in scenarios if s.label == "Maintain")
        push = next(s for s in scenarios if s.label == "Push")
        assert push.projected_time_seconds <= maintain.projected_time_seconds

    def test_ease_off_slower_than_maintain(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        maintain = next(s for s in scenarios if s.label == "Maintain")
        ease = next(s for s in scenarios if s.label == "Ease Off")
        assert ease.projected_time_seconds >= maintain.projected_time_seconds

    def test_confidence_levels(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        maintain = next(s for s in scenarios if s.label == "Maintain")
        push = next(s for s in scenarios if s.label == "Push")
        assert maintain.confidence > push.confidence

    def test_with_previous_state(self):
        engine = TrajectoryEngine()
        prev_state = ProjectionState(
            user_id="u1", event="5000",
            projected_time_seconds=1200.0,
            baseline_time_seconds=1260.0,
        )
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES, prev_state
        )
        assert len(scenarios) == 3
        for s in scenarios:
            assert isinstance(s.delta_from_current, float)

    def test_different_events(self):
        engine = TrajectoryEngine()
        s5k = engine.compute_trajectories("u1", "5000", 1260.0, SAMPLE_FEATURES)
        s10k = engine.compute_trajectories("u1", "10000", 2700.0, SAMPLE_FEATURES)
        assert s5k[0].projected_time_seconds != s10k[0].projected_time_seconds

    def test_empty_features_no_crash(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories("u1", "5000", 1260.0, {})
        assert len(scenarios) == 3

    def test_all_scenarios_have_positive_times(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        for s in scenarios:
            assert s.projected_time_seconds > 0

    def test_delta_types(self):
        engine = TrajectoryEngine()
        scenarios = engine.compute_trajectories(
            "u1", "5000", 1260.0, SAMPLE_FEATURES
        )
        for s in scenarios:
            assert isinstance(s.projected_time_seconds, float)
            assert isinstance(s.delta_from_current, float)
            assert isinstance(s.confidence, float)


class TestScenarioModifiers:
    def test_push_increases_intensity(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["push"]
        modified = engine._apply_scenario(SAMPLE_FEATURES, config)
        assert modified["threshold_density_min_week"] > SAMPLE_FEATURES["threshold_density_min_week"]
        assert modified["z5_pct"] > SAMPLE_FEATURES["z5_pct"]

    def test_ease_off_reduces_volume(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["ease_off"]
        modified = engine._apply_scenario(SAMPLE_FEATURES, config)
        assert modified["rolling_distance_7d"] < SAMPLE_FEATURES["rolling_distance_7d"]

    def test_maintain_unchanged(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["maintain"]
        modified = engine._apply_scenario(SAMPLE_FEATURES, config)
        assert modified["rolling_distance_7d"] == SAMPLE_FEATURES["rolling_distance_7d"]
        assert modified["z5_pct"] == SAMPLE_FEATURES["z5_pct"]

    def test_none_features_preserved(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["push"]
        features = {"rolling_distance_7d": None, "z5_pct": 0.05}
        modified = engine._apply_scenario(features, config)
        assert modified["rolling_distance_7d"] is None
        assert modified["z5_pct"] == 0.05 * config["intensity_factor"]

    def test_push_volume_slightly_increased(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["push"]
        modified = engine._apply_scenario(SAMPLE_FEATURES, config)
        assert modified["rolling_distance_7d"] == SAMPLE_FEATURES["rolling_distance_7d"] * 1.05

    def test_ease_off_consistency_improved(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["ease_off"]
        modified = engine._apply_scenario(SAMPLE_FEATURES, config)
        # Lower stddev = better consistency; dividing by >1 factor lowers it
        assert modified["weekly_load_stddev"] < SAMPLE_FEATURES["weekly_load_stddev"]

    def test_unrelated_features_untouched(self):
        engine = TrajectoryEngine()
        config = SCENARIO_CONFIGS["push"]
        modified = engine._apply_scenario(SAMPLE_FEATURES, config)
        assert modified["acwr_4w"] == SAMPLE_FEATURES["acwr_4w"]
        assert modified["hr_drift_sustained"] == SAMPLE_FEATURES["hr_drift_sustained"]
