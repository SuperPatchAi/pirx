"""Random-Forest injury risk model (probability output).

This model provides a bounded injury-risk probability used as an additive
signal in readiness explanations. It does not write or alter projection state.

Two tiers:
  1. TrainableInjuryRiskModel -- retrained on real accumulated user data when
     proxy injury signals exist (extended rest after high ACWR, performance drops).
  2. InjuryRiskModel -- synthetic-data baseline, used as fallback when real data
     is insufficient.
"""

import logging
import threading
from functools import lru_cache
from io import BytesIO
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MIN_INJURY_SIGNALS = 30


class InjurySignalExtractor:
    """Extracts proxy injury labels from user activity history.

    Proxy signals (per the plan):
      - Extended rest >14 days after high ACWR (>=1.4)
      - Performance drop >10% in a 4-week window
    """

    @staticmethod
    def extract_signals(
        activities: list[dict],
        feature_snapshots: list[dict],
    ) -> list[dict]:
        """Build labeled feature/target pairs from proxy injury signals.

        Returns list of {features: dict, label: float} where label ∈ [0, 1].
        """
        if not activities or not feature_snapshots:
            return []

        snap_by_date: dict[str, dict] = {}
        for snap in feature_snapshots:
            d = snap.get("date") or snap.get("snapshot_date")
            if d:
                snap_by_date[str(d)[:10]] = snap

        sorted_acts = sorted(activities, key=lambda a: a.get("start_time", ""))

        signals: list[dict] = []
        for i, act in enumerate(sorted_acts):
            date_str = str(act.get("start_time", ""))[:10]
            snap = snap_by_date.get(date_str)
            if snap is None:
                continue

            features = {name: snap.get(name) for name in InjuryRiskModel.FEATURE_ORDER}
            label = 0.0

            acwr = snap.get("acwr_4w")
            if acwr is not None and acwr >= 1.4 and i + 1 < len(sorted_acts):
                next_date = str(sorted_acts[i + 1].get("start_time", ""))[:10]
                try:
                    from datetime import date as dt_date
                    curr = dt_date.fromisoformat(date_str)
                    nxt = dt_date.fromisoformat(next_date)
                    gap_days = (nxt - curr).days
                    if gap_days > 14:
                        label = min(1.0, gap_days / 30.0)
                except (ValueError, TypeError):
                    pass

            pace = act.get("avg_pace_min_km") or act.get("pace")
            if pace and i >= 4:
                prev_paces = []
                for j in range(max(0, i - 4), i):
                    pp = sorted_acts[j].get("avg_pace_min_km") or sorted_acts[j].get("pace")
                    if pp and pp > 0:
                        prev_paces.append(pp)
                if prev_paces:
                    avg_prev = np.mean(prev_paces)
                    if avg_prev > 0 and (pace - avg_prev) / avg_prev > 0.10:
                        label = max(label, 0.7)

            signals.append({"features": features, "label": label})

        return signals


class TrainableInjuryRiskModel:
    """RandomForestRegressor retrained on real accumulated user data."""

    def __init__(self):
        self.model = None
        self.is_trained = False
        self.feature_names = list(InjuryRiskModel.FEATURE_ORDER)

    FEATURE_DEFAULTS = {
        "acwr_4w": 1.0, "acwr_6w": 1.0, "acwr_8w": 1.0,
        "weekly_load_stddev": 5000.0, "session_density_stability": 1.0,
        "hrv_trend": 0.0, "resting_hr_trend": 0.0, "sleep_score": 75.0,
    }

    def _features_to_array(self, feature_rows: list[dict], sleep_score: float | None = None) -> np.ndarray:
        """Convert feature dicts using consistent defaults for train and inference."""
        rows = []
        for f in feature_rows:
            row = []
            for name in self.feature_names:
                v = f.get(name)
                if name == "sleep_score" and v is None and sleep_score is not None:
                    v = sleep_score
                if v is None:
                    v = self.FEATURE_DEFAULTS.get(name, 0.0)
                row.append(float(v))
            rows.append(row)
        return np.array(rows, dtype=np.float64)

    def train(self, signals: list[dict]) -> dict:
        """Train on extracted injury signals.

        Args:
            signals: list of {features: dict, label: float} from InjurySignalExtractor.
        """
        from sklearn.ensemble import RandomForestRegressor

        if len(signals) < MIN_INJURY_SIGNALS:
            return {"status": "insufficient_data", "samples": len(signals)}

        feature_rows = [sig["features"] for sig in signals]
        y_vals = [float(sig["label"]) for sig in signals]

        X = self._features_to_array(feature_rows)
        y = np.array(y_vals, dtype=np.float64)

        self.model = RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            max_depth=8,
            min_samples_leaf=4,
        )
        self.model.fit(X, y)
        self.is_trained = True

        train_score = float(self.model.score(X, y))
        return {
            "status": "trained",
            "samples": len(signals),
            "r2_score": round(train_score, 3),
        }

    def predict_probability(self, features: dict, sleep_score: float | None = None) -> Optional[float]:
        if not self.is_trained or self.model is None:
            return None

        x = self._features_to_array([features], sleep_score=sleep_score)
        raw = float(self.model.predict(x)[0])
        return max(0.0, min(1.0, raw))

    def serialize(self) -> bytes:
        if not self.is_trained or self.model is None:
            raise ValueError("Cannot serialize untrained model")
        buf = BytesIO()
        joblib.dump(self.model, buf)
        return buf.getvalue()

    @classmethod
    def deserialize(cls, data: bytes) -> "TrainableInjuryRiskModel":
        instance = cls()
        buf = BytesIO(data)
        instance.model = joblib.load(buf)
        instance.is_trained = True
        return instance


