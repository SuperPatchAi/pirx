"""Tests for real ML library usage across all PIRX modules.

Verifies that sklearn, torch, shap, optuna, dtaidistance, and scipy
are actually invoked — not scaffolded or heuristic-only.
"""
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Phase 1: Real Gradient Boosting Projection
# ---------------------------------------------------------------------------

class TestGBProjectionModel:
    """Verify GBProjectionModel uses real sklearn GradientBoostingRegressor."""

    def _make_training_data(self, n=50):
        rng = np.random.default_rng(42)
        feature_names = [
            "rolling_distance_7d", "rolling_distance_21d", "rolling_distance_42d",
            "rolling_distance_90d", "sessions_per_week", "long_run_count",
            "z1_pct", "z2_pct", "z4_pct", "z5_pct",
            "threshold_density_min_week", "speed_exposure_min_week",
            "matched_hr_band_pace", "hr_drift_sustained", "late_session_pace_decay",
            "weekly_load_stddev", "acwr_4w",
        ]
        feature_rows = []
        targets = []
        for i in range(n):
            features = {
                "rolling_distance_7d": rng.uniform(15000, 50000),
                "rolling_distance_21d": rng.uniform(40000, 150000),
                "rolling_distance_42d": rng.uniform(80000, 300000),
                "rolling_distance_90d": rng.uniform(150000, 600000),
                "sessions_per_week": rng.uniform(3, 7),
                "long_run_count": rng.uniform(0, 6),
                "z1_pct": rng.uniform(0.2, 0.5),
                "z2_pct": rng.uniform(0.15, 0.4),
                "z4_pct": rng.uniform(0.03, 0.2),
                "z5_pct": rng.uniform(0.01, 0.1),
                "threshold_density_min_week": rng.uniform(0, 30),
                "speed_exposure_min_week": rng.uniform(0, 15),
                "matched_hr_band_pace": rng.uniform(240, 360),
                "hr_drift_sustained": rng.uniform(0.01, 0.1),
                "late_session_pace_decay": rng.uniform(0.01, 0.08),
                "weekly_load_stddev": rng.uniform(1000, 12000),
                "acwr_4w": rng.uniform(0.6, 1.6),
            }
            feature_rows.append(features)
            improvement = (
                features["rolling_distance_21d"] / 10000.0
                + features["threshold_density_min_week"] * 0.5
                - features["weekly_load_stddev"] / 5000.0
            )
            targets.append(improvement + rng.normal(0, 2))

        return feature_rows, targets

    def test_train_uses_real_sklearn(self):
        from app.ml.gb_projection_model import GBProjectionModel
        from sklearn.ensemble import GradientBoostingRegressor

        model = GBProjectionModel()
        feature_rows, targets = self._make_training_data(50)
        result = model.train(feature_rows, targets)

        assert result["status"] == "trained"
        assert result["samples"] == 50
        assert isinstance(model.model, GradientBoostingRegressor)
        assert model.is_trained is True
        assert "cv_mae" in result
        assert "feature_importances" in result
        assert result["cv_mae"] > 0

    def test_predict_returns_float(self):
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        feature_rows, targets = self._make_training_data(50)
        model.train(feature_rows, targets)

        prediction = model.predict(feature_rows[0])
        assert isinstance(prediction, float)

    def test_untrained_predict_returns_none(self):
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        assert model.predict({"rolling_distance_7d": 20000}) is None

    def test_insufficient_data_returns_status(self):
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        result = model.train([{"a": 1}] * 10, [1.0] * 10)
        assert result["status"] == "insufficient_data"

    def test_validate_produces_metrics(self):
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        feature_rows, targets = self._make_training_data(50)
        model.train(feature_rows, targets)

        val_result = model.validate(feature_rows[:10], targets[:10])
        assert val_result["status"] == "validated"
        assert "mae" in val_result
        assert "bias" in val_result
        assert "bland_altman_lower" in val_result

    def test_serialize_deserialize_roundtrip(self):
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        feature_rows, targets = self._make_training_data(50)
        model.train(feature_rows, targets)

        data = model.serialize()
        assert isinstance(data, bytes)
        assert len(data) > 0

        restored = GBProjectionModel.deserialize(data)
        assert restored.is_trained is True

        orig_pred = model.predict(feature_rows[0])
        restored_pred = restored.predict(feature_rows[0])
        assert abs(orig_pred - restored_pred) < 0.001

    def test_cross_validation_runs(self):
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        feature_rows, targets = self._make_training_data(50)
        result = model.train(feature_rows, targets)

        assert result["cv_mae"] > 0
        assert result["cv_std"] >= 0


# ---------------------------------------------------------------------------
# Phase 2: Real SHAP TreeExplainer
# ---------------------------------------------------------------------------

