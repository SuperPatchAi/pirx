"""LSTM inference adapter for phased projection serving.

Uses real PyTorch model loading (torch.load) and forward pass when trained
LSTM artifacts are available. Falls back to deterministic projection when
no valid artifact exists.
"""

from __future__ import annotations

import logging
from typing import Optional

import torch

from app.ml.lstm_model import LSTMTrainer, LSTM_FEATURE_NAMES
from app.ml.projection_engine import ProjectionState
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)


class LSTMInferenceAdapter:
    """Generate projection overrides from active LSTM artifacts using real torch inference."""

    def __init__(self):
        self.db = SupabaseService()
        self._cached_trainer: Optional[LSTMTrainer] = None
        self._cached_model_id: Optional[str] = None

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
        weight_bytes = artifact.get("weight_bytes")

        if weight_bytes and isinstance(weight_bytes, bytes):
            feature_sequence = self._build_feature_sequence(user_id, features)
            prediction = self._predict_with_torch(
                weight_bytes, feature_sequence, metadata,
                artifact_id=str(artifact.get("artifact_id", "")),
            )
            if prediction is not None:
                predicted = baseline_time_s - prediction
                predicted = max(60.0, min(predicted, baseline_time_s * 1.25))
                predicted = max(predicted, baseline_time_s * 0.75)

                if previous_state and previous_state.projected_time_seconds > 0:
                    predicted = (
                        0.6 * predicted
                        + 0.4 * previous_state.projected_time_seconds
                    )

                confidence = float(metadata.get("promotion_confidence", 0.65))
                confidence = max(0.0, min(confidence, 1.0))

                return {
                    "predicted_seconds": round(predicted, 2),
                    "confidence": confidence,
                    "model_id": model_id,
                    "artifact_id": artifact.get("artifact_id"),
                    "inference_method": "torch",
                }

        return self._heuristic_fallback(
            features, baseline_time_s, previous_state, metadata, model_id, artifact,
        )

    def _build_feature_sequence(self, user_id: str, current_features: dict) -> list[dict]:
        """Build temporal feature sequence for LSTM from recent feature snapshots."""
        try:
            snapshots = self.db.get_recent_feature_snapshots(user_id, limit=10)
            if snapshots:
                sequence = list(reversed(snapshots))
                sequence.append(current_features)
                return sequence
        except Exception:
            logger.debug("Could not fetch feature snapshots for LSTM sequence")
        return [current_features]

    def _predict_with_torch(
        self,
        weight_bytes: bytes,
        feature_sequence: list[dict],
        metadata: dict,
        artifact_id: str = "",
    ) -> Optional[float]:
        """Run real PyTorch LSTM inference."""
        try:
            cache_key = artifact_id or id(weight_bytes)
            if self._cached_trainer is None or self._cached_model_id != cache_key:
                hidden_dim = int(metadata.get("hidden_dim", 17))
                dropout = float(metadata.get("dropout", 0.5))
                trainer = LSTMTrainer(hidden_dim=hidden_dim, dropout=dropout)
                trainer.load_weights(weight_bytes, input_dim=len(LSTM_FEATURE_NAMES))
                self._cached_trainer = trainer
                self._cached_model_id = cache_key
                self._cached_at = __import__("time").time()

            if __import__("time").time() - getattr(self, "_cached_at", 0) > 3600:
                self._cached_trainer = None
                self._cached_model_id = None
                return None

            return self._cached_trainer.predict(feature_sequence)

        except Exception:
            logger.exception("Torch LSTM inference failed")
            return None

    def _heuristic_fallback(
        self,
        features: dict,
        baseline_time_s: float,
        previous_state: Optional[ProjectionState],
        metadata: dict,
        model_id: Optional[str],
        artifact: dict,
    ) -> Optional[dict]:
        """Bounded heuristic scoring when torch weights are unavailable."""
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
            "inference_method": "heuristic_fallback",
        }