class InjuryRiskModel:
    """Random-Forest-based injury risk estimator."""

    FEATURE_ORDER = [
        "acwr_4w",
        "acwr_6w",
        "acwr_8w",
        "weekly_load_stddev",
        "session_density_stability",
        "hrv_trend",
        "resting_hr_trend",
        "sleep_score",
    ]
    LOW_RISK_MAX = 0.35
    MODERATE_RISK_MAX = 0.6
    _model_lock = threading.Lock()
    _cached_model = None

    @classmethod
    def _get_model(cls):
        if cls._cached_model is not None:
            return cls._cached_model
        with cls._model_lock:
            if cls._cached_model is not None:
                return cls._cached_model
            from sklearn.ensemble import RandomForestRegressor

            rng = np.random.default_rng(42)
            n = 1600

            acwr4 = rng.uniform(0.4, 2.0, n)
            acwr6 = np.clip(acwr4 + rng.normal(0, 0.12, n), 0.4, 2.0)
            acwr8 = np.clip(acwr4 + rng.normal(0, 0.15, n), 0.4, 2.0)
            load_std = rng.uniform(1000, 14000, n)
            density = rng.uniform(0.2, 2.5, n)
            hrv_trend = rng.normal(0, 2.0, n)
            rhr_trend = rng.normal(0, 2.0, n)
            sleep = rng.uniform(30, 95, n)

            raw_risk = (
                0.45 * np.clip((acwr4 - 1.1) / 0.7, 0, 1)
                + 0.18 * np.clip((load_std - 5000) / 8000, 0, 1)
                + 0.12 * np.clip((density - 1.0) / 1.5, 0, 1)
                + 0.10 * np.clip((-hrv_trend) / 4.0, 0, 1)
                + 0.08 * np.clip(rhr_trend / 4.0, 0, 1)
                + 0.07 * np.clip((65 - sleep) / 35, 0, 1)
            )
            y = np.clip(raw_risk + rng.normal(0, 0.03, n), 0, 1)

            X = np.column_stack([acwr4, acwr6, acwr8, load_std, density, hrv_trend, rhr_trend, sleep])
            model = RandomForestRegressor(
                n_estimators=200,
                random_state=42,
                max_depth=8,
                min_samples_leaf=4,
            )
            model.fit(X, y)
            cls._cached_model = model
            return model

    @classmethod
    def predict_probability(
        cls,
        features: dict,
        sleep_score: float | None = None,
        trained_model: Optional["TrainableInjuryRiskModel"] = None,
    ) -> float:
        if trained_model is not None and trained_model.is_trained:
            ml_prob = trained_model.predict_probability(features, sleep_score)
            if ml_prob is not None:
                return ml_prob

        def g(name: str, default: float) -> float:
            v = features.get(name)
            return float(v) if v is not None else default

        x = np.array(
            [[
                g("acwr_4w", 1.0),
                g("acwr_6w", 1.0),
                g("acwr_8w", 1.0),
                g("weekly_load_stddev", 5000.0),
                g("session_density_stability", 1.0),
                g("hrv_trend", 0.0),
                g("resting_hr_trend", 0.0),
                float(sleep_score) if sleep_score is not None else 75.0,
            ]]
        )
        raw_prob = float(cls._get_model().predict(x)[0])
        calibrated = cls._calibrate_probability(raw_prob)
        return max(0.0, min(1.0, calibrated))

    @classmethod
    def get_risk_band(cls, risk_probability: float) -> str:
        if risk_probability < cls.LOW_RISK_MAX:
            return "low"
        if risk_probability < cls.MODERATE_RISK_MAX:
            return "moderate"
        return "high"

    @staticmethod
    def _calibrate_probability(raw_prob: float) -> float:
        p = max(0.0, min(1.0, raw_prob))
        if p < 0.2:
            return p * 0.9
        if p < 0.7:
            return 0.18 + 1.0 * (p - 0.2)
        return min(1.0, 0.68 + 0.9 * (p - 0.7))
