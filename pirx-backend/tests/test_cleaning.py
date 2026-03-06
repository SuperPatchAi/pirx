import pytest
from datetime import datetime
from app.models.activities import NormalizedActivity
from app.services.cleaning_service import (
    CleaningService,
    MIN_PACE_SEC_PER_KM,
    MAX_PACE_SEC_PER_KM,
    MIN_DURATION_SECONDS,
    MIN_DISTANCE_METERS,
)


def make_activity(**overrides) -> NormalizedActivity:
    """Factory for test activities with sensible defaults."""
    defaults = {
        "source": "strava",
        "timestamp": datetime(2026, 3, 1, 8, 0, 0),
        "duration_seconds": 1800,   # 30 min
        "distance_meters": 5000.0,  # 5 km
        "avg_hr": 150,
        "max_hr": 175,
        "avg_pace_sec_per_km": 360.0,  # 6:00/km
        "elevation_gain_m": 30.0,
        "calories": 350,
        "activity_type": "easy",
        "hr_zones": None,
        "laps": None,
        "fit_file_url": None,
    }
    defaults.update(overrides)
    return NormalizedActivity(**defaults)


class TestActivityTypeFilter:
    def test_easy_run_passes(self):
        a = make_activity(activity_type="easy")
        assert CleaningService.clean_activity(a) is not None

    def test_threshold_run_passes(self):
        a = make_activity(activity_type="threshold")
        assert CleaningService.clean_activity(a) is not None

    def test_interval_run_passes(self):
        a = make_activity(activity_type="interval")
        assert CleaningService.clean_activity(a) is not None

    def test_race_passes(self):
        a = make_activity(activity_type="race")
        assert CleaningService.clean_activity(a) is not None

    def test_cross_training_filtered(self):
        a = make_activity(activity_type="cross-training")
        assert CleaningService.clean_activity(a) is None

    def test_unknown_type_filtered(self):
        a = make_activity(activity_type="unknown")
        assert CleaningService.clean_activity(a) is None


class TestDurationFilter:
    def test_30min_passes(self):
        a = make_activity(duration_seconds=1800)
        assert CleaningService.clean_activity(a) is not None

    def test_exactly_3min_passes(self):
        a = make_activity(duration_seconds=180)
        assert CleaningService.clean_activity(a) is not None

    def test_under_3min_filtered(self):
        a = make_activity(duration_seconds=120)
        assert CleaningService.clean_activity(a) is None

    def test_race_60s_passes(self):
        """Races have relaxed minimum: 60 seconds."""
        a = make_activity(activity_type="race", duration_seconds=90, distance_meters=800)
        assert CleaningService.clean_activity(a) is not None

    def test_race_under_60s_filtered(self):
        a = make_activity(activity_type="race", duration_seconds=30, distance_meters=400)
        assert CleaningService.clean_activity(a) is None


class TestDistanceFilter:
    def test_5km_passes(self):
        a = make_activity(distance_meters=5000)
        assert CleaningService.clean_activity(a) is not None

    def test_exactly_1600m_passes(self):
        a = make_activity(distance_meters=1600, duration_seconds=480)
        assert CleaningService.clean_activity(a) is not None

    def test_under_1600m_filtered(self):
        a = make_activity(distance_meters=1000)
        assert CleaningService.clean_activity(a) is None

    def test_race_800m_passes(self):
        """Races have relaxed minimum: 400m."""
        a = make_activity(activity_type="race", distance_meters=800, duration_seconds=120)
        assert CleaningService.clean_activity(a) is not None


class TestPaceBoundsFilter:
    def test_normal_pace_passes(self):
        a = make_activity(avg_pace_sec_per_km=360)  # 6:00/km
        assert CleaningService.clean_activity(a) is not None

    def test_too_fast_filtered(self):
        """Faster than 3:43/km -> likely bike or GPS error."""
        a = make_activity(avg_pace_sec_per_km=200)
        assert CleaningService.clean_activity(a) is None

    def test_too_slow_filtered(self):
        """Slower than 15:00/km -> likely walking."""
        a = make_activity(avg_pace_sec_per_km=950)
        assert CleaningService.clean_activity(a) is None

    def test_pace_computed_from_distance_duration(self):
        """When pace not provided, compute from distance/duration."""
        a = make_activity(avg_pace_sec_per_km=None, duration_seconds=1800, distance_meters=5000)
        result = CleaningService.clean_activity(a)
        assert result is not None  # 360 sec/km is valid

    def test_computed_pace_too_fast_filtered(self):
        a = make_activity(avg_pace_sec_per_km=None, duration_seconds=200, distance_meters=1600)
        # 200s / 1.6km = 125 sec/km -> WAY too fast
        assert CleaningService.clean_activity(a) is None


