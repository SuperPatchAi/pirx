"""What We're Learning About You — pattern detection module.

Detects observational patterns in training data and generates insights.
All content is observational — NEVER prescriptive or coaching.
Patterns are stored as embeddings for chat RAG retrieval.

Content types:
- Consistency patterns (stable/variable training)
- Response patterns (which driver responds to what training)
- Emerging trends (volume, intensity, economy shifts)
- Risk patterns (high ACWR, insufficient rest)
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import numpy as np


@dataclass
class Insight:
    category: str  # "consistency", "response", "trend", "risk"
    title: str
    body: str
    status: str  # "observational", "emerging", "supported"
    confidence: float  # 0-1
    data_points: int


class LearningModule:
    """Detects and generates observational insights from training data."""

    @staticmethod
    def analyze_training_patterns(
        features_history: list[dict],
        driver_history: Optional[list[dict]] = None,
    ) -> list[Insight]:
        """Analyze training data for patterns and generate insights.

        Args:
            features_history: List of feature snapshots over time
            driver_history: List of driver state snapshots over time

        Returns:
            List of detected insights
        """
        insights = []

        if len(features_history) < 2:
            return insights

        insights.extend(LearningModule._detect_consistency_patterns(features_history))
        insights.extend(LearningModule._detect_volume_trends(features_history))
        insights.extend(LearningModule._detect_intensity_patterns(features_history))
        insights.extend(LearningModule._detect_risk_patterns(features_history))

        if driver_history and len(driver_history) >= 2:
            insights.extend(LearningModule._detect_response_patterns(features_history, driver_history))

        return insights

    @staticmethod
    def _detect_consistency_patterns(history: list[dict]) -> list[Insight]:
        """Detect training consistency or variability."""
        insights = []

        stddevs = [h.get("weekly_load_stddev") for h in history if h.get("weekly_load_stddev") is not None]

        if len(stddevs) >= 3:
            avg_stddev = np.mean(stddevs)
            recent_stddev = stddevs[-1]

            if avg_stddev < 3000 and recent_stddev < 3000:
                insights.append(Insight(
                    category="consistency",
                    title="Consistent Training Pattern",
                    body="Your training load has been remarkably stable over the observed period. Consistent load is one of the strongest predictors of sustained improvement in the Load Consistency driver.",
                    status="supported" if len(stddevs) >= 6 else "emerging",
                    confidence=min(0.9, len(stddevs) / 10),
                    data_points=len(stddevs),
                ))
            elif recent_stddev > avg_stddev * 1.5 and recent_stddev > 5000:
                insights.append(Insight(
                    category="consistency",
                    title="Increased Training Variability",
                    body="Your week-to-week training load has become more variable recently compared to your historical pattern. This increased variability is reflected in the Load Consistency driver.",
                    status="observational",
                    confidence=0.6,
                    data_points=len(stddevs),
                ))

        return insights

    @staticmethod
    def _detect_volume_trends(history: list[dict]) -> list[Insight]:
        """Detect volume trends over time."""
        insights = []

        distances = [h.get("rolling_distance_21d") for h in history if h.get("rolling_distance_21d") is not None]

        if len(distances) >= 4:
            first_half = np.mean(distances[:len(distances)//2])
            second_half = np.mean(distances[len(distances)//2:])

            pct_change = (second_half - first_half) / first_half * 100 if first_half > 0 else 0

            if pct_change > 15:
                insights.append(Insight(
                    category="trend",
                    title="Volume Building Phase",
                    body=f"Your 3-week rolling distance has increased approximately {pct_change:.0f}% over the observed period. This progressive volume increase is feeding the Aerobic Base driver.",
                    status="emerging" if len(distances) >= 6 else "observational",
                    confidence=min(0.8, len(distances) / 12),
                    data_points=len(distances),
                ))
            elif pct_change < -15:
                insights.append(Insight(
                    category="trend",
                    title="Volume Reduction Phase",
                    body=f"Your 3-week rolling distance has decreased approximately {abs(pct_change):.0f}% over the observed period. If intentional (taper or recovery), this is expected. The Aerobic Base driver may reflect this shift.",
                    status="observational",
                    confidence=0.6,
                    data_points=len(distances),
                ))

        return insights

    @staticmethod
    def _detect_intensity_patterns(history: list[dict]) -> list[Insight]:
        """Detect intensity distribution patterns."""
        insights = []

        z4_values = [h.get("z4_pct") for h in history if h.get("z4_pct") is not None]
        z5_values = [h.get("z5_pct") for h in history if h.get("z5_pct") is not None]

        if len(z4_values) >= 3:
            avg_z4 = np.mean(z4_values)
            if avg_z4 > 0.15:
                insights.append(Insight(
                    category="trend",
                    title="High Threshold Density",
                    body=f"Your Zone 4 time averages {avg_z4*100:.0f}% of total training time, which is above the typical 10-12% range. This is contributing positively to the Threshold Density driver.",
                    status="emerging" if len(z4_values) >= 6 else "observational",
                    confidence=min(0.8, len(z4_values) / 8),
                    data_points=len(z4_values),
                ))
            elif avg_z4 < 0.05:
                insights.append(Insight(
                    category="trend",
                    title="Low Threshold Exposure",
                    body=f"Your Zone 4 time averages {avg_z4*100:.1f}% of total training — below the typical 10-12% range. The Threshold Density driver reflects this.",
                    status="observational",
                    confidence=0.6,
                    data_points=len(z4_values),
                ))

        if len(z5_values) >= 3:
            avg_z5 = np.mean(z5_values)
            if avg_z5 > 0.08:
                insights.append(Insight(
                    category="trend",
                    title="Significant Speed Work",
                    body=f"Your Zone 5 exposure averages {avg_z5*100:.1f}% of training time. The Speed Exposure driver is benefiting from this high-intensity work.",
                    status="observational",
                    confidence=0.6,
                    data_points=len(z5_values),
                ))

        return insights

    @staticmethod
    def _detect_risk_patterns(history: list[dict]) -> list[Insight]:
        """Detect risk patterns (high ACWR, overreaching signals)."""
        insights = []

        acwrs = [h.get("acwr_4w") for h in history if h.get("acwr_4w") is not None]

        if len(acwrs) >= 2:
            latest_acwr = acwrs[-1]
            if latest_acwr > 1.5:
                insights.append(Insight(
                    category="risk",
                    title="Elevated Training Load Ratio",
                    body=f"Your acute:chronic workload ratio is currently {latest_acwr:.2f}, which is in the elevated range (above 1.5). Research associates this zone with increased injury risk. The Event Readiness score reflects this.",
                    status="supported",
                    confidence=0.85,
                    data_points=len(acwrs),
                ))
            elif latest_acwr > 1.3:
                insights.append(Insight(
                    category="risk",
                    title="Rising Training Load Ratio",
                    body=f"Your ACWR is {latest_acwr:.2f}, approaching the upper boundary of the optimal zone (0.8-1.3). This is worth monitoring.",
                    status="observational",
                    confidence=0.7,
                    data_points=len(acwrs),
                ))

        return insights

    @staticmethod
    def _detect_response_patterns(
        features_history: list[dict],
        driver_history: list[dict],
    ) -> list[Insight]:
        """Detect which training patterns correlate with driver improvements."""
        insights = []

        if len(driver_history) < 3:
            return insights

        # Check if aerobic base improved when volume increased
        ab_values = [d.get("contribution_seconds", 0) for d in driver_history if d.get("driver_name") == "aerobic_base"]
        if len(ab_values) >= 3:
            first = np.mean(ab_values[:len(ab_values)//2])
            second = np.mean(ab_values[len(ab_values)//2:])

            if second > first and (second - first) > 1.0:
                distances = [h.get("rolling_distance_21d") for h in features_history if h.get("rolling_distance_21d") is not None]
                if distances and len(distances) >= 3:
                    dist_first = np.mean(distances[:len(distances)//2])
                    dist_second = np.mean(distances[len(distances)//2:])

                    if dist_second > dist_first:
                        insights.append(Insight(
                            category="response",
                            title="Volume-to-Aerobic Base Response",
                            body="Your Aerobic Base driver has been responding positively to increased training volume. The data shows a correlation between your rising 3-week distance and Aerobic Base contribution.",
                            status="emerging",
                            confidence=0.65,
                            data_points=len(ab_values),
                        ))

        return insights

    @staticmethod
    def generate_summary(insights: list[Insight]) -> dict:
        """Generate structured summary sections from insights.

        Returns 3 sections matching the PRD:
        - What Today Supports
        - What Is Defensible
        - What Needs Development
        """
        supported = [i for i in insights if i.status == "supported"]
        emerging = [i for i in insights if i.status == "emerging"]
        observational = [i for i in insights if i.status == "observational"]

        return {
            "what_today_supports": [
                {"title": i.title, "body": i.body, "confidence": i.confidence}
                for i in supported
            ],
            "what_is_defensible": [
                {"title": i.title, "body": i.body, "confidence": i.confidence}
                for i in emerging
            ],
            "what_needs_development": [
                {"title": i.title, "body": i.body, "confidence": i.confidence}
                for i in observational
            ],
        }
