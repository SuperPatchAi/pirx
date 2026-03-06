from typing import Optional
from app.models.activities import NormalizedActivity


# Absolute pace bounds (sec/km)
MIN_PACE_SEC_PER_KM = 223  # faster than 3:43/km -> likely bike/ski
MAX_PACE_SEC_PER_KM = 900  # slower than 15:00/km -> likely walk

# Minimum thresholds
MIN_DURATION_SECONDS = 180   # 3 minutes
MIN_DISTANCE_METERS = 1600   # ~1 mile

# Activity types that count as "running" for the projection engine
RUNNING_TYPES = {"easy", "threshold", "interval", "race"}


class CleaningService:
    """Filters and validates activities for the PIRX projection engine.

    Based on Dash 2024 research. Activities that fail any filter are
    excluded from feature engineering and projection computation.
    Race activities get relaxed filtering (shorter races are valid).
    """

    @staticmethod
    def clean_activity(
        activity: NormalizedActivity,
        runner_avg_pace: Optional[float] = None,
    ) -> Optional[NormalizedActivity]:
        """Apply cleaning filters to a single activity.

        Returns the activity if it passes all checks, None if filtered out.

        Args:
            activity: Normalized activity from wearable sync
            runner_avg_pace: Runner's average pace in sec/km (for relative filter).
                If None, only absolute bounds are applied.
        """
        # Filter 1: Must be a running activity type
        if activity.activity_type not in RUNNING_TYPES:
            return None

        # Filter 2: Minimum duration (races get shorter minimum: 60s)
        min_dur = 60 if activity.activity_type == "race" else MIN_DURATION_SECONDS
        if activity.duration_seconds < min_dur:
            return None

        # Filter 3: Minimum distance (races get shorter minimum: 400m)
        min_dist = 400 if activity.activity_type == "race" else MIN_DISTANCE_METERS
        if activity.distance_meters < min_dist:
            return None

        # Filter 4: Compute pace if not provided
        pace = activity.avg_pace_sec_per_km
        if pace is None and activity.distance_meters > 0:
            pace = activity.duration_seconds / (activity.distance_meters / 1000)

        if pace is not None:
            # Filter 5: Absolute pace bounds
            if pace < MIN_PACE_SEC_PER_KM:
                return None  # Too fast — likely cycling or GPS error
            if pace > MAX_PACE_SEC_PER_KM:
                return None  # Too slow — likely walking

            # Filter 6: Relative pace check (if runner avg known)
            if runner_avg_pace is not None and pace > runner_avg_pace * 1.5:
                return None  # Much slower than usual — likely mislabeled

        # Filter 7: Missing elevation on long outdoor runs (GPS data quality)
        # Skip this filter for treadmill/indoor runs which legitimately have 0 elevation
        is_indoor = getattr(activity, "source", "") in ("treadmill", "indoor")
        if (not is_indoor
            and activity.elevation_gain_m is not None
            and activity.elevation_gain_m == 0
            and activity.distance_meters > 10000):
            return None  # Zero elevation on 10K+ outdoor run suggests bad GPS

        return activity

    @staticmethod
    def clean_batch(
        activities: list[NormalizedActivity],
        runner_avg_pace: Optional[float] = None,
    ) -> list[NormalizedActivity]:
        """Clean a batch of activities, returning only valid ones."""
        cleaned = []
        for activity in activities:
            result = CleaningService.clean_activity(activity, runner_avg_pace)
            if result is not None:
                cleaned.append(result)
        return cleaned

    @staticmethod
    def compute_runner_avg_pace(activities: list[NormalizedActivity]) -> Optional[float]:
        """Compute a runner's average pace from their recent activities.

        Uses only running activities with valid pace data.
        Returns pace in seconds per km, or None if insufficient data.
        """
        paces = []
        for a in activities:
            if a.activity_type in RUNNING_TYPES and a.distance_meters > 0:
                pace = a.avg_pace_sec_per_km
                if pace is None:
                    pace = a.duration_seconds / (a.distance_meters / 1000)
                if MIN_PACE_SEC_PER_KM <= pace <= MAX_PACE_SEC_PER_KM:
                    paces.append(pace)

        if len(paces) < 3:
            return None  # Need at least 3 activities for reliable avg

        return sum(paces) / len(paces)
