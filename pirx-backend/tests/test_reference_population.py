import pytest
import numpy as np
from app.ml.reference_population import (
    ReferencePopulation, SyntheticRunner, get_reference_population,
    POPULATION_SIZE,
)


class TestPopulationGeneration:
    def test_generates_correct_size(self):
        pop = ReferencePopulation(size=100)
        assert len(pop.runners) == 100

    def test_default_size_1000(self):
        pop = get_reference_population()
        assert len(pop.runners) == POPULATION_SIZE

    def test_deterministic_with_seed(self):
        pop1 = ReferencePopulation(seed=42, size=10)
        pop2 = ReferencePopulation(seed=42, size=10)
        for r1, r2 in zip(pop1.runners, pop2.runners):
            assert r1.time_5000 == r2.time_5000

    def test_different_seed_different_results(self):
        pop1 = ReferencePopulation(seed=42, size=10)
        pop2 = ReferencePopulation(seed=99, size=10)
        assert pop1.runners[0].time_5000 != pop2.runners[0].time_5000


class TestSyntheticRunnerProperties:
    @pytest.fixture
    def pop(self):
        return ReferencePopulation(seed=42, size=200)

    def test_lambda1_in_range(self, pop):
        for r in pop.runners:
            assert 1.08 <= r.lambda1 <= 1.17

    def test_zone_percentages_sum_to_one(self, pop):
        for r in pop.runners:
            total = r.z1_pct + r.z2_pct + r.z3_pct + r.z4_pct + r.z5_pct
            assert total == pytest.approx(1.0, abs=0.01)

    def test_times_increase_with_distance(self, pop):
        for r in pop.runners:
            assert r.time_1500 < r.time_3000 < r.time_5000 < r.time_10000

    def test_performance_levels_assigned(self, pop):
        levels = {r.performance_level for r in pop.runners}
        assert "beginner" in levels or "intermediate" in levels
        assert all(r.performance_level in ("beginner", "intermediate", "advanced", "elite") for r in pop.runners)

    def test_training_types_diverse(self, pop):
        types = {r.training_type for r in pop.runners}
        assert len(types) >= 2  # at least 2 training types

    def test_weekly_km_reasonable(self, pop):
        for r in pop.runners:
            assert 10 <= r.weekly_km <= 180

    def test_age_reasonable(self, pop):
        for r in pop.runners:
            assert 18 <= r.age <= 75

    def test_bmi_reasonable(self, pop):
        for r in pop.runners:
            assert 16 <= r.bmi <= 35


class TestPercentileCalculations:
    @pytest.fixture
    def pop(self):
        return ReferencePopulation(seed=42, size=200)

    def test_fast_runner_high_percentile(self, pop):
        pct = pop.get_percentile("5000", 900.0)  # 15:00 5K
        assert pct > 70

    def test_slow_runner_low_percentile(self, pop):
        pct = pop.get_percentile("5000", 2400.0)  # 40:00 5K
        assert pct < 30

    def test_exponent_percentile(self, pop):
        pct = pop.get_exponent_percentile(1.10)  # Very low = endurance gifted
        assert pct > 50


class TestSimilarRunners:
    def test_similar_runners_returns_correct_count(self):
        pop = ReferencePopulation(seed=42, size=100)
        similar = pop.get_similar_runners(1200, 40, n=5)
        assert len(similar) == 5

    def test_similar_runners_are_close(self):
        pop = ReferencePopulation(seed=42, size=200)
        similar = pop.get_similar_runners(1200, 40, n=3)
        for r in similar:
            assert abs(r.time_5000 - 1200) < 500


class TestCalibrationData:
    def test_calibration_returns_all_keys(self):
        pop = ReferencePopulation(seed=42, size=200)
        cal = pop.get_calibration_data("intermediate")
        assert "count" in cal
        assert "lambda1_mean" in cal
        assert "time_5000_median" in cal
        assert "supported_range_pct" in cal
        assert "training_type_distribution" in cal

    def test_population_summary(self):
        pop = ReferencePopulation(seed=42, size=100)
        summary = pop.get_population_summary()
        assert summary["total_runners"] == 100
        assert "lambda1_range" in summary
        assert "performance_distribution" in summary