class TestRelativePaceFilter:
    def test_normal_relative_pace_passes(self):
        a = make_activity(avg_pace_sec_per_km=360)
        assert CleaningService.clean_activity(a, runner_avg_pace=340) is not None

    def test_much_slower_than_avg_filtered(self):
        """1.5x slower than average -> likely mislabeled walk."""
        a = make_activity(avg_pace_sec_per_km=600)
        assert CleaningService.clean_activity(a, runner_avg_pace=350) is None

    def test_no_runner_avg_skips_relative(self):
        """When no runner avg, only absolute bounds apply."""
        a = make_activity(avg_pace_sec_per_km=500)
        assert CleaningService.clean_activity(a) is not None  # 500 < 900


class TestElevationFilter:
    def test_normal_elevation_passes(self):
        a = make_activity(elevation_gain_m=50, distance_meters=8000)
        assert CleaningService.clean_activity(a) is not None

    def test_zero_elevation_long_run_filtered(self):
        """Zero elevation on 10K+ outdoor run -> bad GPS data."""
        a = make_activity(elevation_gain_m=0, distance_meters=12000, duration_seconds=4200)
        assert CleaningService.clean_activity(a) is None

    def test_zero_elevation_medium_run_passes(self):
        """Zero elevation on sub-10K is OK (could be treadmill or track)."""
        a = make_activity(elevation_gain_m=0, distance_meters=8000, duration_seconds=2880)
        assert CleaningService.clean_activity(a) is not None

    def test_zero_elevation_short_run_passes(self):
        """Zero elevation on sub-5K is OK (could be track)."""
        a = make_activity(elevation_gain_m=0, distance_meters=3000, duration_seconds=900)
        assert CleaningService.clean_activity(a) is not None

    def test_null_elevation_passes(self):
        """None elevation should not trigger the filter."""
        a = make_activity(elevation_gain_m=None, distance_meters=10000, duration_seconds=3600)
        assert CleaningService.clean_activity(a) is not None


class TestBatchCleaning:
    def test_filters_batch(self):
        activities = [
            make_activity(activity_type="easy"),
            make_activity(activity_type="cross-training"),
            make_activity(activity_type="race", distance_meters=5000),
            make_activity(activity_type="easy", duration_seconds=60),  # too short
        ]
        result = CleaningService.clean_batch(activities)
        assert len(result) == 2  # easy + race pass; cross-training + short filtered

    def test_empty_input(self):
        assert CleaningService.clean_batch([]) == []


class TestComputeRunnerAvgPace:
    def test_computes_average(self):
        activities = [
            make_activity(avg_pace_sec_per_km=350),
            make_activity(avg_pace_sec_per_km=360),
            make_activity(avg_pace_sec_per_km=370),
        ]
        avg = CleaningService.compute_runner_avg_pace(activities)
        assert avg == pytest.approx(360.0)

    def test_insufficient_data_returns_none(self):
        activities = [make_activity(), make_activity()]
        avg = CleaningService.compute_runner_avg_pace(activities)
        assert avg is None  # Need at least 3

    def test_ignores_cross_training(self):
        activities = [
            make_activity(avg_pace_sec_per_km=350),
            make_activity(avg_pace_sec_per_km=360),
            make_activity(activity_type="cross-training", avg_pace_sec_per_km=400),
            make_activity(avg_pace_sec_per_km=370),
        ]
        avg = CleaningService.compute_runner_avg_pace(activities)
        assert avg == pytest.approx(360.0)  # cross-training excluded

    def test_ignores_extreme_paces(self):
        activities = [
            make_activity(avg_pace_sec_per_km=350),
            make_activity(avg_pace_sec_per_km=360),
            make_activity(avg_pace_sec_per_km=100),  # too fast, filtered
            make_activity(avg_pace_sec_per_km=370),
        ]
        avg = CleaningService.compute_runner_avg_pace(activities)
        assert avg == pytest.approx(360.0)
