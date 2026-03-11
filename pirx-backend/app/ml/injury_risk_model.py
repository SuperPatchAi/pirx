"""Random-Forest injury risk model (probability output).

This model provides a bounded injury-risk probability used as an additive
signal in readiness explanations. It does not write or alter projection state.
"""

from functools import lru_cache
import numpy as np
from sklearn.ensemble import RandomForestRegressor


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

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_model() -> RandomForestRegressor:
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
        return model

    @classmethod
    def predict_probability(cls, features: dict, sleep_score: float | None = None) -> float:
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
        prob = float(cls._get_model().predict(x)[0])
        return max(0.0, min(1.0, prob))
