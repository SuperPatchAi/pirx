import pytest
import numpy as np
from datetime import datetime, timedelta
from app.models.activities import NormalizedActivity
from app.services.feature_service import FeatureService, FEATURE_DOMAINS, ROLLING_WINDOW_WEIGHTS


def make_activity(days_ago: int = 0, distance: float = 5000.0, duration: int = 1800,
                  activity_type: str = "easy", avg_hr: int = 150,
                  hr_zones: list = None, laps: list = None,
                  pace: float = None) -> NormalizedActivity:
    ref = datetime(2026, 3, 6, 8, 0, 0)
    ts = ref - timedelta(days=days_ago)
    if pace is None and distance > 0:
        pace = duration / (distance / 1000)
    return NormalizedActivity(
        source="strava",
        timestamp=ts,
        duration_seconds=duration,
        distance_meters=distance,
        avg_hr=avg_hr,
        max_hr=avg_hr + 25,
        avg_pace_sec_per_km=pace,
        elevation_gain_m=30.0,
        calories=350,
        activity_type=activity_type,
        hr_zones=hr_zones,
        laps=laps,
        fit_file_url=None,
    )


REF_DATE = datetime(2026, 3, 6, 23, 59, 59)


class TestFeatureDomainsCoverage:
    def test_all_27_features_returned(self):
        activities = [make_activity(days_ago=i) for i in range(30)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        all_feature_names = []
        for domain_features in FEATURE_DOMAINS.values():
            all_feature_names.extend(domain_features)
        for name in all_feature_names:
            assert name in features, f"Missing feature: {name}"
        assert len(features) == 25


class TestVolumeFeatures:
    def test_rolling_distances(self):
        activities = [make_activity(days_ago=i, distance=5000) for i in range(45)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["rolling_distance_7d"] == pytest.approx(35000, rel=0.1)
        assert features["rolling_distance_21d"] > features["rolling_distance_7d"]
        assert features["rolling_distance_42d"] > features["rolling_distance_21d"]

    def test_sessions_per_week(self):
        activities = [make_activity(days_ago=i) for i in range(5)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["sessions_per_week"] == 5

    def test_long_run_count(self):
        activities = [
            make_activity(days_ago=1, distance=16000, duration=4800),
            make_activity(days_ago=3, distance=10000, duration=3600),
            make_activity(days_ago=8, distance=18000, duration=5400),
            make_activity(days_ago=15, distance=5000),
        ]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["long_run_count"] == 2

    def test_empty_activities(self):
        features = FeatureService.compute_all_features([], REF_DATE)
        assert features["rolling_distance_7d"] == 0
        assert features["sessions_per_week"] == 0


class TestIntensityFeatures:
    def test_zone_distribution(self):
        zones = [120.0, 1200.0, 300.0, 240.0, 60.0]
        activities = [make_activity(days_ago=i, hr_zones=zones) for i in range(10)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["z2_pct"] == pytest.approx(1200 / 1920, rel=0.01)
        assert features["z1_pct"] is not None
        sum_pcts = sum(features[f"z{i}_pct"] for i in range(1, 6))
        assert sum_pcts == pytest.approx(1.0, rel=0.01)

    def test_no_hr_zones_returns_none(self):
        activities = [make_activity(days_ago=i) for i in range(5)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["z1_pct"] is None
        assert features["threshold_density_min_week"] is None

    def test_threshold_density(self):
        zones = [0, 0, 0, 600.0, 0]
        activities = [make_activity(days_ago=i, hr_zones=zones) for i in range(21)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["threshold_density_min_week"] == pytest.approx(70.0, rel=0.1)


class TestConsistencyFeatures:
    def test_acwr_returns_value(self):
        activities = [make_activity(days_ago=i, distance=5000) for i in range(60)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["acwr_4w"] is not None
        assert features["acwr_6w"] is not None
        assert features["acwr_8w"] is not None

    def test_acwr_consistent_load_near_1(self):
        """Consistent daily training should give ACWR near 1.0."""
        activities = [make_activity(days_ago=i, distance=5000) for i in range(60)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert 0.8 <= features["acwr_4w"] <= 1.3

    def test_weekly_load_stddev(self):
        activities = [make_activity(days_ago=i, distance=5000) for i in range(42)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["weekly_load_stddev"] is not None
        assert features["weekly_load_stddev"] < 5000

    def test_empty_gives_none_acwr(self):
        features = FeatureService.compute_all_features([], REF_DATE)
        assert features["acwr_4w"] is None


class TestEfficiencyFeatures:
    def test_matched_hr_band_pace(self):
        activities = [
            make_activity(days_ago=1, avg_hr=148, pace=340.0, distance=5000, duration=1700),
            make_activity(days_ago=3, avg_hr=150, pace=345.0, distance=5000, duration=1725),
            make_activity(days_ago=5, avg_hr=165, pace=310.0, distance=5000, duration=1550),
        ]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["matched_hr_band_pace"] == pytest.approx(342.5, rel=0.01)

    def test_no_matching_hr_returns_none(self):
        activities = [make_activity(days_ago=1, avg_hr=170)]
        features = FeatureService.compute_all_features(activities, REF_DATE)
        assert features["matched_hr_band_pace"] is None


class TestPhysiologicalFeatures:
    def test_stubs_return_none(self):
        features = FeatureService.compute_all_features([], REF_DATE)
        assert features["resting_hr_trend"] is None
        assert features["hrv_trend"] is None
        assert features["sleep_score_trend"] is None


class TestWeightedScore:
    def test_weighted_score(self):
        features = {
            "rolling_distance_7d": 35000,
            "rolling_distance_21d": 105000,
            "rolling_distance_42d": 210000,
        }
        score = FeatureService.compute_weighted_feature_score(features)
        assert score == pytest.approx(35000, rel=0.01)

    def test_returns_none_with_missing(self):
        assert FeatureService.compute_weighted_feature_score({}) is None
