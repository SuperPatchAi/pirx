import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.models.activities import NormalizedActivity


ROLLING_WINDOW_WEIGHTS = {
    "7d": 0.45,
    "8_21d": 0.35,
    "22_90d": 0.20,
}

FEATURE_DOMAINS = {
    "volume": [
        "rolling_distance_7d", "rolling_distance_21d", "rolling_distance_42d",
        "rolling_distance_90d", "sessions_per_week", "long_run_count",
    ],
    "intensity": [
        "z1_pct", "z2_pct", "z3_pct", "z4_pct", "z5_pct",
        "threshold_density_min_week", "speed_exposure_min_week",
    ],
    "efficiency": [
        "matched_hr_band_pace", "hr_drift_sustained", "late_session_pace_decay",
    ],
    "consistency": [
        "weekly_load_stddev", "block_variance",
        "session_density_stability", "acwr_4w", "acwr_6w", "acwr_8w",
    ],
    "physiological": [
        "resting_hr_trend", "hrv_trend", "sleep_score_trend",
    ],
}


class FeatureService:
    """Computes 27 rolling-window features across 5 domains from activity data."""

    @staticmethod
    def compute_all_features(
        activities: list[NormalizedActivity],
        reference_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> dict[str, Optional[float]]:
        """Compute all features from a list of cleaned activities.

        Args:
            activities: Cleaned running activities, sorted by timestamp
            reference_date: Date to compute features relative to (default: now)
            user_id: User ID for fetching physiological data (optional)

        Returns:
            Dict of feature_name -> value (None if insufficient data)
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)
        if reference_date.tzinfo is not None:
            reference_date = reference_date.replace(tzinfo=None)

        features = {}
        features.update(FeatureService._compute_volume(activities, reference_date))
        features.update(FeatureService._compute_intensity(activities, reference_date))
        features.update(FeatureService._compute_efficiency(activities, reference_date))
        features.update(FeatureService._compute_consistency(activities, reference_date))
        features.update(FeatureService._compute_physiological(user_id))
        return features

    @staticmethod
    def _filter_window(
        activities: list[NormalizedActivity], ref: datetime, days: int
    ) -> list[NormalizedActivity]:
        """Filter activities within the last N days from reference date."""
        cutoff = ref - timedelta(days=days)
        return [
            a for a in activities
            if (a.timestamp.replace(tzinfo=None) if a.timestamp.tzinfo else a.timestamp) >= cutoff
        ]

    # --- Volume Domain ---
    @staticmethod
    def _compute_volume(
        activities: list[NormalizedActivity], ref: datetime
    ) -> dict:
        w7 = FeatureService._filter_window(activities, ref, 7)
        w21 = FeatureService._filter_window(activities, ref, 21)
        w42 = FeatureService._filter_window(activities, ref, 42)
        w90 = FeatureService._filter_window(activities, ref, 90)

        dist_7 = sum(a.distance_meters for a in w7)
        dist_21 = sum(a.distance_meters for a in w21)
        dist_42 = sum(a.distance_meters for a in w42)
        dist_90 = sum(a.distance_meters for a in w90)

        sessions_per_week = len(w7)

        long_run_count = sum(1 for a in w42 if a.distance_meters >= 15000)

        return {
            "rolling_distance_7d": dist_7,
            "rolling_distance_21d": dist_21,
            "rolling_distance_42d": dist_42,
            "rolling_distance_90d": dist_90,
            "sessions_per_week": sessions_per_week,
            "long_run_count": long_run_count,
        }

    # --- Intensity Domain ---
    @staticmethod
    def _compute_intensity(
        activities: list[NormalizedActivity], ref: datetime
    ) -> dict:
        w21 = FeatureService._filter_window(activities, ref, 21)

        total_zone_time = 0.0
        zone_times = [0.0] * 5

        for a in w21:
            if a.hr_zones and len(a.hr_zones) >= 5:
                for i in range(5):
                    zone_times[i] += a.hr_zones[i]
                    total_zone_time += a.hr_zones[i]

        if total_zone_time > 0:
            z_pcts = {
                f"z{i+1}_pct": zone_times[i] / total_zone_time for i in range(5)
            }
        else:
            z_pcts = {f"z{i+1}_pct": None for i in range(5)}

        threshold_min_week = (
            (zone_times[3] / 60) / (21 / 7) if total_zone_time > 0 else None
        )
        speed_min_week = (
            (zone_times[4] / 60) / (21 / 7) if total_zone_time > 0 else None
        )

        return {
            **z_pcts,
            "threshold_density_min_week": threshold_min_week,
            "speed_exposure_min_week": speed_min_week,
        }

    # --- Efficiency Domain ---
    @staticmethod
    def _compute_efficiency(
        activities: list[NormalizedActivity], ref: datetime
    ) -> dict:
        w21 = FeatureService._filter_window(activities, ref, 21)

        matched_paces: list[float] = []
        for a in w21:
            if a.avg_hr and 140 <= a.avg_hr <= 155 and a.avg_pace_sec_per_km:
                matched_paces.append(a.avg_pace_sec_per_km)

        matched_hr_band_pace = np.mean(matched_paces) if matched_paces else None

        hr_drifts: list[float] = []
        decay_values: list[float] = []
        for a in w21:
            if a.laps and len(a.laps) >= 4:
                half = len(a.laps) // 2
                first_half = a.laps[:half]
                second_half = a.laps[half:]

                first_paces = [
                    l.get("avg_pace_sec_per_km", 0)
                    for l in first_half
                    if l.get("avg_pace_sec_per_km")
                ]
                second_paces = [
                    l.get("avg_pace_sec_per_km", 0)
                    for l in second_half
                    if l.get("avg_pace_sec_per_km")
                ]

                if not first_paces or not second_paces:
                    continue

                first_pace = float(np.mean(first_paces))
                second_pace = float(np.mean(second_paces))

                if first_pace > 0 and second_pace > 0:
                    drift = (second_pace - first_pace) / first_pace
                    hr_drifts.append(drift)

                    quarter = max(len(a.laps) // 4, 1)
                    last_quarter = a.laps[-quarter:]
                    lq_paces = [
                        l.get("avg_pace_sec_per_km", 0)
                        for l in last_quarter
                        if l.get("avg_pace_sec_per_km")
                    ]
                    if lq_paces:
                        last_q_pace = float(np.mean(lq_paces))
                        if last_q_pace > 0:
                            decay = (last_q_pace - first_pace) / first_pace
                            decay_values.append(decay)

        return {
            "matched_hr_band_pace": (
                float(matched_hr_band_pace)
                if matched_hr_band_pace is not None
                else None
            ),
            "hr_drift_sustained": (
                float(np.mean(hr_drifts)) if hr_drifts else None
            ),
            "late_session_pace_decay": (
                float(np.mean(decay_values)) if decay_values else None
            ),
        }

    # --- Consistency Domain ---
    @staticmethod
    def _compute_consistency(
        activities: list[NormalizedActivity], ref: datetime
    ) -> dict:
        w42 = FeatureService._filter_window(activities, ref, 42)

        weekly_loads: list[float] = []
        for week_offset in range(6):
            week_start = ref - timedelta(days=7 * (week_offset + 1))
            week_end = ref - timedelta(days=7 * week_offset)
            week_activities = [
                a for a in w42 if week_start <= a.timestamp < week_end
            ]
            weekly_loads.append(sum(a.distance_meters for a in week_activities))

        weekly_load_stddev = float(np.std(weekly_loads)) if weekly_loads else None

        block_loads: list[float] = []
        for block_offset in range(3):
            block_start = ref - timedelta(days=14 * (block_offset + 1))
            block_end = ref - timedelta(days=14 * block_offset)
            block_activities = [
                a for a in w42 if block_start <= a.timestamp < block_end
            ]
            block_loads.append(sum(a.distance_meters for a in block_activities))

        block_variance = float(np.var(block_loads)) if block_loads else None

        weekly_session_counts: list[int] = []
        for week_offset in range(6):
            week_start = ref - timedelta(days=7 * (week_offset + 1))
            week_end = ref - timedelta(days=7 * week_offset)
            count = sum(1 for a in w42 if week_start <= a.timestamp < week_end)
            weekly_session_counts.append(count)

        session_density_stability = (
            float(np.std(weekly_session_counts)) if weekly_session_counts else None
        )

        acwr_4w = FeatureService._compute_acwr(
            activities, ref, acute_days=7, chronic_days=28
        )
        acwr_6w = FeatureService._compute_acwr(
            activities, ref, acute_days=7, chronic_days=42
        )
        acwr_8w = FeatureService._compute_acwr(
            activities, ref, acute_days=7, chronic_days=56
        )

        return {
            "weekly_load_stddev": weekly_load_stddev,
            "block_variance": block_variance,
            "session_density_stability": session_density_stability,
            "acwr_4w": acwr_4w,
            "acwr_6w": acwr_6w,
            "acwr_8w": acwr_8w,
        }

    @staticmethod
    def _compute_acwr(
        activities: list[NormalizedActivity],
        ref: datetime,
        acute_days: int,
        chronic_days: int,
    ) -> Optional[float]:
        """Compute Acute:Chronic Workload Ratio using EWMA smoothing."""
        daily_loads: list[float] = []
        for day_offset in range(chronic_days):
            day = ref - timedelta(days=day_offset)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_load = sum(
                a.distance_meters
                for a in activities
                if day_start <= a.timestamp < day_end
            )
            daily_loads.append(day_load)

        daily_loads.reverse()  # oldest first

        if not daily_loads or all(d == 0 for d in daily_loads):
            return None

        loads = np.array(daily_loads, dtype=float)

        acute_alpha = 2.0 / (acute_days + 1)
        chronic_alpha = 2.0 / (chronic_days + 1)

        def ewma(arr: np.ndarray, alpha: float) -> float:
            non_zero = arr[arr > 0]
            seed = float(np.mean(non_zero)) if len(non_zero) > 0 else 0.0
            result = seed
            for val in arr:
                result = alpha * val + (1 - alpha) * result
            return float(result)

        acute_load = (
            ewma(loads[-acute_days:], acute_alpha)
            if len(loads) >= acute_days
            else ewma(loads, acute_alpha)
        )
        chronic_load = ewma(loads, chronic_alpha)

        if chronic_load <= 0:
            return 1.0

        return float(acute_load / chronic_load)

    # --- Physiological Domain ---
    @staticmethod
    def _compute_physiological(user_id: str | None = None) -> dict:
        """Physiological features from wearable/manual physiology data.

        Computes 7-day trends for resting HR, HRV, and sleep score.
        Falls back to None when no data is available.
        """
        defaults = {"resting_hr_trend": None, "hrv_trend": None, "sleep_score_trend": None}
        if not user_id:
            return defaults
        try:
            from app.services.supabase_client import SupabaseService
            db = SupabaseService()
            entries = db.get_recent_physiology(user_id, limit=14)
            if not entries or len(entries) < 3:
                return defaults

            hr_vals = [e["resting_hr"] for e in entries if e.get("resting_hr") is not None]
            hrv_vals = [e["hrv"] for e in entries if e.get("hrv") is not None]
            sleep_vals = [e["sleep_score"] for e in entries if e.get("sleep_score") is not None]

            def trend_slope(vals: list) -> float | None:
                if len(vals) < 3:
                    return None
                recent = vals[:7] if len(vals) >= 7 else vals
                older = vals[7:] if len(vals) >= 7 else vals[:len(vals)//2]
                if not recent or not older:
                    return None
                return float(np.mean(recent) - np.mean(older))

            return {
                "resting_hr_trend": trend_slope(hr_vals),
                "hrv_trend": trend_slope(hrv_vals),
                "sleep_score_trend": trend_slope(sleep_vals),
            }
        except Exception:
            return defaults

    @staticmethod
    def compute_weighted_feature_score(features: dict) -> Optional[float]:
        """Compute a weighted aggregate using rolling window weights.

        Combines 7d, 21d, and 42d volume features into a single
        weighted metric used by the projection engine.
        """
        d7 = features.get("rolling_distance_7d")
        d21 = features.get("rolling_distance_21d")
        d42 = features.get("rolling_distance_42d")

        if d7 is None or d21 is None or d42 is None:
            return None

        weekly_7d = d7 / 1
        weekly_21d = d21 / 3
        weekly_42d = d42 / 6

        weighted = (
            ROLLING_WINDOW_WEIGHTS["7d"] * weekly_7d
            + ROLLING_WINDOW_WEIGHTS["8_21d"] * weekly_21d
            + ROLLING_WINDOW_WEIGHTS["22_90d"] * weekly_42d
        )
        return float(weighted)