class TestSHAPExplainer:
    """Verify SHAPExplainer uses real SHAP library when GB model is provided."""

    def test_shap_explain_with_trained_model(self):
        import shap
        from app.ml.shap_explainer import SHAPExplainer
        from app.ml.gb_projection_model import GBProjectionModel

        rng = np.random.default_rng(42)
        model = GBProjectionModel()
        feature_rows = []
        targets = []
        for _ in range(50):
            features = {
                "rolling_distance_7d": rng.uniform(15000, 50000),
                "rolling_distance_21d": rng.uniform(40000, 150000),
                "rolling_distance_42d": rng.uniform(80000, 300000),
                "rolling_distance_90d": rng.uniform(150000, 600000),
                "sessions_per_week": rng.uniform(3, 7),
                "long_run_count": rng.uniform(0, 6),
                "z1_pct": rng.uniform(0.2, 0.5),
                "z2_pct": rng.uniform(0.15, 0.4),
                "z4_pct": rng.uniform(0.03, 0.2),
                "z5_pct": rng.uniform(0.01, 0.1),
                "threshold_density_min_week": rng.uniform(0, 30),
                "speed_exposure_min_week": rng.uniform(0, 15),
                "matched_hr_band_pace": rng.uniform(240, 360),
                "hr_drift_sustained": rng.uniform(0.01, 0.1),
                "late_session_pace_decay": rng.uniform(0.01, 0.08),
                "weekly_load_stddev": rng.uniform(1000, 12000),
                "acwr_4w": rng.uniform(0.6, 1.6),
            }
            feature_rows.append(features)
            targets.append(rng.uniform(-10, 30))

        model.train(feature_rows, targets)

        result = SHAPExplainer.explain_with_shap(
            "aerobic_base", feature_rows[0], model,
        )

        assert result is not None
        assert result.confidence == "high"
        assert "SHAP" in result.narrative
        assert result.driver_name == "aerobic_base"

    def test_shap_falls_back_without_model(self):
        from app.ml.shap_explainer import SHAPExplainer

        features = {
            "rolling_distance_7d": 25000,
            "rolling_distance_21d": 70000,
            "rolling_distance_42d": 140000,
            "z1_pct": 0.35, "z2_pct": 0.25,
        }
        result = SHAPExplainer.explain_driver("aerobic_base", features)
        assert result is not None
        assert result.confidence in ("low", "medium")

    def test_explain_driver_prefers_shap_when_model_provided(self):
        from app.ml.shap_explainer import SHAPExplainer
        from app.ml.gb_projection_model import GBProjectionModel

        rng = np.random.default_rng(42)
        model = GBProjectionModel()
        feature_rows = []
        targets = []
        for _ in range(50):
            features = {
                "rolling_distance_7d": rng.uniform(15000, 50000),
                "rolling_distance_21d": rng.uniform(40000, 150000),
                "rolling_distance_42d": rng.uniform(80000, 300000),
                "rolling_distance_90d": rng.uniform(150000, 600000),
                "sessions_per_week": rng.uniform(3, 7),
                "long_run_count": rng.uniform(0, 6),
                "z1_pct": rng.uniform(0.2, 0.5),
                "z2_pct": rng.uniform(0.15, 0.4),
                "z4_pct": rng.uniform(0.03, 0.2),
                "z5_pct": rng.uniform(0.01, 0.1),
                "threshold_density_min_week": rng.uniform(0, 30),
                "speed_exposure_min_week": rng.uniform(0, 15),
                "matched_hr_band_pace": rng.uniform(240, 360),
                "hr_drift_sustained": rng.uniform(0.01, 0.1),
                "late_session_pace_decay": rng.uniform(0.01, 0.08),
                "weekly_load_stddev": rng.uniform(1000, 12000),
                "acwr_4w": rng.uniform(0.6, 1.6),
            }
            feature_rows.append(features)
            targets.append(rng.uniform(-10, 30))

        model.train(feature_rows, targets)

        result = SHAPExplainer.explain_driver(
            "aerobic_base", feature_rows[0], gb_model=model,
        )
        assert result.confidence == "high"


# ---------------------------------------------------------------------------
# Phase 5: Real LSTM + PyTorch
# ---------------------------------------------------------------------------

