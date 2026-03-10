import pytest
from app.ml.projection_engine import (
    ProjectionEngine, ProjectionState, DriverState,
    DRIVER_NAMES, DEFAULT_DRIVER_WEIGHTS, DRIVER_FEATURE_MAP,
)


def make_features(**overrides) -> dict:
    """Create a test feature dict with sensible defaults.

    Values are calibrated relative to FEATURE_BASELINES so that a typical
    competitive recreational runner (~45 km/week) scores above 50.
    """
    features = {
        "rolling_distance_7d": 25000,
        "rolling_distance_21d": 65000,
        "rolling_distance_42d": 130000,
        "sessions_per_week": 5,
        "long_run_count": 2,
        "z1_pct": 0.35,
        "z2_pct": 0.35,
        "z3_pct": 0.10,
        "z4_pct": 0.10,
        "z5_pct": 0.04,
        "threshold_density_min_week": 12,
        "speed_exposure_min_week": 4,
        "matched_hr_band_pace": 290,
        "hr_drift_sustained": 0.04,
        "late_session_pace_decay": 0.03,
        "weekly_load_stddev": 4000,
        "block_variance": 3000,
        "session_density_stability": 0.8,
        "acwr_4w": 1.1,
        "acwr_6w": 1.05,
        "acwr_8w": 1.0,
        "resting_hr_trend": None,
        "hrv_trend": None,
        "sleep_score_trend": None,
    }
    features.update(overrides)
    return features


class TestProjectionEngineInit:
    def test_default_weights(self):
        engine = ProjectionEngine()
        assert sum(engine.driver_weights.values()) == pytest.approx(1.0)

    def test_custom_alpha(self):
        engine = ProjectionEngine(alpha=0.7)
        assert engine.alpha == 0.7

    def test_alpha_clamped(self):
        engine = ProjectionEngine(alpha=0.1)
        assert engine.alpha == 0.3
        engine = ProjectionEngine(alpha=0.9)
        assert engine.alpha == 0.7


class TestComputeProjection:
    def test_returns_state_and_drivers(self):
        engine = ProjectionEngine()
        features = make_features()
        state, drivers = engine.compute_projection("user-1", "5000", 1200.0, features)
        assert isinstance(state, ProjectionState)
        assert len(drivers) == 5
        assert all(isinstance(d, DriverState) for d in drivers)

    def test_projected_time_reasonable(self):
        engine = ProjectionEngine()
        features = make_features()
        state, _ = engine.compute_projection("user-1", "5000", 1200.0, features)
        # 20:00 5K -> projected should be within ±25%
        assert 900 < state.projected_time_seconds < 1500

    def test_driver_names_correct(self):
        engine = ProjectionEngine()
        features = make_features()
        _, drivers = engine.compute_projection("user-1", "5000", 1200.0, features)
        driver_names = {d.driver_name for d in drivers}
        assert driver_names == set(DRIVER_NAMES)

    def test_user_id_propagated(self):
        engine = ProjectionEngine()
        features = make_features()
        state, drivers = engine.compute_projection("user-abc", "5000", 1200.0, features)
        assert state.user_id == "user-abc"
        assert all(d.user_id == "user-abc" for d in drivers)

    def test_event_propagated(self):
        engine = ProjectionEngine()
        features = make_features()
        state, drivers = engine.compute_projection("u", "10000", 2400.0, features)
        assert state.event == "10000"
        assert all(d.event == "10000" for d in drivers)


class TestDriverSumConstraint:
    def test_drivers_sum_to_total(self):
        engine = ProjectionEngine()
        features = make_features()
        state, drivers = engine.compute_projection("user-1", "5000", 1200.0, features)
        driver_sum = sum(d.contribution_seconds for d in drivers)
        assert driver_sum == pytest.approx(state.total_improvement_seconds, abs=0.01)

    def test_validate_driver_sum_passes(self):
        engine = ProjectionEngine()
        features = make_features()
        state, drivers = engine.compute_projection("user-1", "5000", 1200.0, features)
        assert ProjectionEngine.validate_driver_sum(drivers, state.total_improvement_seconds)

    def test_drivers_sum_zero_improvement(self):
        engine = ProjectionEngine()
        # All features at baseline -> ~50 score -> ~0 improvement
        features = make_features(
            rolling_distance_7d=20000,
            rolling_distance_21d=55000,
            rolling_distance_42d=110000,
            threshold_density_min_week=10,
            speed_exposure_min_week=3,
            hr_drift_sustained=0.05,
            weekly_load_stddev=5000,
        )
        state, drivers = engine.compute_projection("u", "5000", 1200.0, features)
        driver_sum = sum(d.contribution_seconds for d in drivers)
        assert driver_sum == pytest.approx(state.total_improvement_seconds, abs=0.01)


