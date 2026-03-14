"""Gradient Boosting projection model for trained per-user race time prediction.

Replaces the hardcoded weight-based projection when sufficient training data
exists (>= 30 activities with performance anchors). Falls back gracefully to
heuristic projection when no trained model is available.

Uses sklearn GradientBoostingRegressor with Huber loss for GPS-outlier
robustness, cross-validated on user data with exponential recency weighting.
"""
import logging
from io import BytesIO
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_validate

logger = logging.getLogger(__name__)

GB_FEATURE_NAMES = [
    "rolling_distance_7d",
    "rolling_distance_21d",
    "rolling_distance_42d",
    "rolling_distance_90d",
    "sessions_per_week",
    "long_run_count",
    "z1_pct",
    "z2_pct",
    "z4_pct",
    "z5_pct",
    "threshold_density_min_week",
    "speed_exposure_min_week",
    "matched_hr_band_pace",
    "hr_drift_sustained",
    "late_session_pace_decay",
    "weekly_load_stddev",
    "acwr_4w",
]

MIN_TRAINING_SAMPLES = 30


class GBProjectionModel:
    """Trained Gradient Boosting model for per-user projection."""

    def __init__(self):
        self.model: Optional[GradientBoostingRegressor] = None
        self.feature_names = list(GB_FEATURE_NAMES)
        self.is_trained = False

    def train(
        self,
        feature_rows: list[dict],
        targets: list[float],
        sample_weights: Optional[list[float]] = None,
    ) -> dict:
        """Train the GB model on user feature snapshots paired with performance deltas.

        Args:
            feature_rows: Feature dicts (one per training sample).
            targets: Performance delta targets (seconds of improvement from baseline).
            sample_weights: Optional per-sample weights; defaults to exponential
                recency decay (0.45/0.35/0.20 weighting spirit).

        Returns:
            Dict with training metrics (MAE, CV scores, feature importances).
        """
        if len(feature_rows) < MIN_TRAINING_SAMPLES:
            return {"status": "insufficient_data", "samples": len(feature_rows)}

        X = self._features_to_array(feature_rows)
        y = np.array(targets, dtype=np.float64)

        if sample_weights is None:
            n = len(targets)
            decay = np.array([0.98 ** (n - 1 - i) for i in range(n)])
            sample_weights_arr = decay / decay.sum() * n
        else:
            sample_weights_arr = np.array(sample_weights, dtype=np.float64)

        self.model = GradientBoostingRegressor(
            loss="huber",
            learning_rate=0.008,
            max_depth=4,
            n_estimators=200,
            subsample=0.8,
            min_samples_leaf=5,
            random_state=42,
        )

        n_splits = min(5, max(2, len(y)))
        cv_result = cross_validate(
            self.model, X, y,
            cv=n_splits,
            scoring="neg_mean_absolute_error",
            params={"sample_weight": sample_weights_arr},
        )
        cv_scores = cv_result["test_score"]

        self.model.fit(X, y, sample_weight=sample_weights_arr)
        self.is_trained = True

        train_predictions = self.model.predict(X)
        train_mae = float(np.mean(np.abs(train_predictions - y)))

        return {
            "status": "trained",
            "samples": len(targets),
            "train_mae": round(train_mae, 2),
            "cv_mae": round(float(-cv_scores.mean()), 2),
            "cv_std": round(float(cv_scores.std()), 2),
            "feature_importances": dict(zip(
                self.feature_names,
                [round(float(v), 4) for v in self.model.feature_importances_],
            )),
        }

    def predict(self, features: dict) -> Optional[float]:
        """Predict improvement seconds from current features.

        Returns None if model is not trained.
        """
        if not self.is_trained or self.model is None:
            return None

        X = self._features_to_array([features])
        return float(self.model.predict(X)[0])

    def validate(self, feature_rows: list[dict], targets: list[float]) -> dict:
        """Validate model on held-out data with Bland-Altman metrics."""
        if not self.is_trained or self.model is None:
            return {"status": "not_trained"}

        X = self._features_to_array(feature_rows)
        y = np.array(targets, dtype=np.float64)
        predictions = self.model.predict(X)

        errors = predictions - y
        mae = float(np.mean(np.abs(errors)))
        bias = float(np.mean(errors))
        std_err = float(np.std(errors))
        bland_altman_lower = bias - 1.96 * std_err
        bland_altman_upper = bias + 1.96 * std_err

        return {
            "status": "validated",
            "samples": len(targets),
            "mae": round(mae, 2),
            "bias": round(bias, 2),
            "bland_altman_lower": round(bland_altman_lower, 2),
            "bland_altman_upper": round(bland_altman_upper, 2),
        }

    def serialize(self) -> bytes:
        """Serialize trained model to bytes for artifact storage."""
        if not self.is_trained or self.model is None:
            raise ValueError("Cannot serialize untrained model")
        buf = BytesIO()
        joblib.dump(self.model, buf)
        return buf.getvalue()

    @classmethod
    def deserialize(cls, model_bytes: bytes) -> "GBProjectionModel":
        """Restore a trained model from serialized bytes."""
        instance = cls()
        buf = BytesIO(model_bytes)
        instance.model = joblib.load(buf)
        instance.is_trained = True
        return instance

    def _features_to_array(self, feature_rows: list[dict]) -> np.ndarray:
        """Convert feature dicts to numpy array with consistent column order."""
        rows = []
        for features in feature_rows:
            row = []
            for name in self.feature_names:
                v = features.get(name)
                if v is None:
                    row.append(0.0)
                else:
                    f = float(v)
                    row.append(0.0 if f != f else f)
            rows.append(row)
        return np.array(rows, dtype=np.float64)