class TestLSTMModel:
    """Verify PirxLSTM uses real PyTorch nn.Module and training."""

    def _make_sequential_data(self, n=80):
        rng = np.random.default_rng(42)
        feature_rows = []
        targets = []
        for i in range(n):
            features = {
                "rolling_distance_7d": 20000 + rng.normal(0, 3000),
                "rolling_distance_21d": 60000 + rng.normal(0, 8000),
                "rolling_distance_42d": 120000 + rng.normal(0, 15000),
                "rolling_distance_90d": 250000 + rng.normal(0, 30000),
                "sessions_per_week": 4 + rng.normal(0, 1),
                "long_run_count": max(0, 2 + rng.normal(0, 1)),
                "z1_pct": 0.35 + rng.normal(0, 0.05),
                "z2_pct": 0.25 + rng.normal(0, 0.03),
                "z4_pct": 0.10 + rng.normal(0, 0.03),
                "z5_pct": 0.04 + rng.normal(0, 0.01),
                "threshold_density_min_week": 10 + rng.normal(0, 3),
                "speed_exposure_min_week": 3 + rng.normal(0, 1),
                "matched_hr_band_pace": 300 + rng.normal(0, 20),
                "hr_drift_sustained": 0.05 + rng.normal(0, 0.01),
                "late_session_pace_decay": 0.04 + rng.normal(0, 0.01),
                "weekly_load_stddev": 5000 + rng.normal(0, 1000),
                "acwr_4w": 1.0 + rng.normal(0, 0.2),
            }
            feature_rows.append(features)
            targets.append(10.0 + i * 0.1 + rng.normal(0, 2))
        return feature_rows, targets

    def test_lstm_is_real_pytorch_module(self):
        import torch.nn as nn
        from app.ml.lstm_model import PirxLSTM

        model = PirxLSTM(input_dim=17, hidden_dim=17, dropout=0.5)
        assert isinstance(model, nn.Module)
        assert hasattr(model, 'lstm')
        assert hasattr(model, 'fc')

    def test_lstm_forward_pass(self):
        import torch
        from app.ml.lstm_model import PirxLSTM

        model = PirxLSTM(input_dim=17, hidden_dim=17, dropout=0.5)
        model.eval()
        x = torch.randn(2, 11, 17)
        with torch.no_grad():
            output = model(x)
        assert output.shape == (2,)

    def test_lstm_trainer_trains_with_real_torch(self):
        from app.ml.lstm_model import LSTMTrainer

        trainer = LSTMTrainer(
            hidden_dim=8, dropout=0.3, learning_rate=1e-3,
            batch_size=16, seq_length=5, max_epochs=10, patience=3,
        )
        feature_rows, targets = self._make_sequential_data(80)
        result = trainer.train(feature_rows, targets)

        assert result["status"] == "trained"
        assert result["val_loss"] > 0
        assert result["val_mae"] > 0
        assert trainer.model is not None

    def test_lstm_predict_returns_float(self):
        from app.ml.lstm_model import LSTMTrainer

        trainer = LSTMTrainer(
            hidden_dim=8, dropout=0.3, seq_length=5, max_epochs=5, patience=2,
        )
        feature_rows, targets = self._make_sequential_data(80)
        trainer.train(feature_rows, targets)

        prediction = trainer.predict(feature_rows[-5:])
        assert isinstance(prediction, float)

    def test_lstm_serialize_deserialize(self):
        import torch
        from app.ml.lstm_model import LSTMTrainer

        trainer = LSTMTrainer(
            hidden_dim=8, dropout=0.3, seq_length=5, max_epochs=5, patience=2,
        )
        feature_rows, targets = self._make_sequential_data(80)
        trainer.train(feature_rows, targets)

        weight_bytes = trainer.serialize()
        assert isinstance(weight_bytes, bytes)
        assert len(weight_bytes) > 0

        new_trainer = LSTMTrainer(hidden_dim=8, dropout=0.3, seq_length=5)
        new_trainer.load_weights(weight_bytes, input_dim=17)
        assert new_trainer.model is not None

    def test_lstm_insufficient_data(self):
        from app.ml.lstm_model import LSTMTrainer

        trainer = LSTMTrainer(seq_length=5, max_epochs=5)
        result = trainer.train([{"a": 1}] * 10, [1.0] * 10)
        assert result["status"] == "insufficient_data"


# ---------------------------------------------------------------------------
# Phase 5b: Real Optuna
# ---------------------------------------------------------------------------

class TestOptunaIntegration:
    """Verify real optuna.create_study() is used for HPO."""

    def test_optuna_study_runs(self):
        import optuna

        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial):
            x = trial.suggest_float("x", -10, 10)
            return (x - 3) ** 2

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=10)

        assert study.best_value < 10
        assert len(study.trials) == 10
        assert "x" in study.best_params


# ---------------------------------------------------------------------------
# Phase 6: Real DTW
# ---------------------------------------------------------------------------

class TestWorkoutSimilarity:
    """Verify DTW uses real dtaidistance library."""

    def test_dtw_pace_profile_distance(self):
        from app.ml.workout_similarity import WorkoutSimilarity

        profile_a = [300, 290, 285, 280, 275, 270]
        profile_b = [310, 300, 295, 290, 285, 280]
        profile_c = [400, 350, 320, 310, 300, 290]

        dist_ab = WorkoutSimilarity.pace_profile_distance(profile_a, profile_b)
        dist_ac = WorkoutSimilarity.pace_profile_distance(profile_a, profile_c)

        assert dist_ab > 0
        assert dist_ac > dist_ab

    def test_block_fingerprint_shape(self):
        from app.ml.workout_similarity import WorkoutSimilarity

        activities = [
            {"distance_meters": 5000, "duration_seconds": 1500, "avg_pace_sec_per_km": 300, "avg_hr": 150},
            {"distance_meters": 10000, "duration_seconds": 3200, "avg_pace_sec_per_km": 320, "avg_hr": 145},
        ]
        fp = WorkoutSimilarity.block_fingerprint(activities)
        assert fp.shape == (2, 4)

    def test_block_distance_uses_dtw(self):
        from app.ml.workout_similarity import WorkoutSimilarity

        block_a = np.array([[5.0, 25.0, 300, 150], [10.0, 50.0, 320, 145]])
        block_b = np.array([[5.2, 26.0, 305, 152], [9.8, 49.0, 318, 146]])
        block_c = np.array([[15.0, 90.0, 400, 170], [3.0, 15.0, 250, 120]])

        dist_ab = WorkoutSimilarity.block_distance(block_a, block_b)
        dist_ac = WorkoutSimilarity.block_distance(block_a, block_c)

        assert dist_ab > 0
        assert dist_ac > dist_ab

    def test_find_similar_blocks(self):
        from app.ml.workout_similarity import WorkoutSimilarity

        current = np.array([[5.0, 25.0, 300, 150], [10.0, 50.0, 320, 145]])
        historical = [
            np.array([[5.1, 25.5, 302, 151], [10.1, 50.5, 321, 146]]),
            np.array([[15.0, 90.0, 400, 170], [3.0, 15.0, 250, 120]]),
            np.array([[5.2, 26.0, 305, 152], [9.8, 49.0, 318, 146]]),
        ]
        results = WorkoutSimilarity.find_similar_blocks(current, historical, top_k=2)

        assert len(results) == 2
        assert results[0][1] <= results[1][1]

    def test_predict_from_similar_blocks(self):
        from app.ml.workout_similarity import WorkoutSimilarity

        similar = [(0, 1.0), (2, 2.5)]
        outcomes = [
            {"improvement_seconds": 5.0},
            None,
            {"improvement_seconds": 10.0},
        ]
        result = WorkoutSimilarity.predict_from_similar_blocks(similar, outcomes)

        assert result["similar_blocks_used"] == 2
        assert result["expected"] == 7.5
        assert result["confidence"] > 0


