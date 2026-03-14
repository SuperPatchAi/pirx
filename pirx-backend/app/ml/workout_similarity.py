"""DTW-based workout and training block similarity engine.

Uses Dynamic Time Warping from dtaidistance to compare pace profiles
between workouts and training blocks, enabling history-based trajectory
prediction instead of fixed multipliers.
"""
import logging
from typing import Optional

import numpy as np
from dtaidistance import dtw

logger = logging.getLogger(__name__)


class WorkoutSimilarity:
    """Compares workouts and training blocks using Dynamic Time Warping."""

    @staticmethod
    def pace_profile_distance(
        profile_a: list[float],
        profile_b: list[float],
    ) -> float:
        """Compute DTW distance between two pace profiles.

        Args:
            profile_a: Pace values (sec/km) per segment for workout A.
            profile_b: Pace values (sec/km) per segment for workout B.

        Returns:
            DTW distance (lower = more similar).
        """
        if not profile_a or not profile_b:
            return float("inf")

        a = np.array(profile_a, dtype=np.float64)
        b = np.array(profile_b, dtype=np.float64)

        return float(dtw.distance(a, b))

    @staticmethod
    def block_fingerprint(activities: list[dict]) -> np.ndarray:
        """Create a feature fingerprint for a training block.

        Extracts per-activity summary stats and returns a 2D array
        suitable for DTW comparison between blocks.

        Args:
            activities: List of activity dicts within a block (e.g. 14 days).

        Returns:
            (n_activities, 4) array: [distance_km, duration_min, avg_pace, avg_hr]
        """
        if not activities:
            return np.zeros((0, 4), dtype=np.float64)

        rows = []
        for act in activities:
            dist_km = float(act.get("distance_meters", 0) or 0) / 1000.0
            dur_min = float(act.get("duration_seconds", 0) or 0) / 60.0
            avg_pace = float(act.get("avg_pace_sec_per_km", 0) or 0)
            avg_hr = float(act.get("avg_hr", 0) or 0)
            rows.append([dist_km, dur_min, avg_pace, avg_hr])

        return np.array(rows, dtype=np.float64)

    @staticmethod
    def block_distance(block_a: np.ndarray, block_b: np.ndarray) -> float:
        """Compute DTW distance between two training block fingerprints.

        Each block is a 2D array (n_activities, n_features). Features are
        z-score normalized per column before DTW to avoid scale bias.
        DTW is applied independently per feature column and averaged.
        """
        if block_a.shape[0] == 0 or block_b.shape[0] == 0:
            return float("inf")

        n_features = min(block_a.shape[1], block_b.shape[1])
        distances = []
        for col in range(n_features):
            a_col = block_a[:, col].astype(np.float64)
            b_col = block_b[:, col].astype(np.float64)
            combined = np.concatenate([a_col, b_col])
            std = float(np.std(combined))
            if std > 1e-10:
                mean = float(np.mean(combined))
                a_col = (a_col - mean) / std
                b_col = (b_col - mean) / std
            d = dtw.distance(a_col, b_col)
            distances.append(d)

        return float(np.mean(distances)) if distances else float("inf")

    @staticmethod
    def find_similar_blocks(
        current_block: np.ndarray,
        historical_blocks: list[np.ndarray],
        top_k: int = 3,
    ) -> list[tuple[int, float]]:
        """Find the top-k most similar historical blocks to the current block.

        Args:
            current_block: Fingerprint of current 2-week block.
            historical_blocks: List of historical block fingerprints.
            top_k: Number of similar blocks to return.

        Returns:
            List of (block_index, distance) tuples, sorted by distance ascending.
        """
        if not historical_blocks:
            return []

        scored = []
        for i, hist_block in enumerate(historical_blocks):
            dist = WorkoutSimilarity.block_distance(current_block, hist_block)
            scored.append((i, dist))

        scored.sort(key=lambda x: x[1])
        return scored[:top_k]

    @staticmethod
    def predict_from_similar_blocks(
        similar_indices: list[tuple[int, float]],
        outcome_blocks: list[Optional[dict]],
    ) -> dict:
        """Predict trajectory from outcomes that followed similar historical blocks.

        Args:
            similar_indices: (block_index, distance) from find_similar_blocks.
            outcome_blocks: Performance outcomes for the 2 weeks AFTER each
                historical block. Dict with 'improvement_seconds' key.

        Returns:
            Trajectory prediction with expected/optimistic/conservative scenarios.
        """
        improvements = []
        for idx, dist in similar_indices:
            if idx < len(outcome_blocks) and outcome_blocks[idx] is not None:
                imp = outcome_blocks[idx].get("improvement_seconds", 0.0)
                improvements.append(float(imp))

        if not improvements:
            return {
                "expected": 0.0,
                "optimistic": 0.0,
                "conservative": 0.0,
                "confidence": 0.0,
                "similar_blocks_used": 0,
            }

        arr = np.array(improvements)
        return {
            "expected": round(float(np.mean(arr)), 2),
            "optimistic": round(float(np.percentile(arr, 75)), 2),
            "conservative": round(float(np.percentile(arr, 25)), 2),
            "confidence": round(min(1.0, len(improvements) / 5.0), 2),
            "similar_blocks_used": len(improvements),
        }
