"""Two-week trajectory projection engine with DTW-based historical matching.

When sufficient training history exists, uses Dynamic Time Warping to find
similar past training blocks and predicts trajectory from their outcomes.
Falls back to fixed-multiplier scenarios when history is insufficient.
"""
import logging
from typing import Optional
from dataclasses import dataclass

import numpy as np

from app.ml.projection_engine import ProjectionEngine, ProjectionState
from app.ml.workout_similarity import WorkoutSimilarity

logger = logging.getLogger(__name__)


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

MIN_BLOCKS_FOR_DTW = 4


class TrajectoryEngine:
    """Computes forward trajectory scenarios.

    Tries DTW-based historical matching first, falls back to
    fixed-multiplier heuristic when insufficient history.
    """

    def __init__(self, engine: Optional[ProjectionEngine] = None):
        self.engine = engine or ProjectionEngine()

    def compute_trajectories(
        self,
        user_id: str,
        event: str,
        baseline_time_s: float,
        current_features: dict[str, Optional[float]],
        current_state: Optional[ProjectionState] = None,
        activity_history: Optional[list[dict]] = None,
        projection_history: Optional[list[dict]] = None,
    ) -> list[TrajectoryScenario]:
        """Compute trajectory scenarios.

        Tries DTW-based matching if activity_history is provided and sufficient.
        Falls back to heuristic multiplier scenarios otherwise.
        """
        current_projected = (
            current_state.projected_time_seconds
            if current_state and current_state.projected_time_seconds > 0
            else baseline_time_s
        )

        if activity_history and projection_history:
            dtw_result = self._try_dtw_trajectory(
                activity_history, projection_history, current_projected,
            )
            if dtw_result is not None:
                return dtw_result

        return self._heuristic_trajectories(
            user_id, event, baseline_time_s,
            current_features, current_state, current_projected,
        )

    def _try_dtw_trajectory(
        self,
        activity_history: list[dict],
        projection_history: list[dict],
        current_projected: float,
    ) -> Optional[list[TrajectoryScenario]]:
        """Attempt DTW-based trajectory from historical block matching."""
        try:
            blocks, outcomes = self._build_block_pairs(
                activity_history, projection_history,
            )
            if len(blocks) < MIN_BLOCKS_FOR_DTW:
                return None

            current_block = blocks[-1]
            historical_blocks = blocks[:-1]
            historical_outcomes = outcomes[:-1]

            similar = WorkoutSimilarity.find_similar_blocks(
                current_block, historical_blocks, top_k=3,
            )
            if not similar:
                return None

            prediction = WorkoutSimilarity.predict_from_similar_blocks(
                similar, historical_outcomes,
            )
            if prediction["similar_blocks_used"] == 0:
                return None

            return [
                TrajectoryScenario(
                    label="Maintain",
                    description="Based on similar past training blocks",
                    projected_time_seconds=round(
                        current_projected - prediction["expected"], 1,
                    ),
                    delta_from_current=round(prediction["expected"], 1),
                    confidence=prediction["confidence"],
                ),
                TrajectoryScenario(
                    label="Push",
                    description="Optimistic outcome from similar blocks",
                    projected_time_seconds=round(
                        current_projected - prediction["optimistic"], 1,
                    ),
                    delta_from_current=round(prediction["optimistic"], 1),
                    confidence=round(prediction["confidence"] * 0.75, 2),
                ),
                TrajectoryScenario(
                    label="Ease Off",
                    description="Conservative outcome from similar blocks",
                    projected_time_seconds=round(
                        current_projected - prediction["conservative"], 1,
                    ),
                    delta_from_current=round(prediction["conservative"], 1),
                    confidence=round(prediction["confidence"] * 0.9, 2),
                ),
            ]
        except Exception:
            logger.exception("DTW trajectory failed, falling back to heuristic")
            return None

    def _build_block_pairs(
        self,
        activity_history: list[dict],
        projection_history: list[dict],
    ) -> tuple[list[np.ndarray], list[Optional[dict]]]:
        """Split activity history into 14-calendar-day blocks paired with outcome data."""
        from datetime import datetime, timedelta

        if not activity_history:
            return [], []

        sorted_acts = sorted(
            activity_history,
            key=lambda a: a.get("start_time", ""),
        )

        def _parse_date(ts):
            if isinstance(ts, datetime):
                return ts
            try:
                return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        first_date = _parse_date(sorted_acts[0].get("start_time"))
        last_date = _parse_date(sorted_acts[-1].get("start_time"))
        if not first_date or not last_date:
            return [], []

        block_days = 14
        blocks = []
        outcomes = []
        block_start = first_date

        while block_start + timedelta(days=block_days) <= last_date + timedelta(days=1):
            block_end = block_start + timedelta(days=block_days)
            block_acts = [
                a for a in sorted_acts
                if block_start <= (_parse_date(a.get("start_time")) or block_start) < block_end
            ]
            if block_acts:
                fingerprint = WorkoutSimilarity.block_fingerprint(block_acts)
                blocks.append(fingerprint)

                next_block_end = block_end + timedelta(days=block_days)
                improvement = self._estimate_block_improvement(
                    projection_history,
                    block_start.isoformat(),
                    next_block_end.isoformat(),
                )
                outcomes.append({"improvement_seconds": improvement} if improvement != 0.0 else None)
            block_start = block_end

        return blocks, outcomes

    @staticmethod
    def _estimate_block_improvement(
        projection_history: list[dict],
        block_start_date: str,
        block_end_date: str,
    ) -> float:
        """Estimate improvement across a block from projection history by matching dates."""
        if not projection_history or len(projection_history) < 2:
            return 0.0

        sorted_projs = sorted(
            projection_history,
            key=lambda p: p.get("computed_at", p.get("created_at", "")),
        )

        start_proj = None
        end_proj = None
        for p in sorted_projs:
            ts = p.get("computed_at", p.get("created_at", ""))
            if ts >= block_start_date and start_proj is None:
                start_proj = p.get("projected_time_seconds", 0)
            if ts >= block_end_date:
                end_proj = p.get("projected_time_seconds", 0)
                break

        if start_proj and end_proj and start_proj > 0 and end_proj > 0:
            return float(start_proj - end_proj)
        return 0.0

    def _heuristic_trajectories(
        self,
        user_id: str,
        event: str,
        baseline_time_s: float,
        current_features: dict[str, Optional[float]],
        current_state: Optional[ProjectionState],
        current_projected: float,
    ) -> list[TrajectoryScenario]:
        """Heuristic fixed-multiplier trajectories (original fallback)."""
        scenarios = []
        for key in ["maintain", "push", "ease_off"]:
            config = SCENARIO_CONFIGS[key]
            modified_features = self._apply_scenario(current_features, config)

            try:
                proj_state, _ = self.engine.compute_projection(
                    user_id=user_id,
                    event=event,
                    baseline_time_s=baseline_time_s,
                    features=modified_features,
                    previous_state=current_state,
                )
                projected_time = proj_state.projected_time_seconds
            except Exception:
                logger.exception("Projection failed for scenario %s", key)
                projected_time = current_projected

            delta = current_projected - projected_time

            scenarios.append(TrajectoryScenario(
                label=config["label"],
                description=config["description"],
                projected_time_seconds=round(projected_time, 1),
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
                modified[feat] = val / config["consistency_factor"]

        return modified