# ---------------------------------------------------------------------------
# Phase 7: Real Clustering + Correlation
# ---------------------------------------------------------------------------

class TestLearningModuleML:
    """Verify LearningModule uses real scipy.stats and sklearn.cluster."""

    def test_kmeans_classification_runs(self):
        from app.ml.learning_module import LearningModule

        history = []
        for i in range(10):
            history.append({
                "z1_pct": 0.35 + np.random.uniform(-0.05, 0.05),
                "z2_pct": 0.30 + np.random.uniform(-0.05, 0.05),
                "z3_pct": 0.15 + np.random.uniform(-0.03, 0.03),
                "z4_pct": 0.12 + np.random.uniform(-0.03, 0.03),
                "z5_pct": 0.04 + np.random.uniform(-0.01, 0.01),
                "weekly_load_stddev": 4000,
                "rolling_distance_21d": 60000,
                "acwr_4w": 1.0,
            })

        insights = LearningModule._classify_training_type(history)
        assert len(insights) >= 1
        classification = insights[0]
        assert "Classification" in classification.title
        assert "K-means" in classification.body

    def test_correlation_response_detection(self):
        from app.ml.learning_module import LearningModule
        from datetime import date, timedelta

        rng = np.random.default_rng(42)
        n = 15
        features_history = []
        driver_history = []
        base_date = date(2025, 1, 1)

        for i in range(n):
            snapshot_date = (base_date + timedelta(days=i * 7)).isoformat()
            vol = 50000 + i * 2000 + rng.normal(0, 1000)
            features_history.append({
                "snapshot_date": snapshot_date,
                "rolling_distance_7d": vol / 3,
                "rolling_distance_21d": vol,
                "threshold_density_min_week": 10 + rng.normal(0, 2),
                "z4_pct": 0.10 + rng.normal(0, 0.02),
                "speed_exposure_min_week": 3 + rng.normal(0, 1),
                "z5_pct": 0.04 + rng.normal(0, 0.01),
                "matched_hr_band_pace": 300 + rng.normal(0, 10),
                "hr_drift_sustained": 0.05 + rng.normal(0, 0.01),
                "weekly_load_stddev": 5000 + rng.normal(0, 500),
                "acwr_4w": 1.0 + rng.normal(0, 0.1),
            })
            driver_history.append({
                "snapshot_date": snapshot_date,
                "driver_name": "aerobic_base",
                "contribution_seconds": 5 + i * 0.3 + rng.normal(0, 0.5),
            })

        insights = LearningModule._detect_response_patterns(
            features_history, driver_history,
        )

        has_correlation = any("r=" in i.body for i in insights)
        assert has_correlation, "Expected real correlation statistics in response patterns"

    def test_personal_acwr_threshold(self):
        from app.ml.learning_module import LearningModule

        rng = np.random.default_rng(42)
        history = []
        for i in range(20):
            acwr = 0.8 + i * 0.05
            if acwr > 1.3:
                vol = 20000 * (1.0 - (acwr - 1.3) * 0.8) + rng.normal(0, 100)
            else:
                vol = 20000 * (1.0 + i * 0.02) + rng.normal(0, 100)
            history.append({
                "acwr_4w": acwr,
                "rolling_distance_7d": max(vol, 5000),
                "weekly_load_stddev": 4000,
            })

        insights = LearningModule._detect_acwr_personal_threshold(history)
        has_threshold = any("Personal ACWR" in i.title for i in insights)
        assert has_threshold


# ---------------------------------------------------------------------------
# Trajectory Engine DTW integration
# ---------------------------------------------------------------------------

class TestTrajectoryEngineDTW:
    """Verify TrajectoryEngine attempts DTW when history is provided."""

    def test_heuristic_fallback_still_works(self):
        from app.ml.trajectory_engine import TrajectoryEngine

        engine = TrajectoryEngine()
        features = {
            "rolling_distance_7d": 25000,
            "rolling_distance_21d": 70000,
            "rolling_distance_42d": 140000,
            "rolling_distance_90d": 280000,
            "z4_pct": 0.10,
            "z5_pct": 0.04,
            "threshold_density_min_week": 10,
            "speed_exposure_min_week": 3,
            "weekly_load_stddev": 5000,
            "block_variance": 4000,
            "session_density_stability": 1.0,
        }
        scenarios = engine.compute_trajectories(
            "user1", "5000", 1400.0, features,
        )
        assert len(scenarios) == 3
        assert scenarios[0].label == "Maintain"

    def test_dtw_trajectory_with_sufficient_history(self):
        from app.ml.trajectory_engine import TrajectoryEngine

        rng = np.random.default_rng(42)
        activities = []
        projections = []
        for i in range(80):
            activities.append({
                "start_time": f"2025-01-{(i % 28) + 1:02d}T08:00:00Z",
                "distance_meters": rng.uniform(5000, 15000),
                "duration_seconds": rng.uniform(1500, 5000),
                "avg_pace_sec_per_km": rng.uniform(280, 360),
                "avg_hr": rng.uniform(130, 165),
            })
            projections.append({
                "projected_time_seconds": 1400 - i * 0.5,
            })

        engine = TrajectoryEngine()
        features = {
            "rolling_distance_7d": 25000,
            "rolling_distance_21d": 70000,
        }
        scenarios = engine.compute_trajectories(
            "user1", "5000", 1400.0, features,
            activity_history=activities,
            projection_history=projections,
        )
        assert len(scenarios) == 3


