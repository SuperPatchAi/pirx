"""PIRX Projection Engine — computes projected race times and driver decomposition.

Core responsibilities:
1. Compute projected time from features + baseline
2. Decompose improvement into 5 structural drivers
3. Apply volatility dampening
4. Enforce driver sum constraint (drivers MUST sum to total improvement)
5. Produce immutable projection state for storage
"""
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


DRIVER_NAMES = [
    "aerobic_base",
    "threshold_density",
    "speed_exposure",
    "running_economy",
    "load_consistency",
]

ROLLING_WINDOW_WEIGHTS = {"7d": 0.45, "8_21d": 0.35, "22_90d": 0.20}

# Feature-to-driver mapping: which features primarily drive each structural driver
DRIVER_FEATURE_MAP = {
    "aerobic_base": [
        "rolling_distance_7d", "rolling_distance_21d", "rolling_distance_42d",
        "z1_pct", "z2_pct",
    ],
    "threshold_density": [
        "threshold_density_min_week", "z4_pct",
        "matched_hr_band_pace",
    ],
    "speed_exposure": [
        "speed_exposure_min_week", "z5_pct",
    ],
    "running_economy": [
        "hr_drift_sustained", "late_session_pace_decay",
        "matched_hr_band_pace",
    ],
    "load_consistency": [
        "weekly_load_stddev", "block_variance",
        "session_density_stability", "acwr_4w",
    ],
}

# Default weights for driver contribution (learned from data in production)
DEFAULT_DRIVER_WEIGHTS = {
    "aerobic_base": 0.30,
    "threshold_density": 0.25,
    "speed_exposure": 0.15,
    "running_economy": 0.15,
    "load_consistency": 0.15,
}


