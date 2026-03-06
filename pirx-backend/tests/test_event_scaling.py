import pytest
import numpy as np
from app.ml.event_scaling import (
    EventScaler, EVENT_DISTANCES_M, DEFAULT_EXPONENT,
    EXPONENT_BOUNDS, PHASE_TRANSITION_DISTANCE,
)


class TestRiegelScale:
    def test_same_distance_same_time(self):
        t = EventScaler.riegel_scale(1200, 5000, 5000)
        assert t == pytest.approx(1200, rel=0.01)

    def test_longer_distance_slower(self):
        t_10k = EventScaler.riegel_scale(1200, 5000, 10000)
        assert t_10k > 1200

    def test_shorter_distance_faster(self):
        t_3k = EventScaler.riegel_scale(1200, 5000, 3000)
        assert t_3k < 1200

    def test_known_conversion(self):
        """20:00 5K -> ~41:30 10K with exponent 1.06."""
        t_10k = EventScaler.riegel_scale(1200, 5000, 10000, 1.06)
        assert 2400 < t_10k < 2600

    def test_zero_distance_raises(self):
        with pytest.raises(ValueError):
            EventScaler.riegel_scale(1200, 0, 5000)

    def test_negative_time_raises(self):
        with pytest.raises(ValueError):
            EventScaler.riegel_scale(-100, 5000, 10000)


class TestModifiedRiegel:
    def test_higher_mileage_faster(self):
        """Runners with more weekly mileage should scale better to longer distances."""
        t_low = EventScaler.modified_riegel(1200, 5000, 10000, weekly_km=30)
        t_high = EventScaler.modified_riegel(1200, 5000, 10000, weekly_km=80)
        assert t_high < t_low

    def test_default_40km_similar_to_riegel(self):
        t_mod = EventScaler.modified_riegel(1200, 5000, 10000, weekly_km=40)
        t_rie = EventScaler.riegel_scale(1200, 5000, 10000, 1.06)
        assert abs(t_mod - t_rie) < 10  # within 10 seconds


class TestIndividualExponent:
    def test_two_races(self):
        results = [
            {"distance_m": 5000, "time_s": 1200},
            {"distance_m": 10000, "time_s": 2520},
        ]
        exp = EventScaler.compute_individual_exponent(results)
        assert exp is not None
        assert EXPONENT_BOUNDS[0] <= exp <= EXPONENT_BOUNDS[1]

    def test_single_race_returns_none(self):
        results = [{"distance_m": 5000, "time_s": 1200}]
        assert EventScaler.compute_individual_exponent(results) is None

    def test_exponent_bounded(self):
        """Even extreme data should be bounded by population norms."""
        results = [
            {"distance_m": 1500, "time_s": 240},
            {"distance_m": 42195, "time_s": 7200},
        ]
        exp = EventScaler.compute_individual_exponent(results)
        assert EXPONENT_BOUNDS[0] <= exp <= EXPONENT_BOUNDS[1]


class TestPhaseTransition:
    def test_crossing_5k_boundary_adds_penalty(self):
        """Crossing the 5K boundary should increase predicted time."""
        t_no_phase = EventScaler.riegel_scale(1200, 3000, 10000, 1.06)
        t_phase = EventScaler.scale_with_phase_transition(1200, 3000, 10000, 1.06)
        assert t_phase > t_no_phase

    def test_within_boundary_no_change(self):
        """Scaling within same side of 5K boundary = no adjustment."""
        t_no_phase = EventScaler.riegel_scale(1200, 5000, 10000, 1.06)
        t_phase = EventScaler.scale_with_phase_transition(1200, 5000, 10000, 1.06)
        assert t_phase == pytest.approx(t_no_phase, rel=0.001)


class TestScaleAllEvents:
    def test_default_events(self):
        results = EventScaler.scale_all_events(1200, "5000")
        assert set(results.keys()) == {"1500", "3000", "5000", "10000"}

    def test_times_ordered(self):
        results = EventScaler.scale_all_events(1200, "5000")
        assert results["1500"] < results["3000"] < results["5000"] < results["10000"]

    def test_unknown_event_raises(self):
        with pytest.raises(ValueError):
            EventScaler.scale_all_events(1200, "50m")


class TestEnvironmentalAdjustment:
    def test_optimal_no_change(self):
        t = EventScaler.environmental_adjustment(1200, 12.0)
        assert t == 1200

    def test_hot_day_slower(self):
        t = EventScaler.environmental_adjustment(1200, 30.0)
        assert t > 1200

    def test_cold_day_slower(self):
        t = EventScaler.environmental_adjustment(1200, 0.0)
        assert t > 1200

    def test_penalty_proportional(self):
        """30°C should be worse than 20°C."""
        t_20 = EventScaler.environmental_adjustment(1200, 20.0)
        t_30 = EventScaler.environmental_adjustment(1200, 30.0)
        assert t_30 > t_20