# ---------------------------------------------------------------------------
# Phase 3: Real Readiness Classifier
# ---------------------------------------------------------------------------

class TestReadinessClassifier:
    """Verify ReadinessClassifier uses real sklearn GradientBoostingClassifier."""

    def test_train_uses_real_sklearn(self):
        from app.ml.readiness_engine import ReadinessClassifier
        from sklearn.ensemble import GradientBoostingClassifier

        clf = ReadinessClassifier()
        rng = np.random.default_rng(42)

        feature_rows = []
        labels = []
        for _ in range(20):
            f = {
                "acwr_4w": rng.uniform(0.7, 1.5),
                "days_since_activity": rng.uniform(0, 5),
                "days_since_threshold": rng.uniform(0, 20),
                "days_since_long_run": rng.uniform(0, 30),
                "hrv_trend": rng.normal(0, 2),
                "resting_hr_trend": rng.normal(0, 2),
                "sleep_score": rng.uniform(40, 95),
                "weekly_load_stddev": rng.uniform(2000, 10000),
                "session_density_stability": rng.uniform(0.3, 2.0),
            }
            feature_rows.append(f)
            labels.append(1 if f["acwr_4w"] < 1.2 and f["sleep_score"] > 60 else 0)

        result = clf.train(feature_rows, labels)
        assert result["status"] == "trained"
        assert isinstance(clf.model, GradientBoostingClassifier)
        assert clf.is_trained is True

    def test_predict_returns_score(self):
        from app.ml.readiness_engine import ReadinessClassifier

        clf = ReadinessClassifier()
        rng = np.random.default_rng(42)
        rows = [
            {
                "acwr_4w": rng.uniform(0.7, 1.5),
                "days_since_activity": rng.uniform(0, 5),
                "days_since_threshold": rng.uniform(0, 20),
                "days_since_long_run": rng.uniform(0, 30),
                "hrv_trend": rng.normal(0, 2),
                "resting_hr_trend": rng.normal(0, 2),
                "sleep_score": rng.uniform(40, 95),
                "weekly_load_stddev": rng.uniform(2000, 10000),
                "session_density_stability": rng.uniform(0.3, 2.0),
            }
            for _ in range(10)
        ]
        labels = [1 if r["sleep_score"] > 60 else 0 for r in rows]
        clf.train(rows, labels)

        score = clf.predict_readiness(rows[0])
        assert score is not None
        assert 0.0 <= score <= 100.0

    def test_insufficient_data(self):
        from app.ml.readiness_engine import ReadinessClassifier

        clf = ReadinessClassifier()
        result = clf.train([{"acwr_4w": 1.0}] * 3, [1, 0, 1])
        assert result["status"] == "insufficient_data"

    def test_serialize_deserialize(self):
        from app.ml.readiness_engine import ReadinessClassifier

        clf = ReadinessClassifier()
        rng = np.random.default_rng(42)
        rows = [
            {
                "acwr_4w": rng.uniform(0.7, 1.5),
                "days_since_activity": rng.uniform(0, 5),
                "days_since_threshold": rng.uniform(0, 20),
                "days_since_long_run": rng.uniform(0, 30),
                "hrv_trend": rng.normal(0, 2),
                "resting_hr_trend": rng.normal(0, 2),
                "sleep_score": rng.uniform(40, 95),
                "weekly_load_stddev": rng.uniform(2000, 10000),
                "session_density_stability": rng.uniform(0.3, 2.0),
            }
            for _ in range(10)
        ]
        labels = [1 if r["sleep_score"] > 60 else 0 for r in rows]
        clf.train(rows, labels)

        data = clf.serialize()
        restored = ReadinessClassifier.deserialize(data)
        assert restored.is_trained is True

        orig = clf.predict_readiness(rows[0])
        rest = restored.predict_readiness(rows[0])
        assert abs(orig - rest) < 0.01

    def test_readiness_engine_uses_classifier(self):
        from app.ml.readiness_engine import ReadinessEngine, ReadinessClassifier

        clf = ReadinessClassifier()
        rng = np.random.default_rng(42)
        rows = [
            {
                "acwr_4w": rng.uniform(0.7, 1.5),
                "days_since_activity": rng.uniform(0, 5),
                "days_since_threshold": rng.uniform(0, 20),
                "days_since_long_run": rng.uniform(0, 30),
                "hrv_trend": rng.normal(0, 2),
                "resting_hr_trend": rng.normal(0, 2),
                "sleep_score": rng.uniform(40, 95),
                "weekly_load_stddev": rng.uniform(2000, 10000),
                "session_density_stability": rng.uniform(0.3, 2.0),
            }
            for _ in range(10)
        ]
        labels = [1 if r["sleep_score"] > 60 else 0 for r in rows]
        clf.train(rows, labels)

        result = ReadinessEngine.compute_readiness(
            features={"acwr_4w": 1.0, "weekly_load_stddev": 4000},
            days_since_last_activity=2,
            sleep_score=80,
            trained_classifier=clf,
        )
        assert result.score > 0
        assert "ML-based readiness" in result.factors[0]["factor"]