@dataclass
class ProjectionState:
    """Immutable projection state — one row per update, append-only."""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    event: str = "5000"
    projected_time_seconds: float = 0.0
    supported_range_low: float = 0.0
    supported_range_high: float = 0.0
    baseline_time_seconds: float = 0.0
    total_improvement_seconds: float = 0.0
    volatility: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DriverState:
    """Immutable driver state — one row per driver per update."""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    event: str = "5000"
    driver_name: str = ""
    contribution_seconds: float = 0.0
    score: float = 0.0  # 0-100 normalized score
    trend: str = "stable"  # "improving", "stable", "declining"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectionEngine:
    """Core projection computation engine."""

    def __init__(
        self,
        driver_weights: Optional[dict[str, float]] = None,
        alpha: float = 0.5,  # volatility dampening factor [0.3, 0.7]
    ):
        self.driver_weights = driver_weights or DEFAULT_DRIVER_WEIGHTS.copy()
        self.alpha = np.clip(alpha, 0.3, 0.7)

    def compute_projection(
        self,
        user_id: str,
        event: str,
        baseline_time_s: float,
        features: dict[str, Optional[float]],
        previous_state: Optional[ProjectionState] = None,
    ) -> tuple[ProjectionState, list[DriverState]]:
        """Compute a new projection from features and baseline.

        Args:
            user_id: User identifier
            event: Event distance key (e.g., "5000")
            baseline_time_s: Runner's baseline race time in seconds
            features: Feature dict from FeatureService
            previous_state: Previous ProjectionState for dampening

        Returns:
            (ProjectionState, list of 5 DriverStates)
        """
        # Step 1: Compute raw driver scores from features
        raw_scores = self._compute_driver_scores(features)

        # Step 2: Compute total improvement from driver scores
        total_improvement = self._compute_total_improvement(
            raw_scores, baseline_time_s
        )

        # Step 3: Decompose into driver contributions (MUST sum to total)
        driver_contributions = self._decompose_drivers(
            raw_scores, total_improvement
        )

        # Step 4: Compute raw projected time
        raw_projected = baseline_time_s - total_improvement

        # Step 5: Apply volatility dampening if previous state exists
        if previous_state and previous_state.projected_time_seconds > 0:
            projected = self._apply_dampening(
                raw_projected, previous_state.projected_time_seconds
            )
            volatility = abs(raw_projected - previous_state.projected_time_seconds)
        else:
            projected = raw_projected
            volatility = 0.0

        # Step 6: Compute supported range
        range_low, range_high = self._compute_range(projected, volatility, features)

        # Step 7: Build immutable states
        projection_state = ProjectionState(
            user_id=user_id,
            event=event,
            projected_time_seconds=round(projected, 2),
            supported_range_low=round(range_low, 2),
            supported_range_high=round(range_high, 2),
            baseline_time_seconds=baseline_time_s,
            total_improvement_seconds=round(total_improvement, 2),
            volatility=round(volatility, 2),
        )

        driver_states = self._build_driver_states(
            user_id, event, driver_contributions, raw_scores
        )

        return projection_state, driver_states

    def _compute_driver_scores(self, features: dict) -> dict[str, float]:
        """Compute 0-100 score for each driver from features."""
        scores = {}
        for driver, feature_names in DRIVER_FEATURE_MAP.items():
            values = []
            for f in feature_names:
                v = features.get(f)
                if v is not None:
                    values.append(v)

            if not values:
                scores[driver] = 50.0  # neutral score when no data
            else:
                raw = np.mean(values)
                scores[driver] = self._normalize_score(driver, raw)

        return scores

    def _normalize_score(self, driver: str, raw_value: float) -> float:
        """Normalize a raw feature aggregate to 0-100 scale.

        Uses driver-specific scaling. Scores above 50 = above average.
        """
        # Reference baselines for "average" runner (calibrated from population data)
        baselines = {
            "aerobic_base": 30000,      # 30km/week typical volume
            "threshold_density": 15,     # 15 min/week Z4
            "speed_exposure": 5,         # 5 min/week Z5
            "running_economy": 0.05,     # 5% drift typical
            "load_consistency": 5000,    # stddev of weekly load
        }

        baseline = baselines.get(driver, 1)
        if baseline == 0:
            return 50.0

        ratio = raw_value / baseline

        # For consistency, lower stddev = better (invert)
        if driver == "load_consistency":
            ratio = 2.0 - min(ratio, 2.0)
        # For efficiency, lower drift = better (invert)
        elif driver == "running_economy":
            ratio = 2.0 - min(ratio, 2.0)

        score = 50.0 * ratio
        return float(np.clip(score, 0, 100))

    def _compute_total_improvement(
        self, scores: dict[str, float], baseline_time_s: float
    ) -> float:
        """Compute total improvement in seconds from driver scores.

        Each driver contributes proportionally to its weight and score.
        Maximum possible improvement is capped at 15% of baseline.
        """
        weighted_sum = sum(
            scores[d] * self.driver_weights[d] for d in DRIVER_NAMES
        )

        # Scale: 50 = no improvement, 100 = max improvement
        # Max improvement = 15% of baseline time
        max_improvement = baseline_time_s * 0.15
        improvement_factor = (weighted_sum - 50) / 50  # range: -1 to +1

        total = improvement_factor * max_improvement
        return float(total)

    def _decompose_drivers(
        self, scores: dict[str, float], total_improvement: float
    ) -> dict[str, float]:
        """Decompose total improvement into per-driver contributions.

        CRITICAL: contributions MUST sum exactly to total_improvement.
        """
        weighted_scores = {
            d: scores[d] * self.driver_weights[d] for d in DRIVER_NAMES
        }

        total_weighted = sum(weighted_scores.values())

        if total_weighted == 0 or total_improvement == 0:
            return {d: 0.0 for d in DRIVER_NAMES}

        contributions = {}
        running_total = 0.0

        for i, driver in enumerate(DRIVER_NAMES):
            if i == len(DRIVER_NAMES) - 1:
                # Last driver gets the remainder to ensure exact sum
                contributions[driver] = round(total_improvement - running_total, 2)
            else:
                fraction = weighted_scores[driver] / total_weighted
                contribution = round(total_improvement * fraction, 2)
                contributions[driver] = contribution
                running_total += contribution

        return contributions

    def _apply_dampening(self, raw: float, previous: float) -> float:
        """Apply volatility dampening: smoothed = α × new + (1 - α) × previous."""
        return self.alpha * raw + (1 - self.alpha) * previous

    def _compute_range(
        self, projected: float, volatility: float, features: dict
    ) -> tuple[float, float]:
        """Compute Supported Range around projection.

        Width increases with:
        - Higher volatility
        - Fewer available features (more uncertainty)
        - Higher ACWR (training load instability)
        """
        # Base range: 1.5% of projected time
        base_pct = 0.015

        # Volatility component
        vol_pct = min(volatility / projected, 0.05) if projected > 0 else 0

        # Data quality component
        available_features = sum(1 for v in features.values() if v is not None)
        total_features = max(len(features), 1)
        data_quality = available_features / total_features
        uncertainty_pct = (1 - data_quality) * 0.02

        # ACWR instability component
        acwr = features.get("acwr_4w")
        acwr_pct = 0.0
        if acwr is not None:
            if acwr > 1.5 or acwr < 0.6:
                acwr_pct = 0.01

        total_pct = base_pct + vol_pct + uncertainty_pct + acwr_pct

        return (
            projected * (1 - total_pct),
            projected * (1 + total_pct),
        )

    def _build_driver_states(
        self, user_id: str, event: str,
        contributions: dict[str, float], scores: dict[str, float],
    ) -> list[DriverState]:
        """Build immutable DriverState objects."""
        states = []
        for driver in DRIVER_NAMES:
            trend = "stable"
            score = scores.get(driver, 50.0)
            if score > 60:
                trend = "improving"
            elif score < 40:
                trend = "declining"

            states.append(DriverState(
                user_id=user_id,
                event=event,
                driver_name=driver,
                contribution_seconds=contributions.get(driver, 0.0),
                score=round(score, 1),
                trend=trend,
            ))
        return states

    @staticmethod
    def check_structural_shift(
        new_state: ProjectionState,
        previous_state: Optional[ProjectionState],
        threshold_seconds: float = 2.0,
    ) -> bool:
        """Check if the projection shifted enough to warrant an update.

        Returns True if delta >= threshold (default 2 seconds).
        """
        if previous_state is None:
            return True

        delta = abs(new_state.projected_time_seconds - previous_state.projected_time_seconds)
        return delta >= threshold_seconds

    @staticmethod
    def validate_driver_sum(
        driver_states: list[DriverState],
        total_improvement: float,
        tolerance: float = 0.01,
    ) -> bool:
        """Validate that driver contributions sum to total improvement."""
        driver_sum = sum(d.contribution_seconds for d in driver_states)
        return abs(driver_sum - total_improvement) <= tolerance
