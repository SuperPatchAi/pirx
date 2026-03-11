"""Local Matrix Completion (LMC) rank-2 baseline estimation.

Predicts runner performance across distances from 1-3 known race results.
Based on Blythe & Király (2016): 164,746 runners, 1,417,432 performances.
LMC outperforms Riegel by 30% (RMSE) and beats Purdy Points, k-NN, and EM.
"""
import numpy as np
from typing import Optional


COMPONENT_MATRIX = {
    "800":  [4.305,  0.3045, 0.2224],
    "1500": [4.964,  0.0798, 0.3263],
    "mile": [5.049,  0.0806, 0.3092],
    "3000": [5.621, -0.040,  0.299],
    "5000": [6.179, -0.1597, 0.3157],
    "10000": [6.844, -0.1983, 0.2717],
    "half":  [7.555, -0.2279, -0.1153],
    "marathon": [8.243, -0.2785, -0.6912],
}

LAMBDA_BOUNDS = {
    "lambda1_min": 1.10,
    "lambda1_max": 1.15,
    "lambda1_median": 1.12,
    "lambda2_min": -0.4,
    "lambda2_max": 0.4,
    "lambda2_median": 0.0,
}


class LMCEngine:
    """Local Matrix Completion engine for cross-distance performance prediction."""

    def __init__(self, rank: int = 2):
        """Initialize LMC engine.

        Args:
            rank: Model rank. 2 for users with 1-3 races, 3 for 4+ races.
        """
        if rank not in (1, 2, 3):
            raise ValueError("Rank must be 1, 2, or 3")
        self.rank = rank

    def estimate_runner(
        self, known_events: list[str], known_times_seconds: list[float]
    ) -> np.ndarray:
        """Estimate runner coefficients (lambda) from known race results.

        Args:
            known_events: List of event keys (e.g., ["5000", "10000"])
            known_times_seconds: Corresponding race times in seconds

        Returns:
            Lambda vector of length `self.rank`

        Raises:
            ValueError: If events don't match or insufficient data
        """
        if len(known_events) != len(known_times_seconds):
            raise ValueError("Events and times must have same length")
        if len(known_events) == 0:
            raise ValueError("Need at least 1 known performance")

        for event in known_events:
            if event not in COMPONENT_MATRIX:
                raise ValueError(f"Unknown event: {event}. Valid: {list(COMPONENT_MATRIX.keys())}")

        F_sub = np.array([COMPONENT_MATRIX[e][:self.rank] for e in known_events])
        log_times = np.log(np.array(known_times_seconds, dtype=float))

        lambda_hat, residuals, rank_out, sv = np.linalg.lstsq(F_sub, log_times, rcond=None)

        # Bound lambda0 (intercept multiplier) near 1.0
        if len(lambda_hat) >= 1:
            lambda_hat[0] = np.clip(lambda_hat[0], 1.08, 1.15)

        # Bound lambda1 (speed-endurance coefficient) within population norms
        if len(lambda_hat) >= 2:
            lambda_hat[1] = np.clip(
                lambda_hat[1],
                LAMBDA_BOUNDS["lambda2_min"],
                LAMBDA_BOUNDS["lambda2_max"],
            )

        return lambda_hat

    def predict_time(self, lambda_hat: np.ndarray, target_event: str) -> float:
        """Predict race time at a target distance.

        Args:
            lambda_hat: Runner's estimated coefficients
            target_event: Event key to predict

        Returns:
            Predicted time in seconds
        """
        if target_event not in COMPONENT_MATRIX:
            raise ValueError(f"Unknown event: {target_event}")

        f_target = np.array(COMPONENT_MATRIX[target_event][:self.rank])
        log_time_pred = np.dot(lambda_hat, f_target)
        return float(np.exp(log_time_pred))

    def predict_all_events(
        self, lambda_hat: np.ndarray, events: list[str] = None
    ) -> dict[str, float]:
        """Predict times for multiple events.

        Args:
            lambda_hat: Runner's estimated coefficients
            events: Events to predict. Defaults to PIRX core events.

        Returns:
            Dict of event -> predicted time in seconds
        """
        if events is None:
            events = ["1500", "3000", "5000", "10000"]

        return {event: self.predict_time(lambda_hat, event) for event in events}

    def cold_start_estimate(
        self, best_pace_sec_per_km: float, effort_distance_m: float
    ) -> np.ndarray:
        """Estimate lambda from sustained effort when no race data exists.

        Uses the runner's best sustained pace effort as a proxy race result.
        Applies a conservative adjustment (slower by 5%) since training
        efforts are typically slower than race efforts.

        Args:
            best_pace_sec_per_km: Best sustained pace in sec/km
            effort_distance_m: Distance of the sustained effort in meters

        Returns:
            Estimated lambda vector
        """
        proxy_time = best_pace_sec_per_km * (effort_distance_m / 1000) * 1.05

        closest_event = self._find_closest_event(effort_distance_m)
        return self.estimate_runner([closest_event], [proxy_time])

    @staticmethod
    def _find_closest_event(distance_m: float) -> str:
        """Find the closest standard event to a given distance."""
        event_distances = {
            "800": 800, "1500": 1500, "mile": 1609, "3000": 3000,
            "5000": 5000, "10000": 10000, "half": 21097, "marathon": 42195,
        }
        closest = min(event_distances, key=lambda e: abs(event_distances[e] - distance_m))
        return closest

    def compute_supported_range(
        self, lambda_hat: np.ndarray, target_event: str, confidence: float = 0.68
    ) -> tuple[float, float]:
        """Compute the Supported Range (uncertainty interval) for a prediction.

        Width increases with:
        - Distance from known events
        - Component uncertainty (f2: ±0.02, f3: ±0.04)
        - Fewer known races

        Args:
            lambda_hat: Runner's lambda
            target_event: Event to compute range for
            confidence: Confidence level (0.68 = 1σ, 0.95 = 2σ)

        Returns:
            (lower_bound_seconds, upper_bound_seconds)
        """
        predicted = self.predict_time(lambda_hat, target_event)

        f2_uncertainty = 0.02
        f3_uncertainty = 0.04

        log_uncertainty = 0.0
        if self.rank >= 2 and len(lambda_hat) >= 2:
            log_uncertainty += abs(lambda_hat[1]) * f2_uncertainty
        if self.rank >= 3 and len(lambda_hat) >= 3:
            log_uncertainty += abs(lambda_hat[2]) * f3_uncertainty

        base_uncertainty = 0.015  # ~1.5% base uncertainty
        total_log_uncertainty = base_uncertainty + log_uncertainty

        multiplier = 1.0 if confidence <= 0.68 else 1.96

        lower = predicted * np.exp(-total_log_uncertainty * multiplier)
        upper = predicted * np.exp(total_log_uncertainty * multiplier)

        return (float(lower), float(upper))