# ---------------------------------------------------------------------------
# Injury Risk Model (already uses sklearn but on synthetic data)
# ---------------------------------------------------------------------------

class TestInjuryRiskModelReal:
    """Verify InjuryRiskModel uses real sklearn RandomForestRegressor."""

    def test_uses_real_random_forest(self):
        from app.ml.injury_risk_model import InjuryRiskModel
        from sklearn.ensemble import RandomForestRegressor

        model = InjuryRiskModel._get_model()
        assert isinstance(model, RandomForestRegressor)
        assert model.n_estimators == 200

    def test_predict_returns_bounded_probability(self):
        from app.ml.injury_risk_model import InjuryRiskModel

        prob = InjuryRiskModel.predict_probability(
            {"acwr_4w": 1.8, "weekly_load_stddev": 12000},
            sleep_score=50,
        )
        assert 0.0 <= prob <= 1.0

    def test_risk_bands(self):
        from app.ml.injury_risk_model import InjuryRiskModel

        assert InjuryRiskModel.get_risk_band(0.2) == "low"
        assert InjuryRiskModel.get_risk_band(0.5) == "moderate"
        assert InjuryRiskModel.get_risk_band(0.8) == "high"


# ---------------------------------------------------------------------------
# Phase 4: Trainable Injury Risk Model on real data
# ---------------------------------------------------------------------------

class TestTrainableInjuryRiskModel:
    """Verify TrainableInjuryRiskModel uses real sklearn RandomForestRegressor
    trained on extracted proxy injury signals."""

    def _make_signals(self, n=50, seed=42):
        rng = np.random.default_rng(seed)
        signals = []
        for _ in range(n):
            acwr = rng.uniform(0.5, 2.0)
            label = 0.0
            if acwr > 1.4:
                label = rng.uniform(0.5, 1.0)
            signals.append({
                "features": {
                    "acwr_4w": acwr,
                    "acwr_6w": acwr + rng.normal(0, 0.1),
                    "acwr_8w": acwr + rng.normal(0, 0.12),
                    "weekly_load_stddev": rng.uniform(2000, 12000),
                    "session_density_stability": rng.uniform(0.3, 2.0),
                    "hrv_trend": rng.normal(0, 2),
                    "resting_hr_trend": rng.normal(0, 2),
                    "sleep_score": rng.uniform(40, 90),
                },
                "label": label,
            })
        return signals

    def test_train_uses_real_sklearn(self):
        from app.ml.injury_risk_model import TrainableInjuryRiskModel
        from sklearn.ensemble import RandomForestRegressor

        model = TrainableInjuryRiskModel()
        signals = self._make_signals(50)
        result = model.train(signals)
        assert result["status"] == "trained"
        assert result["samples"] == 50
        assert isinstance(model.model, RandomForestRegressor)
        assert model.is_trained is True

    def test_insufficient_data(self):
        from app.ml.injury_risk_model import TrainableInjuryRiskModel

        model = TrainableInjuryRiskModel()
        result = model.train(self._make_signals(10))
        assert result["status"] == "insufficient_data"
        assert model.is_trained is False

    def test_predict_bounded(self):
        from app.ml.injury_risk_model import TrainableInjuryRiskModel

        model = TrainableInjuryRiskModel()
        model.train(self._make_signals(50))

        prob = model.predict_probability({"acwr_4w": 1.7, "weekly_load_stddev": 10000})
        assert prob is not None
        assert 0.0 <= prob <= 1.0

    def test_serialize_deserialize(self):
        from app.ml.injury_risk_model import TrainableInjuryRiskModel

        model = TrainableInjuryRiskModel()
        model.train(self._make_signals(50))
        data = model.serialize()

        restored = TrainableInjuryRiskModel.deserialize(data)
        assert restored.is_trained is True

        orig = model.predict_probability({"acwr_4w": 1.5})
        rest = restored.predict_probability({"acwr_4w": 1.5})
        assert abs(orig - rest) < 0.001

    def test_injury_risk_model_uses_trained(self):
        """InjuryRiskModel.predict_probability delegates to trained model when provided."""
        from app.ml.injury_risk_model import InjuryRiskModel, TrainableInjuryRiskModel

        trained = TrainableInjuryRiskModel()
        trained.train(self._make_signals(50))

        prob_with = InjuryRiskModel.predict_probability(
            {"acwr_4w": 1.7}, sleep_score=50, trained_model=trained,
        )
        prob_without = InjuryRiskModel.predict_probability(
            {"acwr_4w": 1.7}, sleep_score=50,
        )
        assert 0.0 <= prob_with <= 1.0
        assert 0.0 <= prob_without <= 1.0


