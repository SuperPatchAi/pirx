"""Smart baseline estimation from activity history.

Replaces the naive 'median training pace * 5km' approach with a
multi-signal, tiered strategy that accounts for the difference between
training pace and race pace.

Tiers (highest confidence first):
  1. Detected race result — standard distance + high HR + fast pace
  2. Fastest sustained effort — >= 3 km with HR > 85% of estimated max
  3. Best-effort percentile — P10 pace with training-to-race discount
  4. Adjusted median — median pace with 0.80 training-to-race factor
  5. Cold-start default — 25:00 (1500 s)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_5K_SECONDS = 1500.0

MIN_PACE = 223   # 3:43/km — faster is likely bike/GPS error
MAX_PACE = 900   # 15:00/km — slower is likely walking
MIN_DISTANCE = 1600  # ~1 mile
MIN_ACTIVITIES = 3

RACE_DISTANCE_RANGES = [
    (1400, 1600, 1500),     # 1500m / mile
    (2900, 3200, 3000),     # 3000m / 2-mile
    (4750, 5250, 5000),     # 5K
    (9500, 10500, 10000),   # 10K
    (20500, 21700, 21097),  # Half marathon
    (41000, 43000, 42195),  # Marathon
]


def estimate_5k_baseline(activities: list[dict]) -> float:
    """Estimate a runner's 5K race capability from raw activity dicts.

    Each activity dict should have keys: avg_pace_sec_per_km, distance_meters,
    duration_seconds, avg_hr, max_hr.  Values may be None.

    Returns estimated 5K time in seconds.
    """
    valid = _extract_valid_paces(activities)
    if len(valid) < MIN_ACTIVITIES:
        logger.info("Baseline estimation: fewer than %d valid activities, using default", MIN_ACTIVITIES)
        return DEFAULT_5K_SECONDS

    # --- Tier 1: Detected race result ---
    race_time = _detect_race_result(activities)
    if race_time is not None:
        logger.info("Baseline estimation tier-1 (race detected): %.0fs", race_time)
        return race_time

    # --- Tier 2: Fastest sustained effort (>= 3km, HR > 85% max) ---
    effort_time = _fastest_sustained_effort(activities)
    if effort_time is not None:
        logger.info("Baseline estimation tier-2 (sustained effort): %.0fs", effort_time)
        return effort_time

    paces = sorted(p for p, _ in valid)

    # --- Tier 3: P10 pace with race discount ---
    p10_idx = max(0, len(paces) // 10)
    p10_pace = paces[p10_idx]
    tier3_estimate = p10_pace * 5.0 * 0.96
    if tier3_estimate >= 600:  # sanity: at least 10:00 5K
        logger.info(
            "Baseline estimation tier-3 (P10 pace): %.0fs (P10=%.0f s/km from %d activities)",
            tier3_estimate, p10_pace, len(paces),
        )
        return tier3_estimate

    # --- Tier 4: Adjusted median ---
    median_pace = paces[len(paces) // 2]
    tier4_estimate = median_pace * 5.0 * 0.80
    if tier4_estimate >= 600:
        logger.info(
            "Baseline estimation tier-4 (adjusted median): %.0fs (median=%.0f s/km)",
            tier4_estimate, median_pace,
        )
        return tier4_estimate

    # --- Tier 5: Default ---
    logger.info("Baseline estimation tier-5 (default): %.0fs", DEFAULT_5K_SECONDS)
    return DEFAULT_5K_SECONDS


def _extract_valid_paces(activities: list[dict]) -> list[tuple[float, dict]]:
    """Return list of (pace_sec_per_km, activity_dict) for valid running activities."""
    result = []
    for a in activities:
        pace = _get_pace(a)
        dist = float(a.get("distance_meters") or 0)
        if pace and MIN_PACE <= pace <= MAX_PACE and dist > MIN_DISTANCE:
            result.append((pace, a))
    return result


def _get_pace(a: dict) -> Optional[float]:
    """Extract or compute pace from an activity dict."""
    pace = a.get("avg_pace_sec_per_km")
    if pace is not None:
        return float(pace)
    dist = float(a.get("distance_meters") or 0)
    dur = float(a.get("duration_seconds") or 0)
    if dist > 0 and dur > 0:
        return dur / (dist / 1000)
    return None


def _get_hr_pct(a: dict) -> Optional[float]:
    """Compute avg HR as fraction of estimated max HR."""
    avg_hr = a.get("avg_hr")
    max_hr = a.get("max_hr")
    if not avg_hr:
        return None
    estimated_max = max_hr if max_hr and max_hr > 150 else 190
    return avg_hr / estimated_max


def _detect_race_result(activities: list[dict]) -> Optional[float]:
    """Tier 1: Find an activity that looks like a race and project to 5K.

    Criteria: standard race distance (+-5%), HR >= 83% of max, and pace
    faster than the P25 of all training paces (allowing sub-3:43 race paces).
    """
    valid = _extract_valid_paces(activities)
    if len(valid) < MIN_ACTIVITIES:
        return None

    paces_sorted = sorted(p for p, _ in valid)
    p25_threshold = paces_sorted[max(0, len(paces_sorted) // 4)]

    best_race: Optional[tuple[float, float]] = None  # (5k_equivalent, confidence)

    for a in activities:
        dist = float(a.get("distance_meters") or 0)
        dur = float(a.get("duration_seconds") or 0)
        pace = _get_pace(a)
        hr_pct = _get_hr_pct(a)

        if pace is None or dist < MIN_DISTANCE or dur <= 0:
            continue
        if hr_pct is None or hr_pct < 0.83:
            continue
        if pace > p25_threshold:
            continue

        for lo, hi, canonical_dist in RACE_DISTANCE_RANGES:
            if lo <= dist <= hi:
                if canonical_dist == 5000:
                    equiv_5k = dur
                else:
                    from app.ml.event_scaling import EventScaler
                    equiv_5k = EventScaler.riegel_scale(dur, canonical_dist, 5000)

                confidence = hr_pct
                if best_race is None or confidence > best_race[1]:
                    best_race = (equiv_5k, confidence)
                break

    if best_race is not None:
        return best_race[0]
    return None


def _fastest_sustained_effort(activities: list[dict]) -> Optional[float]:
    """Tier 2: Find fastest effort >= 3km with HR > 85% max, project to 5K."""
    candidates: list[float] = []

    for a in activities:
        dist = float(a.get("distance_meters") or 0)
        dur = float(a.get("duration_seconds") or 0)
        pace = _get_pace(a)

        if dist < 3000 or dur <= 0 or pace is None:
            continue
        if not (MIN_PACE <= pace <= MAX_PACE):
            continue

        hr_pct = _get_hr_pct(a)
        if hr_pct is None or hr_pct < 0.85:
            continue

        equiv_5k = pace * 5.0
        candidates.append(equiv_5k)

    if not candidates:
        return None

    return min(candidates)
