"""What We're Learning About You — pattern detection module.

Uses real ML techniques for pattern detection:
- scipy.stats for Pearson/Spearman correlation between features and driver contributions
- sklearn.cluster.KMeans for training type classification (pyramidal/polarized/threshold/mixed)
- Statistical significance testing (p-values) for response patterns

Falls back to threshold-based heuristics when data is insufficient for ML methods.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

INTENSITY_FEATURES_FOR_CLUSTERING = ["z1_pct", "z2_pct", "z3_pct", "z4_pct", "z5_pct"]
TRAINING_TYPE_LABELS = {0: "Pyramidal", 1: "Polarized", 2: "Threshold-heavy", 3: "Mixed"}
MIN_SAMPLES_FOR_CORRELATION = 6
MIN_SAMPLES_FOR_CLUSTERING = 4


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

        Uses real correlation analysis and clustering when data is sufficient,
        falls back to threshold heuristics otherwise.
        """
        insights = []

        if len(features_history) < 2:
            return insights

        insights.extend(LearningModule._detect_consistency_patterns(features_history))
        insights.extend(LearningModule._detect_volume_trends(features_history))
        insights.extend(LearningModule._detect_intensity_patterns(features_history))
        insights.extend(LearningModule._detect_risk_patterns(features_history))
        insights.extend(LearningModule._classify_training_type(features_history))

        if driver_history and len(driver_history) >= 2:
            insights.extend(
                LearningModule._detect_response_patterns(features_history, driver_history)
            )

        insights.extend(
            LearningModule._detect_acwr_personal_threshold(features_history)
        )

        return insights

    @staticmethod
    def _classify_training_type(history: list[dict]) -> list[Insight]:
        """Classify training type using K-means clustering on intensity distribution."""
        insights = []

        zone_rows = []
        for h in history:
            row = []
            for f in INTENSITY_FEATURES_FOR_CLUSTERING:
                v = h.get(f)
                if v is None:
                    row.append(0.0)
                else:
                    fv = float(v)
                    row.append(0.0 if fv != fv else fv)
            if any(v > 0 for v in row):
                zone_rows.append(row)

        if len(zone_rows) < MIN_SAMPLES_FOR_CLUSTERING:
            return insights

        X = np.array(zone_rows, dtype=np.float64)

        n_clusters = min(4, len(zone_rows))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        centers = kmeans.cluster_centers_

        current_label = int(labels[-1])
        current_center = centers[current_label]

        z1z2_pct = float(current_center[0] + current_center[1])
        z3_pct = float(current_center[2])
        z4z5_pct = float(current_center[3] + current_center[4])

        if z1z2_pct > 0.75 and z3_pct < 0.05:
            training_type = "Polarized"
        elif z1z2_pct > 0.75:
            training_type = "Pyramidal"
        elif z1z2_pct < 0.60 and z4z5_pct > 0.25:
            training_type = "Threshold-heavy"
        elif z4z5_pct > 0.20:
            training_type = "Threshold-heavy"
        else:
            training_type = "Mixed"

        recent_labels = labels[-min(4, len(labels)):]
        shifted = len(set(recent_labels)) > 1

        body = (
            f"Based on K-means clustering of your intensity distribution "
            f"(Z1-Z5 proportions across {len(zone_rows)} sessions), "
            f"your current training pattern classifies as {training_type} "
            f"(low-intensity: {z1z2_pct*100:.0f}%, high-intensity: {z4z5_pct*100:.0f}%)."
        )
        if shifted:
            body += " Your training type has shifted recently across multiple clusters."

        insights.append(Insight(
            category="trend",
            title=f"Training Classification: {training_type}",
            body=body,
            status="supported" if len(zone_rows) >= 8 else "emerging",
            confidence=min(0.9, len(zone_rows) / 12),
            data_points=len(zone_rows),
        ))

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
        """Detect feature-to-driver correlations using Pearson/Spearman statistics."""
        insights = []

        if len(driver_history) < MIN_SAMPLES_FOR_CORRELATION:
            return LearningModule._detect_response_patterns_heuristic(
                features_history, driver_history,
            )

        driver_features_map = {
            "aerobic_base": ["rolling_distance_7d", "rolling_distance_21d"],
            "threshold_density": ["threshold_density_min_week", "z4_pct"],
            "speed_exposure": ["speed_exposure_min_week", "z5_pct"],
            "running_economy": ["matched_hr_band_pace", "hr_drift_sustained"],
            "load_consistency": ["weekly_load_stddev", "acwr_4w"],
        }

        driver_by_date: dict[str, dict[str, float]] = {}
        for d in driver_history:
            name = d.get("driver_name")
            date_key = d.get("snapshot_date") or d.get("created_at", "")
            if isinstance(date_key, str):
                date_key = date_key[:10]
            if name:
                driver_by_date.setdefault(name, {})[date_key] = d.get("contribution_seconds", 0)

        features_by_date: dict[str, dict] = {}
        for f in features_history:
            date_key = f.get("snapshot_date") or f.get("created_at", "")
            if isinstance(date_key, str):
                date_key = date_key[:10]
            features_by_date[date_key] = f

        for driver_name, feature_keys in driver_features_map.items():
            date_map = driver_by_date.get(driver_name, {})
            if len(date_map) < MIN_SAMPLES_FOR_CORRELATION:
                continue

            for feat_key in feature_keys:
                paired_c = []
                paired_f = []
                for date_key, c_val in date_map.items():
                    feat_snap = features_by_date.get(date_key)
                    if feat_snap:
                        f_val = feat_snap.get(feat_key)
                        if f_val is not None:
                            paired_c.append(c_val)
                            paired_f.append(f_val)

                if len(paired_c) < MIN_SAMPLES_FOR_CORRELATION:
                    continue

                c_arr = np.array(paired_c, dtype=np.float64)
                f_arr = np.array(paired_f, dtype=np.float64)

                if np.std(c_arr) < 1e-10 or np.std(f_arr) < 1e-10:
                    continue

                r_pearson, p_pearson = stats.pearsonr(f_arr, c_arr)
                r_spearman, p_spearman = stats.spearmanr(f_arr, c_arr)

                if p_pearson < 0.05 and abs(r_pearson) > 0.4:
                    from app.ml.shap_explainer import FEATURE_DESCRIPTIONS, DRIVER_DISPLAY_NAMES
                    feat_desc = FEATURE_DESCRIPTIONS.get(feat_key, feat_key)
                    driver_desc = DRIVER_DISPLAY_NAMES.get(driver_name, driver_name)
                    direction = "positively" if r_pearson > 0 else "negatively"
                    n_paired = len(paired_c)

                    insights.append(Insight(
                        category="response",
                        title=f"{feat_desc} → {driver_desc} Response",
                        body=(
                            f"Your {driver_desc} responds {direction} to {feat_desc.lower()} "
                            f"(r={r_pearson:.2f}, p={p_pearson:.3f}, "
                            f"Spearman ρ={r_spearman:.2f}). "
                            f"This correlation is based on {n_paired} data points."
                        ),
                        status="supported" if p_pearson < 0.01 else "emerging",
                        confidence=min(0.95, abs(r_pearson)),
                        data_points=n_paired,
                    ))

        return insights

    @staticmethod
    def _detect_response_patterns_heuristic(
        features_history: list[dict],
        driver_history: list[dict],
    ) -> list[Insight]:
        """Heuristic fallback for response detection with insufficient data."""
        insights = []

        if len(driver_history) < 3:
            return insights

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
    def _detect_acwr_personal_threshold(history: list[dict]) -> list[Insight]:
        """Learn the user's personal ACWR danger zone using correlation analysis."""
        insights = []

        paired_acwr = []
        paired_perf = []
        for i in range(1, len(history)):
            acwr = history[i].get("acwr_4w")
            prev_dist = history[i - 1].get("rolling_distance_7d")
            curr_dist = history[i].get("rolling_distance_7d")
            if acwr is None or prev_dist is None or curr_dist is None or prev_dist <= 0:
                continue
            paired_acwr.append(acwr)
            paired_perf.append((curr_dist - prev_dist) / prev_dist)

        if len(paired_acwr) < MIN_SAMPLES_FOR_CORRELATION:
            return insights

        acwr_arr = np.array(paired_acwr, dtype=np.float64)
        perf_arr = np.array(paired_perf, dtype=np.float64)

        if np.std(acwr_arr) < 1e-10 or np.std(perf_arr) < 1e-10:
            return insights

        r, p = stats.pearsonr(acwr_arr, perf_arr)

        high_acwr_mask = acwr_arr > 1.3
        if high_acwr_mask.sum() >= 2:
            high_acwr_perfs = perf_arr[high_acwr_mask]
            if np.mean(high_acwr_perfs) < -0.05:
                threshold = float(np.min(acwr_arr[high_acwr_mask]))
                insights.append(Insight(
                    category="risk",
                    title="Personal ACWR Threshold Detected",
                    body=(
                        f"Your data suggests performance tends to drop when ACWR exceeds "
                        f"{threshold:.2f} (correlation r={r:.2f}, p={p:.3f}). "
                        f"This may differ from the generic 1.5 threshold."
                    ),
                    status="emerging" if p < 0.1 else "observational",
                    confidence=min(0.8, abs(r)),
                    data_points=len(paired_acwr),
                ))

        return insights

    @staticmethod
    def generate_summary(insights: list[Insight]) -> dict:
        """Generate structured summary sections from insights."""
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
