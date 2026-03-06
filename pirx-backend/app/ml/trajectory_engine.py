"""Two-week trajectory projection engine.

Models forward scenarios by simulating feature changes over 14 days
and running them through the ProjectionEngine.

Three scenarios:
1. Maintain — continue current training pattern (features unchanged)
2. Push — increase threshold/speed work (+15% intensity features)
3. Ease off — reduce volume (-20% volume features, improved consistency)
"""
from typing import Optional
from dataclasses import dataclass
from app.ml.projection_engine import ProjectionEngine, ProjectionState


@dataclass
class TrajectoryScenario:
    label: str
    description: str
    projected_time_seconds: float
    delta_from_current: float
    confidence: float  # 0-1, lower for more aggressive scenarios


SCENARIO_CONFIGS = {
    "maintain": {
        "label": "Maintain",
        "description": "Continue current training pattern",
        "volume_factor": 1.0,
        "intensity_factor": 1.0,
        "consistency_factor": 1.0,
        "confidence": 0.85,
    },
    "push": {
        "label": "Push",
        "description": "Increase threshold & speed work",
        "volume_factor": 1.05,
        "intensity_factor": 1.15,
        "consistency_factor": 0.95,
        "confidence": 0.65,
    },
    "ease_off": {
        "label": "Ease Off",
        "description": "Reduce volume, maintain quality",
        "volume_factor": 0.80,
        "intensity_factor": 0.90,
        "consistency_factor": 1.10,
        "confidence": 0.75,
    },
}


VOLUME_FEATURES = [
    "rolling_distance_7d", "rolling_distance_21d", "rolling_distance_42d",
    "rolling_distance_90d",
]

INTENSITY_FEATURES = [
    "threshold_density_min_week", "speed_exposure_min_week",
    "z4_pct", "z5_pct",
]

CONSISTENCY_FEATURES = [
    "weekly_load_stddev", "block_variance", "session_density_stability",
]


class TrajectoryEngine:
    """Computes forward trajectory scenarios."""

    def __init__(self, engine: Optional[ProjectionEngine] = None):
        self.engine = engine or ProjectionEngine()

    def compute_trajectories(
        self,
        user_id: str,
        event: str,
        baseline_time_s: float,
        current_features: dict[str, Optional[float]],
        current_state: Optional[ProjectionState] = None,
    ) -> list[TrajectoryScenario]:
        """Compute all three trajectory scenarios.

        Args:
            user_id: User identifier
            event: Event distance key (e.g., "5000")
            baseline_time_s: Runner's baseline race time in seconds
            current_features: Current feature values
            current_state: Current projection state (for delta calculation)

        Returns:
            List of 3 TrajectoryScenario objects
        """
        current_projected = (
            current_state.projected_time_seconds
            if current_state and current_state.projected_time_seconds > 0
            else baseline_time_s
        )

        scenarios = []
        for key in ["maintain", "push", "ease_off"]:
            config = SCENARIO_CONFIGS[key]
            modified_features = self._apply_scenario(
                current_features, config
            )

            proj_state, _ = self.engine.compute_projection(
                user_id=user_id,
                event=event,
                baseline_time_s=baseline_time_s,
                features=modified_features,
                previous_state=current_state,
            )

            delta = current_projected - proj_state.projected_time_seconds

            scenarios.append(TrajectoryScenario(
                label=config["label"],
                description=config["description"],
                projected_time_seconds=round(proj_state.projected_time_seconds, 1),
                delta_from_current=round(delta, 1),
                confidence=config["confidence"],
            ))

        return scenarios

    def _apply_scenario(
        self,
        features: dict[str, Optional[float]],
        config: dict,
    ) -> dict[str, Optional[float]]:
        """Apply scenario modifiers to features."""
        modified = dict(features)

        for feat in VOLUME_FEATURES:
            val = modified.get(feat)
            if val is not None:
                modified[feat] = val * config["volume_factor"]

        for feat in INTENSITY_FEATURES:
            val = modified.get(feat)
            if val is not None:
                modified[feat] = val * config["intensity_factor"]

        for feat in CONSISTENCY_FEATURES:
            val = modified.get(feat)
            if val is not None:
                # For consistency features, lower = better, so invert the factor
                modified[feat] = val / config["consistency_factor"]

        return modified
