"""LSTM inference adapter for phased projection serving.

This adapter reads active model lifecycle records and their latest artifact
metadata, then produces a projection-time override candidate. The deterministic
projection path remains the safety rail when artifacts are unavailable.
"""

from __future__ import annotations

from typing import Optional

from app.ml.projection_engine import ProjectionState
from app.services.supabase_client import SupabaseService


class LSTMInferenceAdapter:
    """Generate projection overrides from active LSTM artifacts."""

    def __init__(self):
        self.db = SupabaseService()

    def predict_projection_time(
        self,
        user_id: str,
        event: str,
        features: dict,
        baseline_time_s: float,
        previous_state: Optional[ProjectionState] = None,
    ) -> Optional[dict]:
        active_model = self.db.get_active_model(user_id, event)
        if not active_model or active_model.get("model_family") != "lstm":
            return None

        model_id = active_model.get("model_id")
        artifact = self.db.get_latest_model_artifact(model_id) if model_id else None
        if not artifact:
            return None

        metadata = artifact.get("metadata") or {}
        # Lightweight, bounded scoring until full neural serving is enabled.
        adjustment = (
            -25.0 * float(features.get("rolling_distance_21d", 0) or 0) / 100000.0
            - 1.0 * float(features.get("threshold_density_min_week", 0) or 0)
            - 1.2 * float(features.get("speed_exposure_min_week", 0) or 0)
            + 8.0 * float(features.get("weekly_load_stddev", 0) or 0) / 10000.0
            + 20.0 * abs(float(features.get("acwr_4w", 1.0) or 1.0) - 1.0)
        )
        predicted = baseline_time_s + adjustment
        predicted = max(60.0, min(predicted, baseline_time_s * 1.25))
        predicted = max(predicted, baseline_time_s * 0.75)

        if previous_state and previous_state.projected_time_seconds > 0:
            predicted = 0.6 * predicted + 0.4 * previous_state.projected_time_seconds

        confidence = float(metadata.get("validation_score", 0.65))
        confidence = max(0.0, min(confidence, 1.0))

        return {
            "predicted_seconds": round(predicted, 2),
            "confidence": confidence,
            "model_id": model_id,
            "artifact_id": artifact.get("artifact_id"),
        }
