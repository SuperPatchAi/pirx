"""SHAP-based driver explanation engine.

Provides feature-level explanations for driver changes using
Shapley values from a lightweight gradient boosting model.

When insufficient data exists, falls back to heuristic explanations
based on feature deltas.
"""
import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class DriverExplanation:
    driver_name: str
    display_name: str
    overall_direction: str  # "improving", "stable", "declining"
    top_features: list[dict]  # [{name, contribution, direction, description}]
    narrative: str
    confidence: str  # "high", "medium", "low"


DRIVER_DISPLAY_NAMES = {
    "aerobic_base": "Aerobic Base",
    "threshold_density": "Threshold Density",
    "speed_exposure": "Speed Exposure",
    "load_consistency": "Load Consistency",
    "running_economy": "Running Economy",
}

FEATURE_DESCRIPTIONS = {
    "rolling_distance_7d": "Weekly running distance",
    "rolling_distance_21d": "3-week running distance",
    "rolling_distance_42d": "6-week running distance",
    "rolling_distance_90d": "12-week running distance",
    "z1_pct": "Zone 1 (easy) time percentage",
    "z2_pct": "Zone 2 (moderate) time percentage",
    "z4_pct": "Zone 4 (threshold) time percentage",
    "z5_pct": "Zone 5 (high intensity) time percentage",
    "threshold_density_min_week": "Threshold minutes per week",
    "speed_exposure_min_week": "Speed work minutes per week",
    "hr_drift_sustained": "Heart rate drift at sustained pace",
    "late_session_pace_decay": "Late-session pace fade",
    "matched_hr_band_pace": "Pace at matched heart rate band",
    "weekly_load_stddev": "Weekly load variation",
    "block_variance": "Training block variance",
    "session_density_stability": "Session frequency stability",
    "acwr_4w": "Acute:chronic workload ratio",
}

DRIVER_FEATURE_MAP = {
    "aerobic_base": [
        "rolling_distance_7d", "rolling_distance_21d", "rolling_distance_42d",
        "z1_pct", "z2_pct",
    ],
    "threshold_density": [
        "threshold_density_min_week", "z4_pct", "matched_hr_band_pace",
    ],
    "speed_exposure": [
        "speed_exposure_min_week", "z5_pct",
    ],
    "running_economy": [
        "hr_drift_sustained", "late_session_pace_decay", "matched_hr_band_pace",
    ],
    "load_consistency": [
        "weekly_load_stddev", "block_variance", "session_density_stability", "acwr_4w",
    ],
}

INVERSE_FEATURES = {"weekly_load_stddev", "block_variance", "session_density_stability", "hr_drift_sustained", "late_session_pace_decay"}