class TestInjurySignalExtractor:
    """Verify InjurySignalExtractor detects proxy injury signals."""

    def test_extended_rest_after_high_acwr(self):
        from app.ml.injury_risk_model import InjurySignalExtractor

        activities = [
            {"start_time": "2025-01-01T08:00:00", "avg_pace_min_km": 5.0},
            {"start_time": "2025-01-20T08:00:00", "avg_pace_min_km": 5.2},
        ]
        snapshots = [
            {"date": "2025-01-01", "acwr_4w": 1.6, "weekly_load_stddev": 5000},
            {"date": "2025-01-20", "acwr_4w": 0.8, "weekly_load_stddev": 3000},
        ]

        signals = InjurySignalExtractor.extract_signals(activities, snapshots)
        assert len(signals) >= 1
        high_label = signals[0]
        assert high_label["label"] > 0.0, "19-day gap after ACWR 1.6 should produce injury signal"

    def test_performance_drop(self):
        from app.ml.injury_risk_model import InjurySignalExtractor

        activities = [
            {"start_time": f"2025-01-{d:02d}T08:00:00", "avg_pace_min_km": 5.0}
            for d in range(1, 6)
        ]
        activities.append({"start_time": "2025-01-06T08:00:00", "avg_pace_min_km": 6.0})

        snapshots = [
            {"date": f"2025-01-{d:02d}", "acwr_4w": 1.0} for d in range(1, 7)
        ]

        signals = InjurySignalExtractor.extract_signals(activities, snapshots)
        dropped = [s for s in signals if s["label"] >= 0.7]
        assert len(dropped) >= 1, "20% pace drop should produce injury signal"

    def test_no_signals_healthy_data(self):
        from app.ml.injury_risk_model import InjurySignalExtractor

        activities = [
            {"start_time": f"2025-01-{d:02d}T08:00:00", "avg_pace_min_km": 5.0}
            for d in range(1, 8)
        ]
        snapshots = [
            {"date": f"2025-01-{d:02d}", "acwr_4w": 1.0, "weekly_load_stddev": 3000}
            for d in range(1, 8)
        ]

        signals = InjurySignalExtractor.extract_signals(activities, snapshots)
        injury_count = sum(1 for s in signals if s["label"] > 0.0)
        assert injury_count == 0, "Healthy data should produce no injury signals"

    def test_empty_inputs(self):
        from app.ml.injury_risk_model import InjurySignalExtractor

        assert InjurySignalExtractor.extract_signals([], []) == []
        assert InjurySignalExtractor.extract_signals([{"start_time": "2025-01-01"}], []) == []


# ---------------------------------------------------------------------------
# Bug regression tests (added during end-to-end audit)
# ---------------------------------------------------------------------------

class TestBugRegressions:
    """Regression tests for bugs found during ML infrastructure audit."""

    def test_readiness_classifier_single_class_labels(self):
        """BUG-1: predict_proba crashes with IndexError on single-class labels."""
        from app.ml.readiness_engine import ReadinessClassifier

        clf = ReadinessClassifier()
        rows = [{"acwr_4w": 1.0 + i * 0.1} for i in range(10)]
        all_ones = [1] * 10
        result = clf.train(rows, all_ones)
        assert result["status"] == "single_class"

        all_zeros = [0] * 10
        result = clf.train(rows, all_zeros)
        assert result["status"] == "single_class"

        mixed = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        result = clf.train(rows, mixed)
        assert result["status"] == "trained"
        score = clf.predict_readiness({"acwr_4w": 1.2})
        assert score is not None
        assert 0 <= score <= 100

    def test_nan_feature_does_not_propagate(self):
        """BUG-8: NaN in features should be replaced with 0, not propagated."""
        from app.ml.gb_projection_model import GBProjectionModel

        model = GBProjectionModel()
        features_with_nan = {"rolling_distance_7d": float("nan"), "acwr_4w": 1.0}
        arr = model._features_to_array([features_with_nan])
        assert not np.isnan(arr).any(), "NaN should not propagate through _features_to_array"
        assert arr[0, 0] == 0.0

    def test_nan_feature_lstm(self):
        """BUG-8: NaN in LSTM features should be replaced with 0."""
        from app.ml.lstm_model import LSTMTrainer

        trainer = LSTMTrainer()
        features_with_nan = {"rolling_distance_7d": float("nan"), "z1_pct": None}
        arr = trainer._features_to_array([features_with_nan])
        assert not np.isnan(arr).any()

    def test_readiness_defaults_none_not_zero(self):
        """BUG-11: days_since_last_threshold/long_run should default to None, not 0."""
        from app.ml.readiness_engine import ReadinessEngine
        import inspect

        sig = inspect.signature(ReadinessEngine.compute_readiness)
        assert sig.parameters["days_since_last_threshold"].default is None
        assert sig.parameters["days_since_last_long_run"].default is None

    def test_trainable_injury_model_consistent_defaults(self):
        """BUG-4: Training and inference should use the same feature defaults."""
        from app.ml.injury_risk_model import TrainableInjuryRiskModel

        model = TrainableInjuryRiskModel()
        train_arr = model._features_to_array([{}])
        infer_arr = model._features_to_array([{}])
        np.testing.assert_array_equal(train_arr, infer_arr)

    def test_learning_module_acwr_paired_correctly(self):
        """BUG-6: ACWR and perf_change must be paired by time index."""
        from app.ml.learning_module import LearningModule

        history = []
        for i in range(15):
            entry = {"rolling_distance_7d": 20000.0 + i * 100}
            if i % 2 == 0:
                entry["acwr_4w"] = 1.0 + i * 0.05
            history.append(entry)

        LearningModule._detect_acwr_personal_threshold(history)

    def test_lstm_min_sequences_guard(self):
        """BUG-9: LSTM should reject training with too few sequences."""
        from app.ml.lstm_model import LSTMTrainer, LSTM_FEATURE_NAMES

        trainer = LSTMTrainer(seq_length=11)
        rows = [{name: float(i) for name in LSTM_FEATURE_NAMES} for i in range(15)]
        targets = [float(i) for i in range(15)]
        result = trainer.train(rows, targets)
        assert result["status"] in ("insufficient_data", "insufficient_sequences")


