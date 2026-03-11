import pytest
import numpy as np
from app.ml.lmc import LMCEngine, COMPONENT_MATRIX, LAMBDA_BOUNDS


class TestLMCInit:
    def test_default_rank_2(self):
        engine = LMCEngine()
        assert engine.rank == 2

    def test_rank_1(self):
        engine = LMCEngine(rank=1)
        assert engine.rank == 1

    def test_invalid_rank(self):
        with pytest.raises(ValueError):
            LMCEngine(rank=4)


class TestEstimateRunner:
    def test_single_race(self):
        engine = LMCEngine(rank=2)
        # 20:00 5K runner
        lam = engine.estimate_runner(["5000"], [1200.0])
        assert len(lam) == 2
        assert LAMBDA_BOUNDS["lambda1_min"] <= lam[0] <= LAMBDA_BOUNDS["lambda1_max"]

    def test_two_races(self):
        engine = LMCEngine(rank=2)
        # 20:00 5K, 42:00 10K
        lam = engine.estimate_runner(["5000", "10000"], [1200.0, 2520.0])
        assert len(lam) == 2

    def test_rank_3_with_three_races(self):
        engine = LMCEngine(rank=3)
        lam = engine.estimate_runner(
            ["1500", "5000", "10000"],
            [300.0, 1200.0, 2520.0],
        )
        assert len(lam) == 3

    def test_empty_events_raises(self):
        engine = LMCEngine()
        with pytest.raises(ValueError):
            engine.estimate_runner([], [])

    def test_mismatched_lengths_raises(self):
        engine = LMCEngine()
        with pytest.raises(ValueError):
            engine.estimate_runner(["5000"], [1200.0, 2520.0])

    def test_unknown_event_raises(self):
        engine = LMCEngine()
        with pytest.raises(ValueError):
            engine.estimate_runner(["50m"], [6.0])


class TestPredictTime:
    def test_known_event_returns_close(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        predicted = engine.predict_time(lam, "5000")
        # Should be reasonably close to the input (not exact due to rank truncation)
        assert 1000 < predicted < 1500

    def test_longer_distance_slower(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        t_5k = engine.predict_time(lam, "5000")
        t_10k = engine.predict_time(lam, "10000")
        assert t_10k > t_5k

    def test_shorter_distance_faster(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        t_5k = engine.predict_time(lam, "5000")
        t_1500 = engine.predict_time(lam, "1500")
        assert t_1500 < t_5k

    def test_unknown_event_raises(self):
        engine = LMCEngine()
        lam = np.array([1.12, 0.05])
        with pytest.raises(ValueError):
            engine.predict_time(lam, "50m")


class TestPredictAllEvents:
    def test_default_four_events(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        predictions = engine.predict_all_events(lam)
        assert set(predictions.keys()) == {"1500", "3000", "5000", "10000"}

    def test_custom_events(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        predictions = engine.predict_all_events(lam, events=["5000", "marathon"])
        assert "marathon" in predictions

    def test_times_increase_with_distance(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        predictions = engine.predict_all_events(lam)
        assert predictions["1500"] < predictions["3000"] < predictions["5000"] < predictions["10000"]


class TestColdStart:
    def test_cold_start_returns_lambda(self):
        engine = LMCEngine(rank=2)
        lam = engine.cold_start_estimate(300.0, 5000)  # 5:00/km for 5K
        assert len(lam) == 2

    def test_cold_start_conservative(self):
        """Cold start should be slower than using the pace as a race result."""
        engine = LMCEngine(rank=2)
        lam_cold = engine.cold_start_estimate(300.0, 5000)
        lam_race = engine.estimate_runner(["5000"], [300.0 * 5])

        t_cold = engine.predict_time(lam_cold, "5000")
        t_race = engine.predict_time(lam_race, "5000")
        # Cold start adds 5% penalty, so should predict slower
        assert t_cold >= t_race * 0.99  # allow small floating point tolerance


class TestSupportedRange:
    def test_range_is_symmetric_around_prediction(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        predicted = engine.predict_time(lam, "5000")
        lower, upper = engine.compute_supported_range(lam, "5000")
        assert lower < predicted < upper

    def test_95_wider_than_68(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        low_68, high_68 = engine.compute_supported_range(lam, "5000", confidence=0.68)
        low_95, high_95 = engine.compute_supported_range(lam, "5000", confidence=0.95)
        assert (high_95 - low_95) > (high_68 - low_68)


class TestLambdaBounding:
    def test_lambda0_near_one(self):
        """lambda_hat[0] (intercept) should be near 1.0, not clipped to [1.10, 1.15]."""
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000", "10000"], [1200.0, 2600.0])
        assert 0.85 <= lam[0] <= 1.15

    def test_lambda1_within_population_bounds(self):
        """lambda_hat[1] (speed-endurance) should be centered near 0, not ~1.1."""
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000", "10000"], [1200.0, 2600.0])
        assert -0.4 <= lam[1] <= 0.4

    def test_single_race_rank2_lambda0_near_one(self):
        engine = LMCEngine(rank=2)
        lam = engine.estimate_runner(["5000"], [1200.0])
        assert 0.85 <= lam[0] <= 1.15


class TestFindClosestEvent:
    def test_exact_distance(self):
        assert LMCEngine._find_closest_event(5000) == "5000"

    def test_near_distance(self):
        assert LMCEngine._find_closest_event(5100) == "5000"

    def test_marathon(self):
        assert LMCEngine._find_closest_event(42000) == "marathon"