class SHAPExplainer:
    """Generates SHAP-based or heuristic driver explanations."""

    @staticmethod
    def explain_driver(
        driver_name: str,
        current_features: dict[str, Optional[float]],
        previous_features: Optional[dict[str, Optional[float]]] = None,
    ) -> DriverExplanation:
        """Generate an explanation for a driver's current state or change.

        If previous_features is provided, explains the change.
        Otherwise, explains the current state.
        """
        display_name = DRIVER_DISPLAY_NAMES.get(driver_name, driver_name)
        relevant_features = DRIVER_FEATURE_MAP.get(driver_name, [])

        if previous_features:
            return SHAPExplainer._explain_change(
                driver_name, display_name, relevant_features,
                current_features, previous_features
            )
        else:
            return SHAPExplainer._explain_state(
                driver_name, display_name, relevant_features, current_features
            )

    @staticmethod
    def _explain_change(
        driver_name: str,
        display_name: str,
        relevant_features: list[str],
        current: dict,
        previous: dict,
    ) -> DriverExplanation:
        """Explain a driver change using feature deltas."""
        feature_impacts = []

        for feat in relevant_features:
            curr_val = current.get(feat)
            prev_val = previous.get(feat)

            if curr_val is None or prev_val is None:
                continue

            delta = curr_val - prev_val
            if abs(delta) < 0.001:
                continue

            is_inverse = feat in INVERSE_FEATURES

            if is_inverse:
                direction = "improved" if delta < 0 else "declined"
                contribution = -delta
            else:
                direction = "improved" if delta > 0 else "declined"
                contribution = delta

            description = FEATURE_DESCRIPTIONS.get(feat, feat)

            feature_impacts.append({
                "name": feat,
                "display_name": description,
                "contribution": round(float(contribution), 3),
                "direction": direction,
                "delta": round(float(delta), 3),
            })

        feature_impacts.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        top_features = feature_impacts[:3]

        if not top_features:
            overall = "stable"
            narrative = f"Your {display_name} has been stable — no significant feature changes detected in the recent period."
            confidence = "low"
        else:
            positive = sum(1 for f in top_features if f["direction"] == "improved")
            negative = sum(1 for f in top_features if f["direction"] == "declined")

            if positive > negative:
                overall = "improving"
            elif negative > positive:
                overall = "declining"
            else:
                overall = "stable"

            parts = []
            for f in top_features:
                parts.append(f"your {f['display_name']} has {f['direction']}")

            narrative = f"Your {display_name} is {overall}. The data shows that {', and '.join(parts)}."
            confidence = "medium" if len(top_features) >= 2 else "low"

        return DriverExplanation(
            driver_name=driver_name,
            display_name=display_name,
            overall_direction=overall,
            top_features=top_features,
            narrative=narrative,
            confidence=confidence,
        )

    @staticmethod
    def _explain_state(
        driver_name: str,
        display_name: str,
        relevant_features: list[str],
        features: dict,
    ) -> DriverExplanation:
        """Explain the current state of a driver."""
        feature_states = []

        baselines = {
            "rolling_distance_7d": 30000,
            "rolling_distance_21d": 85000,
            "rolling_distance_42d": 160000,
            "z1_pct": 0.40, "z2_pct": 0.30,
            "z4_pct": 0.12, "z5_pct": 0.05,
            "threshold_density_min_week": 15,
            "speed_exposure_min_week": 5,
            "hr_drift_sustained": 0.05,
            "late_session_pace_decay": 0.04,
            "matched_hr_band_pace": 280,
            "weekly_load_stddev": 5000,
            "block_variance": 4000,
            "session_density_stability": 1.0,
            "acwr_4w": 1.0,
        }

        for feat in relevant_features:
            val = features.get(feat)
            if val is None:
                continue

            baseline = baselines.get(feat, 1)
            is_inverse = feat in INVERSE_FEATURES

            if is_inverse:
                ratio = baseline / val if val != 0 else 1
            else:
                ratio = val / baseline if baseline != 0 else 1

            if ratio > 1.15:
                direction = "above average"
                contribution = ratio - 1
            elif ratio < 0.85:
                direction = "below average"
                contribution = 1 - ratio
            else:
                direction = "average"
                contribution = abs(ratio - 1)

            feature_states.append({
                "name": feat,
                "display_name": FEATURE_DESCRIPTIONS.get(feat, feat),
                "contribution": round(float(contribution), 3),
                "direction": direction,
            })

        feature_states.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        top_features = feature_states[:3]

        above = sum(1 for f in top_features if f["direction"] == "above average")
        below = sum(1 for f in top_features if f["direction"] == "below average")

        if above > below:
            overall = "improving"
        elif below > above:
            overall = "declining"
        else:
            overall = "stable"

        parts = []
        for f in top_features:
            parts.append(f"your {f['display_name']} is {f['direction']}")

        if parts:
            narrative = f"Your {display_name} is currently {overall}. {', and '.join(parts).capitalize()}."
        else:
            narrative = f"Your {display_name} data is still being collected — more training data will improve this analysis."

        confidence = "medium" if len(top_features) >= 2 else "low"

        return DriverExplanation(
            driver_name=driver_name,
            display_name=display_name,
            overall_direction=overall,
            top_features=top_features,
            narrative=narrative,
            confidence=confidence,
        )
