from unittest.mock import MagicMock, patch

from app.tasks.ml_tasks import train_user_lstm, tune_user_lstm, train_user_gb


class TestMlTasks:
    @patch("app.services.supabase_client.SupabaseService")
    def test_train_user_lstm_no_data(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = []

        result = train_user_lstm("u1")
        assert result["status"] == "no_data"
        assert result["user_id"] == "u1"

    @patch("app.tasks.ml_tasks._build_gb_training_data")
    @patch("app.services.supabase_client.SupabaseService")
    def test_train_user_lstm_insufficient_data(self, mock_svc_cls, mock_build):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"id": i} for i in range(70)]
        mock_build.return_value = ([{"a": 1}] * 10, [1.0] * 10)

        result = train_user_lstm("u1")
        assert result["status"] == "no_data"

    @patch("app.ml.lstm_model.LSTMTrainer")
    @patch("app.tasks.ml_tasks._build_gb_training_data")
    @patch("app.services.supabase_client.SupabaseService")
    def test_train_user_lstm_logs_metric(self, mock_svc_cls, mock_build, mock_trainer_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"id": i} for i in range(150)]
        mock_svc.create_model_registry.return_value = {"model_id": "m1"}
        mock_svc.create_model_training_job.return_value = {"job_id": "j1"}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc.add_model_artifact.return_value = {}
        mock_svc.update_model_training_job.return_value = {}
        mock_svc.update_model_registry_status.return_value = {}
        mock_svc.deactivate_active_models.return_value = {}

        mock_build.return_value = ([{"a": 1}] * 80, [1.0] * 80)

        mock_trainer = MagicMock()
        mock_trainer_cls.return_value = mock_trainer
        mock_trainer.train.return_value = {
            "status": "trained", "samples": 80, "val_loss": 0.30,
            "val_mae": 5.0, "epochs_trained": 20,
        }
        mock_trainer.serialize.return_value = b"fake_weights"

        result = train_user_lstm("u1")
        assert result["status"] == "completed"
        mock_svc.create_model_registry.assert_called_once()
        mock_svc.create_model_training_job.assert_called_once()
        mock_svc.insert_model_metric.assert_called_once()
        mock_svc.add_model_artifact.assert_called_once()
        mock_svc.update_model_training_job.assert_called_once_with("j1", "completed")
        mock_svc.deactivate_active_models.assert_called_once()
        status_call = mock_svc.update_model_registry_status.call_args
        assert status_call[0][0] == "m1"
        assert status_call[0][1] == "active"
        assert "promotion_confidence" in status_call[0][2]
        metric = mock_svc.insert_model_metric.call_args[0][0]
        assert metric["model_type"] == "lstm"
        assert metric["metric_type"] == "lstm_training"

    @patch("app.services.supabase_client.SupabaseService")
    def test_tune_user_lstm_no_data(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = []

        result = tune_user_lstm("u1")
        assert result["status"] == "no_data"

    @patch("optuna.create_study")
    @patch("app.tasks.ml_tasks._build_gb_training_data")
    @patch("app.services.supabase_client.SupabaseService")
    def test_tune_user_lstm_logs_metric(self, mock_svc_cls, mock_build, mock_create_study):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"id": i} for i in range(150)]
        mock_svc.create_model_registry.return_value = {"model_id": "m1"}
        mock_svc.create_model_training_job.return_value = {"job_id": "j2"}
        mock_svc.create_optuna_study.return_value = {"study_id": "s1"}
        mock_svc.create_optuna_trial.return_value = {}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc.update_optuna_study.return_value = {}
        mock_svc.deactivate_active_models.return_value = {}
        mock_svc.update_model_training_job.return_value = {}
        mock_svc.update_model_registry_status.return_value = {}
        mock_svc.add_model_artifact.return_value = {}

        mock_build.return_value = ([{"a": 1}] * 80, [1.0] * 80)

        mock_study = MagicMock()
        mock_study.best_value = 0.30
        mock_study.best_trial.number = 2
        mock_study.best_params = {"hidden_dim": 16, "dropout": 0.3, "learning_rate": 0.001, "batch_size": 32}
        mock_create_study.return_value = mock_study

        result = tune_user_lstm("u1")
        assert result["status"] in ("completed", "completed_no_promotion")
        mock_svc.create_model_registry.assert_called_once()
        mock_svc.create_model_training_job.assert_called_once()
        mock_svc.create_optuna_study.assert_called_once()
        mock_svc.update_optuna_study.assert_called_once()
        mock_svc.insert_model_metric.assert_called_once()
        mock_svc.update_model_training_job.assert_called_once_with("j2", "completed")
        metric = mock_svc.insert_model_metric.call_args[0][0]
        assert metric["model_type"] == "lstm"
        assert metric["metric_type"] == "optuna_tuning"
        assert "best_value" in result

    @patch("optuna.create_study")
    @patch("app.tasks.ml_tasks._build_gb_training_data")
    @patch("app.services.supabase_client.SupabaseService")
    def test_tune_user_lstm_does_not_promote_when_threshold_not_met(
        self, mock_svc_cls, mock_build, mock_create_study,
    ):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"id": i} for i in range(150)]
        mock_svc.create_model_registry.return_value = {"model_id": "m1"}
        mock_svc.create_model_training_job.return_value = {"job_id": "j2"}
        mock_svc.create_optuna_study.return_value = {"study_id": "s1"}
        mock_svc.create_optuna_trial.return_value = {}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc.update_optuna_study.return_value = {}
        mock_svc.deactivate_active_models.return_value = {}
        mock_svc.update_model_training_job.return_value = {}
        mock_svc.update_model_registry_status.return_value = {}
        mock_svc.add_model_artifact.return_value = {}

        mock_build.return_value = ([{"a": 1}] * 80, [1.0] * 80)

        mock_study = MagicMock()
        mock_study.best_value = 0.45
        mock_study.best_trial.number = 1
        mock_study.best_params = {"hidden_dim": 16, "dropout": 0.3, "learning_rate": 0.001, "batch_size": 32}
        mock_create_study.return_value = mock_study

        result = tune_user_lstm("u1")
        assert result["status"] == "completed_no_promotion"
        mock_svc.deactivate_active_models.assert_not_called()
        mock_svc.update_model_registry_status.assert_called_once_with("m1", "inactive")