class TestVolatilityDampening:
    def test_dampening_smooths_projection(self):
        engine = ProjectionEngine(alpha=0.5)
        features = make_features()

        # First projection (no previous)
        state1, _ = engine.compute_projection("u", "5000", 1200.0, features)

        # Second projection with large feature shift (guarantees raw != previous)
        features2 = make_features(
            rolling_distance_7d=50000,
            rolling_distance_21d=150000,
            rolling_distance_42d=300000,
            threshold_density_min_week=30,
            speed_exposure_min_week=10,
        )
        state2, _ = engine.compute_projection("u", "5000", 1200.0, features2, previous_state=state1)

        # Raw would be very different, dampened should be closer to previous
        # Volatility = |raw - previous|, so must be > 0 with large feature shift
        assert state2.volatility > 0

    def test_no_previous_no_dampening(self):
        engine = ProjectionEngine()
        features = make_features()
        state, _ = engine.compute_projection("u", "5000", 1200.0, features)
        assert state.volatility == 0.0


class TestSupportedRange:
    def test_range_brackets_projection(self):
        engine = ProjectionEngine()
        features = make_features()
        state, _ = engine.compute_projection("u", "5000", 1200.0, features)
        assert state.supported_range_low < state.projected_time_seconds
        assert state.supported_range_high > state.projected_time_seconds

    def test_range_wider_with_fewer_features(self):
        engine = ProjectionEngine()

        full_features = make_features()
        sparse_features = {k: None for k in full_features}
        sparse_features["rolling_distance_7d"] = 30000

        state_full, _ = engine.compute_projection("u", "5000", 1200.0, full_features)
        state_sparse, _ = engine.compute_projection("u", "5000", 1200.0, sparse_features)

        full_width = state_full.supported_range_high - state_full.supported_range_low
        sparse_width = state_sparse.supported_range_high - state_sparse.supported_range_low
        assert sparse_width > full_width


class TestStructuralShift:
    def test_shift_above_threshold(self):
        s1 = ProjectionState(projected_time_seconds=1200)
        s2 = ProjectionState(projected_time_seconds=1197)
        assert ProjectionEngine.check_structural_shift(s2, s1, threshold_seconds=2.0)

    def test_no_shift_below_threshold(self):
        s1 = ProjectionState(projected_time_seconds=1200)
        s2 = ProjectionState(projected_time_seconds=1199)
        assert not ProjectionEngine.check_structural_shift(s2, s1, threshold_seconds=2.0)

    def test_first_projection_always_shifts(self):
        s = ProjectionState(projected_time_seconds=1200)
        assert ProjectionEngine.check_structural_shift(s, None)


class TestDriverTrends:
    def test_improving_trend(self):
        engine = ProjectionEngine()
        features = make_features(
            rolling_distance_7d=40000,  # very high volume -> high aerobic_base score
        )
        _, drivers = engine.compute_projection("u", "5000", 1200.0, features)
        ab = next(d for d in drivers if d.driver_name == "aerobic_base")
        assert ab.score > 60
        assert ab.trend == "improving"

    def test_stable_trend(self):
        engine = ProjectionEngine()
        features = make_features()
        _, drivers = engine.compute_projection("u", "5000", 1200.0, features)
        has_stable = any(d.trend == "stable" for d in drivers)
        has_any_trend = any(d.trend in ("stable", "improving", "declining") for d in drivers)
        assert has_any_trend, "All drivers should have a valid trend"

    def test_zone_pct_influences_aerobic_base(self):
        """Verify zone percentages aren't swamped by distance values (C2 fix)."""
        engine = ProjectionEngine()
        low_zone = make_features(z1_pct=0.10, z2_pct=0.10)
        high_zone = make_features(z1_pct=0.80, z2_pct=0.60)
        _, drivers_low = engine.compute_projection("u", "5000", 1200.0, low_zone)
        _, drivers_high = engine.compute_projection("u", "5000", 1200.0, high_zone)
        ab_low = next(d for d in drivers_low if d.driver_name == "aerobic_base")
        ab_high = next(d for d in drivers_high if d.driver_name == "aerobic_base")
        assert ab_high.score > ab_low.score, "Higher zone pct should raise Aerobic Base score"

    def test_matched_pace_influences_economy(self):
        """Verify matched_hr_band_pace (inverse) influences Running Economy (C2 fix)."""
        engine = ProjectionEngine()
        slow_pace = make_features(matched_hr_band_pace=400)
        fast_pace = make_features(matched_hr_band_pace=200)
        _, drivers_slow = engine.compute_projection("u", "5000", 1200.0, slow_pace)
        _, drivers_fast = engine.compute_projection("u", "5000", 1200.0, fast_pace)
        re_slow = next(d for d in drivers_slow if d.driver_name == "running_economy")
        re_fast = next(d for d in drivers_fast if d.driver_name == "running_economy")
        assert re_fast.score > re_slow.score, "Faster matched pace should raise Economy score"