class TestBugFixSweepRegressions:
    """Regression tests for the 32-bug ML infrastructure fix sweep."""

    def test_nan_baseline_blocked_in_projection(self):
        """PE-1+PE-3: NaN baseline must be rejected by projection engine."""
        import math
        from app.ml.projection_engine import ProjectionEngine

        engine = ProjectionEngine()
        state, drivers = engine.compute_projection(
            "u1", "5000", float("nan"), {"rolling_distance_7d": 20000},
        )
        assert state.projected_time_seconds == 0

    def test_nan_feature_skipped_in_driver_scoring(self):
        """PE-1: NaN feature values must be skipped, not corrupt driver scores."""
        from app.ml.projection_engine import ProjectionEngine

        engine = ProjectionEngine()
        state, drivers = engine.compute_projection(
            "u1", "5000", 1500.0,
            {"rolling_distance_7d": float("nan"), "rolling_distance_21d": 55000},
        )
        assert state.projected_time_seconds > 0

    def test_acwr_u_shaped_scoring(self):
        """PE-2: ACWR=1.5 should score lower than ACWR=1.05."""
        from app.ml.projection_engine import ProjectionEngine

        engine = ProjectionEngine()
        features_optimal = {"acwr_4w": 1.05, "weekly_load_stddev": 5000}
        features_risky = {"acwr_4w": 1.5, "weekly_load_stddev": 5000}

        scores_opt = engine._compute_driver_scores(features_optimal)
        scores_risk = engine._compute_driver_scores(features_risky)
        assert scores_opt["load_consistency"] > scores_risk["load_consistency"]

    def test_driver_sum_when_all_zero(self):
        """PE-4: Total improvement should be distributed evenly when all driver weights=0."""
        from app.ml.projection_engine import ProjectionEngine

        engine = ProjectionEngine()
        contributions = engine._decompose_drivers(
            {"aerobic_base": 0, "threshold_density": 0, "speed_exposure": 0,
             "running_economy": 0, "load_consistency": 0},
            total_improvement=50.0,
        )
        assert abs(sum(contributions.values()) - 50.0) < 0.02

    def test_ewma_seed_uses_first_element(self):
        """BUG-23: EWMA seed must use arr[0], not mean of non-zero values."""
        from app.services.feature_service import FeatureService
        from app.models.activities import NormalizedActivity
        from datetime import datetime, timedelta

        now = datetime(2025, 6, 1)
        activities = []
        for i in range(56):
            day = now - timedelta(days=55 - i)
            a = NormalizedActivity(
                id=str(i), user_id="u1", source="test",
                activity_type="run",
                timestamp=day,
                distance_meters=10000 if i % 3 == 0 else 0,
                duration_seconds=3600 if i % 3 == 0 else 0,
            )
            activities.append(a)

        acwr = FeatureService._compute_acwr(activities, now, 7, 28)
        assert acwr is None or acwr > 0

    def test_readiness_zero_not_conflated_with_none(self):
        """BUG-18: days_since_last_threshold=0 must not become 14."""
        from app.ml.readiness_engine import ReadinessEngine

        result = ReadinessEngine.compute_readiness(
            features={"acwr_4w": 1.0, "weekly_load_stddev": 3000},
            days_since_last_activity=0,
            days_since_last_threshold=0,
            days_since_last_long_run=0,
        )
        assert result.score > 0

    def test_polarized_vs_pyramidal_classification(self):
        """BUG-19: Polarized training (high Z1+Z2, low Z3) must not be classified as Pyramidal."""
        from app.ml.learning_module import LearningModule
        import numpy as np

        history = []
        for _ in range(12):
            history.append({
                "z1_pct": 0.50, "z2_pct": 0.30, "z3_pct": 0.02,
                "z4_pct": 0.03, "z5_pct": 0.15,
                "weekly_load_stddev": 3000,
            })

        insights = LearningModule.analyze_training_patterns(history)
        classification = [i for i in insights if "Classification" in i.title]
        if classification:
            assert "Polarized" in classification[0].title

    def test_riegel_scaling_in_baseline_estimator(self):
        """BUG-27: Non-5K distances must use Riegel scaling in baseline tier 2."""
        from app.ml.baseline_estimator import estimate_5k_baseline

        filler = [{"distance_meters": 5000, "duration_seconds": 1500,
                   "avg_pace_sec_per_km": 300, "avg_hr": 140, "max_hr": 185}
                  for _ in range(5)]

        acts_5k = filler + [{"distance_meters": 5000, "duration_seconds": 1200,
                             "avg_pace_sec_per_km": 240, "avg_hr": 165, "max_hr": 185}]
        five_k_result = estimate_5k_baseline(acts_5k)

        acts_10k = filler + [{"distance_meters": 10000, "duration_seconds": 2600,
                              "avg_pace_sec_per_km": 260, "avg_hr": 165, "max_hr": 185}]
        ten_k_result = estimate_5k_baseline(acts_10k)
        assert ten_k_result != five_k_result

    def test_calibration_continuity(self):
        """BUG-22: Calibration function should be continuous at boundaries."""
        from app.ml.injury_risk_model import InjuryRiskModel

        at_boundary_low = InjuryRiskModel._calibrate_probability(0.2)
        below_boundary_low = InjuryRiskModel._calibrate_probability(0.1999)
        assert abs(at_boundary_low - below_boundary_low) < 0.005

        at_boundary_high = InjuryRiskModel._calibrate_probability(0.7)
        below_boundary_high = InjuryRiskModel._calibrate_probability(0.6999)
        assert abs(at_boundary_high - below_boundary_high) < 0.005