class TestTrainUserGB:
    @patch("app.services.supabase_client.SupabaseService")
    def test_train_gb_no_data(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = []

        result = train_user_gb("u1")
        assert result["status"] == "no_data"

    @patch("app.tasks.ml_tasks._build_gb_training_data")
    @patch("app.services.supabase_client.SupabaseService")
    def test_train_gb_completes(self, mock_svc_cls, mock_build):
        import numpy as np

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"id": i} for i in range(50)]
        mock_svc.create_model_registry.return_value = {"model_id": "m1"}
        mock_svc.create_model_training_job.return_value = {"job_id": "j1"}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc.add_model_artifact.return_value = {}
        mock_svc.deactivate_active_models.return_value = {}
        mock_svc.update_model_training_job.return_value = {}
        mock_svc.update_model_registry_status.return_value = {}

        rng = np.random.default_rng(42)
        feature_rows = [
            {
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
            for _ in range(50)
        ]
        targets = [rng.uniform(-10, 30) for _ in range(50)]
        mock_build.return_value = (feature_rows, targets)

        result = train_user_gb("u1")
        assert result["status"] == "completed"
        assert "cv_mae" in result
        mock_svc.create_model_registry.assert_called_once()
        mock_svc.add_model_artifact.assert_called_once()
        reg_call = mock_svc.create_model_registry.call_args[0][0]
        assert reg_call["model_family"] == "gb"
