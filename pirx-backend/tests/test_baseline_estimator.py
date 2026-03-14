import pytest
from app.ml.baseline_estimator import (
    estimate_5k_baseline,
    DEFAULT_5K_SECONDS,
    _extract_valid_paces,
    _detect_race_result,
    _fastest_sustained_effort,
)


def _make_activity(
    pace: float = 300.0,
    distance: float = 8000.0,
    duration: float = 2400.0,
    avg_hr: int | None = 145,
    max_hr: int | None = 185,
) -> dict:
    return {
        "avg_pace_sec_per_km": pace,
        "distance_meters": distance,
        "duration_seconds": duration,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
    }


class TestEstimate5kBaseline:
    def test_default_with_no_activities(self):
        assert estimate_5k_baseline([]) == DEFAULT_5K_SECONDS

    def test_default_with_too_few_activities(self):
        acts = [_make_activity() for _ in range(2)]
        assert estimate_5k_baseline(acts) == DEFAULT_5K_SECONDS

    def test_tier3_p10_for_training_only(self):
        """Runner with all easy runs should get P10-based estimate, not median*5."""
        paces = [290, 295, 300, 305, 310, 315, 320, 325, 330, 335]
        acts = [_make_activity(pace=p, avg_hr=140, max_hr=185) for p in paces]
        result = estimate_5k_baseline(acts)
        # P10 ~ 290, * 5 * 0.96 = 1392
        # Old median would have been: 310 * 5 = 1550
        assert result < 1450
        assert result > 1300

    def test_tier1_race_detection(self):
        """A 5K at race HR should be detected as tier-1."""
        acts = [_make_activity(pace=300, avg_hr=140, max_hr=185) for _ in range(10)]
        # Add a 5K "race": 5000m in 1110s (18:30), HR 170/185 = 91.9%
        acts.append(_make_activity(
            pace=222.0, distance=5000.0, duration=1110.0,
            avg_hr=170, max_hr=185,
        ))
        result = estimate_5k_baseline(acts)
        # Should detect the 5K race and use it directly: ~1110s
        assert result == pytest.approx(1110.0, abs=5)

    def test_tier1_10k_race_scales_to_5k(self):
        """A 10K race should be detected and Riegel-scaled to 5K."""
        acts = [_make_activity(pace=300, avg_hr=140, max_hr=185) for _ in range(10)]
        # Add a 10K "race": 10000m in 2280s (38:00), HR 165/185 = 89.2%
        acts.append(_make_activity(
            pace=228.0, distance=10000.0, duration=2280.0,
            avg_hr=165, max_hr=185,
        ))
        result = estimate_5k_baseline(acts)
        # Riegel 10K->5K: 2280 * (5000/10000)^1.06 ≈ 1095
        assert result < 1200
        assert result > 1000

    def test_tier2_sustained_effort(self):
        """A fast 4km run at high HR should be picked up by tier-2 with Riegel scaling."""
        acts = [_make_activity(pace=310, avg_hr=140, max_hr=185) for _ in range(10)]
        acts.append(_make_activity(
            pace=240.0, distance=4000.0, duration=960.0,
            avg_hr=163, max_hr=185,
        ))
        result = estimate_5k_baseline(acts)
        assert result <= 1250
        assert result > 900

    def test_no_hr_data_falls_to_tier3(self):
        """Without HR data, race/effort tiers are skipped; tier-3 P10 is used."""
        paces = [290, 295, 300, 305, 310, 315, 320, 325, 330, 335]
        acts = [_make_activity(pace=p, avg_hr=None, max_hr=None) for p in paces]
        result = estimate_5k_baseline(acts)
        # Tier 3: P10=290, 290*5*0.96 = 1392
        assert 1300 < result < 1500

    def test_much_better_than_old_median_for_fast_runner(self):
        """A sub-18:30 runner should NOT get a 25:00+ baseline."""
        paces = [280, 290, 300, 305, 307, 310, 312, 315, 320, 325]
        acts = [_make_activity(pace=p, avg_hr=140, max_hr=185) for p in paces]
        result = estimate_5k_baseline(acts)
        # Old system: median=310, 310*5=1550 (25:50!)
        # New: P10=280, 280*5*0.96=1344 (22:24) -- much closer to reality
        assert result < 1400

    def test_invalid_paces_filtered(self):
        """Activities with paces outside [223, 900] are ignored."""
        acts = [
            _make_activity(pace=200),  # too fast (cycling)
            _make_activity(pace=950),  # too slow (walking)
            _make_activity(pace=300),
            _make_activity(pace=310),
            _make_activity(pace=320),
        ]
        result = estimate_5k_baseline(acts)
        # Only 3 valid activities, tier 3: P10 of [300, 310, 320] = 300
        assert result > 0

    def test_short_distances_filtered(self):
        """Activities shorter than 1600m are ignored."""
        acts = [_make_activity(pace=300, distance=500) for _ in range(5)]
        result = estimate_5k_baseline(acts)
        assert result == DEFAULT_5K_SECONDS


class TestExtractValidPaces:
    def test_filters_by_pace_bounds(self):
        acts = [
            _make_activity(pace=200),
            _make_activity(pace=300),
            _make_activity(pace=950),
        ]
        result = _extract_valid_paces(acts)
        assert len(result) == 1
        assert result[0][0] == 300.0

    def test_computes_pace_from_duration_distance(self):
        acts = [{"avg_pace_sec_per_km": None, "distance_meters": 5000.0,
                 "duration_seconds": 1500.0, "avg_hr": None, "max_hr": None}]
        result = _extract_valid_paces(acts)
        assert len(result) == 1
        assert result[0][0] == pytest.approx(300.0)


class TestDetectRaceResult:
    def test_detects_5k_race(self):
        acts = [_make_activity(pace=310, avg_hr=140, max_hr=185) for _ in range(8)]
        acts.append(_make_activity(
            pace=220.0, distance=5000.0, duration=1100.0,
            avg_hr=168, max_hr=185,
        ))
        result = _detect_race_result(acts)
        assert result is not None
        assert result == pytest.approx(1100.0, abs=5)

    def test_none_when_no_race(self):
        acts = [_make_activity(pace=310, avg_hr=140, max_hr=185) for _ in range(8)]
        assert _detect_race_result(acts) is None

    def test_needs_minimum_activities(self):
        acts = [_make_activity(
            pace=220.0, distance=5000.0, duration=1100.0,
            avg_hr=168, max_hr=185,
        )]
        assert _detect_race_result(acts) is None


class TestFastestSustainedEffort:
    def test_finds_hard_tempo(self):
        acts = [_make_activity(pace=310, avg_hr=140, max_hr=185) for _ in range(5)]
        acts.append(_make_activity(
            pace=250.0, distance=5000.0, duration=1250.0,
            avg_hr=165, max_hr=185,
        ))
        result = _fastest_sustained_effort(acts)
        assert result is not None
        assert result == pytest.approx(1250.0, abs=5)  # 250 * 5

    def test_none_when_no_high_hr_efforts(self):
        acts = [_make_activity(pace=310, avg_hr=140, max_hr=185) for _ in range(5)]
        assert _fastest_sustained_effort(acts) is None

    def test_ignores_short_distances(self):
        acts = [_make_activity(
            pace=200.0, distance=1000.0, duration=200.0,
            avg_hr=175, max_hr=185,
        )]
        assert _fastest_sustained_effort(acts) is None
