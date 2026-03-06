"""Event Readiness scoring engine.

Readiness is independent from projection — it indicates how prepared
a runner is to race TODAY, not their structural fitness level.

Score 0-100:
  90-100: Peak readiness (race day)
  70-89:  Good readiness (solid training block)
  50-69:  Moderate (building phase, minor fatigue)
  30-49:  Low (heavy load, recovery needed)
  0-29:   Very low (overreached, illness, injury risk)

Components weighted:
  - ACWR balance: 30% (0.8-1.3 optimal)
  - Fatigue freshness: 25% (inverse of recent load density)
  - Training recency: 20% (days since last key workout types)
  - Physiological markers: 15% (HRV trend, resting HR trend, sleep)
  - Consistency bonus: 10% (load stability over 4 weeks)
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional


READINESS_WEIGHTS = {
    "acwr_balance": 0.30,
    "fatigue_freshness": 0.25,
    "training_recency": 0.20,
    "physiological": 0.15,
    "consistency_bonus": 0.10,
}


@dataclass
class ReadinessResult:
    score: float  # 0-100
    label: str    # "Peak", "Good", "Moderate", "Low", "Very Low"
    components: dict[str, float]  # individual component scores
    factors: list[dict]  # explanatory factors


class ReadinessEngine:
    """Computes Event Readiness score from features and physiological data."""

    @staticmethod
    def compute_readiness(
        features: dict[str, Optional[float]],
        days_since_last_activity: int = 0,
        days_since_last_threshold: Optional[int] = 0,
        days_since_last_long_run: Optional[int] = 0,
        days_since_last_race: Optional[int] = None,
        resting_hr_trend: Optional[float] = None,  # positive = rising (bad)
        hrv_trend: Optional[float] = None,  # positive = rising (good)
        sleep_score: Optional[float] = None,  # 0-100
    ) -> ReadinessResult:
        """Compute readiness score from available data.

        Args:
            features: Feature dict from FeatureService (needs acwr_4w, weekly_load_stddev, etc.)
            days_since_last_activity: Days since the last running activity
            days_since_last_threshold: Days since last threshold/tempo workout
            days_since_last_long_run: Days since last long run (>15km)
            days_since_last_race: Days since last race (None if no recent race)
            resting_hr_trend: Trend in resting HR (positive = increasing = worse)
            hrv_trend: Trend in HRV (positive = increasing = better)
            sleep_score: Recent sleep quality 0-100
        """
        components = {}
        factors = []

        # 1. ACWR Balance (30%)
        acwr = features.get("acwr_4w")
        if acwr is not None:
            acwr_score = ReadinessEngine._score_acwr(acwr)
            components["acwr_balance"] = acwr_score
            if acwr > 1.5:
                factors.append({"factor": "High training load ratio", "impact": "negative", "detail": f"ACWR {acwr:.2f} — injury risk zone"})
            elif acwr < 0.6:
                factors.append({"factor": "Low training load ratio", "impact": "negative", "detail": f"ACWR {acwr:.2f} — detraining zone"})
            elif 0.8 <= acwr <= 1.3:
                factors.append({"factor": "Balanced training load", "impact": "positive", "detail": f"ACWR {acwr:.2f} — optimal zone"})
        else:
            components["acwr_balance"] = 50.0

        # 2. Fatigue Freshness (25%)
        freshness = ReadinessEngine._score_freshness(
            days_since_last_activity, days_since_last_race
        )
        components["fatigue_freshness"] = freshness
        if days_since_last_activity == 0:
            factors.append({"factor": "Ran today", "impact": "neutral", "detail": "Recent activity — allow recovery before racing"})
        elif days_since_last_activity >= 3:
            factors.append({"factor": "Rest days", "impact": "positive", "detail": f"{days_since_last_activity} days rest — fresh legs"})

        # 3. Training Recency (20%)
        recency = ReadinessEngine._score_recency(
            days_since_last_threshold, days_since_last_long_run
        )
        components["training_recency"] = recency
        if days_since_last_threshold is not None and days_since_last_threshold > 14:
            factors.append({"factor": "No recent threshold work", "impact": "negative", "detail": f"{days_since_last_threshold} days since last tempo/threshold"})
        if days_since_last_long_run is not None and days_since_last_long_run > 21:
            factors.append({"factor": "No recent long run", "impact": "negative", "detail": f"{days_since_last_long_run} days since last long run"})

        # 4. Physiological Markers (15%)
        physio = ReadinessEngine._score_physiological(
            resting_hr_trend, hrv_trend, sleep_score
        )
        components["physiological"] = physio
        if sleep_score is not None and sleep_score >= 80:
            factors.append({"factor": "Good sleep quality", "impact": "positive", "detail": f"Sleep score {sleep_score:.0f}/100"})
        elif sleep_score is not None and sleep_score < 50:
            factors.append({"factor": "Poor sleep quality", "impact": "negative", "detail": f"Sleep score {sleep_score:.0f}/100"})

        # 5. Consistency Bonus (10%)
        consistency = ReadinessEngine._score_consistency(features)
        components["consistency_bonus"] = consistency

        # Weighted total
        total = sum(
            components[k] * READINESS_WEIGHTS[k]
            for k in READINESS_WEIGHTS
        )
        total = float(np.clip(total, 0, 100))

        label = ReadinessEngine._get_label(total)

        return ReadinessResult(
            score=round(total, 1),
            label=label,
            components={k: round(v, 1) for k, v in components.items()},
            factors=factors,
        )

    @staticmethod
    def _score_acwr(acwr: float) -> float:
        """Score ACWR: optimal at 0.8-1.3, penalty outside."""
        if 0.8 <= acwr <= 1.3:
            # Peak score within optimal zone, highest at 1.0
            deviation = abs(acwr - 1.05) / 0.25
            return 100 - (deviation * 15)
        elif acwr > 1.3:
            # Rapid decline above 1.3
            overshoot = acwr - 1.3
            return max(0, 85 - (overshoot * 150))
        else:
            # Gradual decline below 0.8
            undershoot = 0.8 - acwr
            return max(0, 85 - (undershoot * 100))

    @staticmethod
    def _score_freshness(days_since_activity: int, days_since_race: Optional[int]) -> float:
        """Score freshness: sweet spot is 1-2 days rest."""
        # Ran today: moderate freshness
        if days_since_activity == 0:
            base = 55
        elif days_since_activity == 1:
            base = 85
        elif days_since_activity == 2:
            base = 90
        elif days_since_activity == 3:
            base = 80
        elif days_since_activity <= 5:
            base = 70
        elif days_since_activity <= 10:
            base = 50  # starting to lose sharpness
        else:
            base = 30  # significant time off

        # Recent race penalty (need recovery)
        if days_since_race is not None:
            if days_since_race < 3:
                base *= 0.5
            elif days_since_race < 7:
                base *= 0.7
            elif days_since_race < 14:
                base *= 0.85

        return float(np.clip(base, 0, 100))

    @staticmethod
    def _score_recency(days_since_threshold: Optional[int], days_since_long_run: Optional[int]) -> float:
        """Score training recency: recent key workouts = sharper."""
        if days_since_threshold is None:
            days_since_threshold = 14
        if days_since_long_run is None:
            days_since_long_run = 30
        threshold_score = max(0, 100 - days_since_threshold * 5)
        long_run_score = max(0, 100 - days_since_long_run * 3)
        return (threshold_score * 0.6 + long_run_score * 0.4)

    @staticmethod
    def _score_physiological(
        resting_hr_trend: Optional[float],
        hrv_trend: Optional[float],
        sleep_score: Optional[float],
    ) -> float:
        """Score physiological markers."""
        scores = []

        if resting_hr_trend is not None:
            # Negative trend (decreasing HR) is good
            if resting_hr_trend <= -1:
                scores.append(90)
            elif resting_hr_trend <= 0:
                scores.append(70)
            elif resting_hr_trend <= 2:
                scores.append(50)
            else:
                scores.append(30)

        if hrv_trend is not None:
            # Positive trend (increasing HRV) is good
            if hrv_trend >= 2:
                scores.append(90)
            elif hrv_trend >= 0:
                scores.append(70)
            elif hrv_trend >= -2:
                scores.append(50)
            else:
                scores.append(30)

        if sleep_score is not None:
            scores.append(sleep_score)

        return float(np.mean(scores)) if scores else 50.0

    @staticmethod
    def _score_consistency(features: dict) -> float:
        """Score training consistency from feature data."""
        stddev = features.get("weekly_load_stddev")
        session_stability = features.get("session_density_stability")

        scores = []
        if stddev is not None:
            # Lower stddev = more consistent
            if stddev < 3000:
                scores.append(90)
            elif stddev < 6000:
                scores.append(70)
            elif stddev < 10000:
                scores.append(50)
            else:
                scores.append(30)

        if session_stability is not None:
            if session_stability < 0.5:
                scores.append(90)
            elif session_stability < 1.0:
                scores.append(70)
            elif session_stability < 2.0:
                scores.append(50)
            else:
                scores.append(30)

        return float(np.mean(scores)) if scores else 50.0

    @staticmethod
    def _get_label(score: float) -> str:
        if score >= 90:
            return "Peak"
        elif score >= 70:
            return "Good"
        elif score >= 50:
            return "Moderate"
        elif score >= 30:
            return "Low"
        return "Very Low"
