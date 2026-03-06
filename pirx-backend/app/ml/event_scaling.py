"""Event distance scaling using Riegel power law and individual exponents.

Scales a baseline race performance across PIRX target distances (1500m-10K).
Implements classic Riegel, modified Riegel, and LMC-integrated scaling.
"""
import numpy as np
from typing import Optional


EVENT_DISTANCES_M = {
    "800": 800,
    "1500": 1500,
    "mile": 1609,
    "3000": 3000,
    "5000": 5000,
    "10000": 10000,
    "half": 21097,
    "marathon": 42195,
}

DEFAULT_EXPONENT = 1.06
EXPONENT_BOUNDS = (1.10, 1.15)  # Population norms from Blythe & Király
PHASE_TRANSITION_DISTANCE = 5000  # meters


class EventScaler:
    """Scales running performance across distances using power law models."""

    @staticmethod
    def riegel_scale(
        known_time_s: float,
        known_distance_m: float,
        target_distance_m: float,
        exponent: float = DEFAULT_EXPONENT,
    ) -> float:
        """Classic Riegel power law scaling.

        T2 = T1 × (D2 / D1) ^ exponent

        Args:
            known_time_s: Known race time in seconds
            known_distance_m: Known race distance in meters
            target_distance_m: Target distance in meters
            exponent: Power law exponent (default 1.06)

        Returns:
            Predicted time in seconds at target distance
        """
        if known_distance_m <= 0 or target_distance_m <= 0:
            raise ValueError("Distances must be positive")
        if known_time_s <= 0:
            raise ValueError("Time must be positive")

        return known_time_s * (target_distance_m / known_distance_m) ** exponent

    @staticmethod
    def modified_riegel(
        known_time_s: float,
        known_distance_m: float,
        target_distance_m: float,
        weekly_km: float = 40.0,
    ) -> float:
        """Modified Riegel that adjusts exponent by training volume.

        Higher weekly mileage → lower effective exponent (better endurance scaling).

        Args:
            known_time_s: Known race time in seconds
            known_distance_m: Known race distance in meters
            target_distance_m: Target distance in meters
            weekly_km: Weekly training volume in km
        """
        # Volume modifier: more mileage = lower exponent
        # Baseline 40km/week = 1.06, each +10km reduces by 0.005
        k = max(0.98, 1.06 - 0.005 * ((weekly_km - 40) / 10))
        k = min(k, 1.15)  # bound within population norms

        return EventScaler.riegel_scale(known_time_s, known_distance_m, target_distance_m, k)

    @staticmethod
    def compute_individual_exponent(
        race_results: list[dict],
    ) -> Optional[float]:
        """Compute individual power law exponent from multiple race results.

        Each dict should have: {"distance_m": float, "time_s": float}
        Requires at least 2 race results at different distances.

        Returns:
            Individual exponent, or None if insufficient data.
        """
        if len(race_results) < 2:
            return None

        log_distances = np.log([r["distance_m"] for r in race_results])
        log_times = np.log([r["time_s"] for r in race_results])

        # Fit log(time) = exponent * log(distance) + intercept
        A = np.vstack([log_distances, np.ones(len(log_distances))]).T
        result = np.linalg.lstsq(A, log_times, rcond=None)
        exponent = result[0][0]

        # Bound within population norms
        exponent = np.clip(exponent, EXPONENT_BOUNDS[0], EXPONENT_BOUNDS[1])

        return float(exponent)

    @staticmethod
    def scale_with_phase_transition(
        known_time_s: float,
        known_distance_m: float,
        target_distance_m: float,
        exponent: float = DEFAULT_EXPONENT,
    ) -> float:
        """Scale with phase transition handling at 5000m boundary.

        Below 5K: better short-distance performance predicts *worse* long-distance.
        Above 5K: speed and endurance positively correlated.
        ~800m: anaerobic → aerobic transition.

        Applies exponent adjustment when crossing the 5K boundary.
        """
        crosses_boundary = (
            (known_distance_m < PHASE_TRANSITION_DISTANCE and target_distance_m >= PHASE_TRANSITION_DISTANCE)
            or (known_distance_m >= PHASE_TRANSITION_DISTANCE and target_distance_m < PHASE_TRANSITION_DISTANCE)
        )

        if crosses_boundary:
            # Apply uncertainty penalty: widen the exponent toward population median
            adjustment = 0.02  # Additional ~2% uncertainty
            if target_distance_m > known_distance_m:
                exponent += adjustment
            else:
                exponent -= adjustment

        return EventScaler.riegel_scale(known_time_s, known_distance_m, target_distance_m, exponent)

    @staticmethod
    def scale_all_events(
        known_time_s: float,
        known_event: str,
        exponent: float = DEFAULT_EXPONENT,
        target_events: list[str] = None,
    ) -> dict[str, float]:
        """Scale a known performance to all PIRX target events.

        Args:
            known_time_s: Known race time in seconds
            known_event: Event key (e.g., "5000")
            exponent: Power law exponent
            target_events: Events to predict. Default: ["1500", "3000", "5000", "10000"]

        Returns:
            Dict of event -> predicted time in seconds
        """
        if known_event not in EVENT_DISTANCES_M:
            raise ValueError(f"Unknown event: {known_event}")

        if target_events is None:
            target_events = ["1500", "3000", "5000", "10000"]

        known_distance = EVENT_DISTANCES_M[known_event]
        results = {}

        for event in target_events:
            if event not in EVENT_DISTANCES_M:
                raise ValueError(f"Unknown target event: {event}")
            target_distance = EVENT_DISTANCES_M[event]
            results[event] = EventScaler.scale_with_phase_transition(
                known_time_s, known_distance, target_distance, exponent
            )

        return results

    @staticmethod
    def environmental_adjustment(
        predicted_time_s: float,
        temperature_c: float,
    ) -> float:
        """Apply temperature correction to projected time.

        Optimal range: 10-17.5°C. Decline: ~0.35% per °C outside optimal.
        Based on Grivas & Safari (2025).
        """
        optimal_low = 10.0
        optimal_high = 17.5
        decline_rate = 0.0035  # 0.35% per degree

        if optimal_low <= temperature_c <= optimal_high:
            return predicted_time_s

        if temperature_c < optimal_low:
            deviation = optimal_low - temperature_c
        else:
            deviation = temperature_c - optimal_high

        penalty = 1.0 + (decline_rate * deviation)
        return predicted_time_s * penalty
