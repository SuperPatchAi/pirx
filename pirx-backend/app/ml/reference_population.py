"""Synthetic reference population generated from published research statistics.

Provides 1000 representative runner profiles for calibrating PIRX projections
when the real user base is too small for KNN or population-based analysis.

Sources:
- Blythe & Kiraly 2016 (164,746 runners): lambda distributions, component matrix
- Zrenner et al. 2021 (6,771 runners): training features, response metrics
- Lerebourg et al. 2023 (820 athletes): BMI, age, marathon correlations
- Qin et al. 2025 (120 runners): intensity distributions, pyramidal vs polarized
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional
from app.ml.lmc import COMPONENT_MATRIX, LAMBDA_BOUNDS


POPULATION_SIZE = 1000
RANDOM_SEED = 42


@dataclass
class SyntheticRunner:
    """A synthetic runner profile for population calibration."""
    runner_id: int

    # LMC parameters
    lambda1: float  # Overall endurance (1.10-1.15)
    lambda2: float  # Speed-endurance balance

    # Race times (seconds)
    time_1500: float
    time_3000: float
    time_5000: float
    time_10000: float

    # Training features
    weekly_km: float
    sessions_per_week: int
    z1_pct: float
    z2_pct: float
    z3_pct: float
    z4_pct: float
    z5_pct: float
    long_run_km: float

    # Demographics
    age: int
    bmi: float

    # Derived
    training_type: str  # "pyramidal", "polarized", "threshold-heavy"
    performance_level: str  # "beginner", "intermediate", "advanced", "elite"


class ReferencePopulation:
    """Generates and queries synthetic runner population."""

    def __init__(self, seed: int = RANDOM_SEED, size: int = POPULATION_SIZE):
        self.rng = np.random.default_rng(seed)
        self.size = size
        self._runners: list[SyntheticRunner] = []
        self._generate()

    def _generate(self):
        """Generate the full synthetic population."""
        for i in range(self.size):
            runner = self._generate_runner(i)
            self._runners.append(runner)

    def _generate_runner(self, idx: int) -> SyntheticRunner:
        # --- LMC Parameters (Blythe & Kiraly 2016) ---
        # Lambda1: median 1.12, 5th pct 1.10, 95th pct 1.15
        lambda1 = self.rng.normal(1.12, 0.015)
        lambda1 = float(np.clip(lambda1, 1.08, 1.17))

        # Lambda2: centered at 0, spread based on specialization
        lambda2 = self.rng.normal(0.0, 0.08)
        lambda2 = float(np.clip(lambda2, -0.4, 0.4))

        # Compute race times from lambdas using component matrix
        def compute_time(event: str) -> float:
            f = COMPONENT_MATRIX[event]
            log_t = lambda1 * f[0] + lambda2 * f[1]
            return float(np.exp(log_t))

        time_1500 = compute_time("1500")
        time_3000 = compute_time("3000")
        time_5000 = compute_time("5000")
        time_10000 = compute_time("10000")

        # --- Performance level from 5K time ---
        if time_5000 < 960:      # sub-16:00
            level = "elite"
        elif time_5000 < 1200:   # sub-20:00
            level = "advanced"
        elif time_5000 < 1500:   # sub-25:00
            level = "intermediate"
        else:
            level = "beginner"

        # --- Training features (Zrenner et al. 2021) ---
        # Weekly km correlates with performance: r=0.58
        base_km = 70 - (time_5000 / 30)  # faster = more km
        weekly_km = float(self.rng.lognormal(np.log(max(base_km, 15)), 0.3))
        weekly_km = float(np.clip(weekly_km, 10, 180))

        sessions_per_week = int(np.clip(
            self.rng.poisson(max(3, weekly_km / 10)), 2, 14
        ))

        # --- Intensity distribution (Qin et al. 2025) ---
        # Randomly assign training type
        training_type_roll = self.rng.random()
        if training_type_roll < 0.5:
            # Pyramidal: 70/20/10
            z1 = self.rng.normal(0.40, 0.08)
            z2 = self.rng.normal(0.30, 0.06)
            z3 = self.rng.normal(0.13, 0.04)
            z4 = self.rng.normal(0.12, 0.04)
            z5 = self.rng.normal(0.05, 0.02)
            t_type = "pyramidal"
        elif training_type_roll < 0.8:
            # Polarized: 80/5/15
            z1 = self.rng.normal(0.45, 0.08)
            z2 = self.rng.normal(0.35, 0.06)
            z3 = self.rng.normal(0.03, 0.02)
            z4 = self.rng.normal(0.07, 0.03)
            z5 = self.rng.normal(0.10, 0.03)
            t_type = "polarized"
        else:
            # Threshold-heavy
            z1 = self.rng.normal(0.30, 0.06)
            z2 = self.rng.normal(0.25, 0.06)
            z3 = self.rng.normal(0.15, 0.04)
            z4 = self.rng.normal(0.20, 0.05)
            z5 = self.rng.normal(0.10, 0.03)
            t_type = "threshold-heavy"

        # Normalize zone percentages to sum to 1.0
        zones = np.array([z1, z2, z3, z4, z5])
        zones = np.clip(zones, 0.01, 0.9)
        zones = zones / zones.sum()

        # Long run: correlated with weekly volume
        long_run_km = float(np.clip(weekly_km * self.rng.uniform(0.25, 0.45), 5, 42))

        # --- Demographics (Lerebourg et al. 2023) ---
        age = int(np.clip(self.rng.normal(38, 10), 18, 75))
        bmi = float(np.clip(self.rng.normal(22.5, 2.5), 16, 35))

        return SyntheticRunner(
            runner_id=idx,
            lambda1=lambda1,
            lambda2=lambda2,
            time_1500=round(time_1500, 1),
            time_3000=round(time_3000, 1),
            time_5000=round(time_5000, 1),
            time_10000=round(time_10000, 1),
            weekly_km=round(weekly_km, 1),
            sessions_per_week=sessions_per_week,
            z1_pct=round(float(zones[0]), 3),
            z2_pct=round(float(zones[1]), 3),
            z3_pct=round(float(zones[2]), 3),
            z4_pct=round(float(zones[3]), 3),
            z5_pct=round(float(zones[4]), 3),
            long_run_km=round(long_run_km, 1),
            age=age,
            bmi=round(bmi, 1),
            training_type=t_type,
            performance_level=level,
        )

    @property
    def runners(self) -> list[SyntheticRunner]:
        return self._runners

    def get_percentile(self, event: str, time_seconds: float) -> float:
        """Get the percentile ranking for a time at a given event.

        Returns 0-100 where 100 = fastest.
        """
        time_attr = f"time_{event}"
        times = [getattr(r, time_attr) for r in self._runners if hasattr(r, time_attr)]
        if not times:
            return 50.0

        slower_count = sum(1 for t in times if t > time_seconds)
        return round(100.0 * slower_count / len(times), 1)

    def get_exponent_percentile(self, lambda1: float) -> float:
        """Get percentile for a lambda1 value. Lower lambda1 = more endurance-gifted."""
        values = [r.lambda1 for r in self._runners]
        # Lower lambda1 is better, so count those with HIGHER lambda1
        better_count = sum(1 for v in values if v > lambda1)
        return round(100.0 * better_count / len(values), 1)

    def get_similar_runners(
        self, time_5000: float, weekly_km: float, n: int = 10
    ) -> list[SyntheticRunner]:
        """Find the n most similar runners by 5K time and weekly volume.

        Uses normalized Euclidean distance.
        """
        time_mean = np.mean([r.time_5000 for r in self._runners])
        time_std = np.std([r.time_5000 for r in self._runners]) or 1
        km_mean = np.mean([r.weekly_km for r in self._runners])
        km_std = np.std([r.weekly_km for r in self._runners]) or 1

        distances = []
        for r in self._runners:
            dt = ((r.time_5000 - time_5000) / time_std) ** 2
            dk = ((r.weekly_km - weekly_km) / km_std) ** 2
            distances.append((np.sqrt(dt + dk), r))

        distances.sort(key=lambda x: x[0])
        return [r for _, r in distances[:n]]

    def get_calibration_data(self, performance_level: str) -> dict:
        """Get population statistics for a performance level.

        Returns calibration data for driver weights, range widths, etc.
        """
        runners = [r for r in self._runners if r.performance_level == performance_level]
        if not runners:
            runners = self._runners

        return {
            "count": len(runners),
            "lambda1_mean": round(float(np.mean([r.lambda1 for r in runners])), 4),
            "lambda1_std": round(float(np.std([r.lambda1 for r in runners])), 4),
            "time_5000_median": round(float(np.median([r.time_5000 for r in runners])), 1),
            "time_5000_p10": round(float(np.percentile([r.time_5000 for r in runners], 10)), 1),
            "time_5000_p90": round(float(np.percentile([r.time_5000 for r in runners], 90)), 1),
            "weekly_km_median": round(float(np.median([r.weekly_km for r in runners])), 1),
            "z4_pct_mean": round(float(np.mean([r.z4_pct for r in runners])), 3),
            "z5_pct_mean": round(float(np.mean([r.z5_pct for r in runners])), 3),
            "training_type_distribution": {
                "pyramidal": sum(1 for r in runners if r.training_type == "pyramidal") / len(runners),
                "polarized": sum(1 for r in runners if r.training_type == "polarized") / len(runners),
                "threshold-heavy": sum(1 for r in runners if r.training_type == "threshold-heavy") / len(runners),
            },
            "supported_range_pct": self._compute_range_calibration(runners),
        }

    def _compute_range_calibration(self, runners: list[SyntheticRunner]) -> dict:
        """Compute Supported Range width calibration from population variance."""
        times_5k = [r.time_5000 for r in runners]
        std = float(np.std(times_5k))
        mean = float(np.mean(times_5k))

        return {
            "one_sigma_pct": round(std / mean * 100, 2),
            "two_sigma_pct": round(2 * std / mean * 100, 2),
        }

    def get_population_summary(self) -> dict:
        """Get a summary of the full synthetic population."""
        levels = {}
        for level in ["beginner", "intermediate", "advanced", "elite"]:
            count = sum(1 for r in self._runners if r.performance_level == level)
            levels[level] = count

        return {
            "total_runners": self.size,
            "performance_distribution": levels,
            "lambda1_range": {
                "min": round(min(r.lambda1 for r in self._runners), 4),
                "max": round(max(r.lambda1 for r in self._runners), 4),
                "median": round(float(np.median([r.lambda1 for r in self._runners])), 4),
            },
            "time_5000_range": {
                "min": round(min(r.time_5000 for r in self._runners), 1),
                "max": round(max(r.time_5000 for r in self._runners), 1),
                "median": round(float(np.median([r.time_5000 for r in self._runners])), 1),
            },
        }


# Module-level singleton for reuse
_population: Optional[ReferencePopulation] = None


def get_reference_population() -> ReferencePopulation:
    """Get the singleton reference population."""
    global _population
    if _population is None:
        _population = ReferencePopulation()
    return _population
