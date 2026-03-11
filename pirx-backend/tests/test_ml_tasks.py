from unittest.mock import MagicMock, patch

from app.tasks.ml_tasks import train_user_lstm, tune_user_lstm


class TestMlTasks:
    @patch("app.services.supabase_client.SupabaseService")
    def test_train_user_lstm_no_data(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = []

        result = train_user_lstm("u1")
        assert result["status"] == "no_data"
        assert result["user_id"] == "u1"

    @patch("app.services.supabase_client.SupabaseService")
    def test_train_user_lstm_logs_metric(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"distance_meters": 5000, "duration_seconds": 1500}]
        mock_svc.create_model_registry.return_value = {"model_id": "m1"}
        mock_svc.create_model_training_job.return_value = {"job_id": "j1"}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc.add_model_artifact.return_value = {}
        mock_svc.update_model_training_job.return_value = {}
        mock_svc.update_model_registry_status.return_value = {}

        result = train_user_lstm("u1")
        assert result["status"] == "completed"
        mock_svc.create_model_registry.assert_called_once()
        mock_svc.create_model_training_job.assert_called_once()
        mock_svc.insert_model_metric.assert_called_once()
        mock_svc.add_model_artifact.assert_called_once()
        mock_svc.update_model_training_job.assert_called_once_with("j1", "completed")
        mock_svc.update_model_registry_status.assert_called_once_with("m1", "active")
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

    @patch("app.services.supabase_client.SupabaseService")
    def test_tune_user_lstm_logs_metric(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_recent_activities.return_value = [{"distance_meters": 5000, "duration_seconds": 1500}]
        mock_svc.create_model_registry.return_value = {"model_id": "m1"}
        mock_svc.create_model_training_job.return_value = {"job_id": "j2"}
        mock_svc.create_optuna_study.return_value = {"study_id": "s1"}
        mock_svc.create_optuna_trial.return_value = {}
        mock_svc.insert_model_metric.return_value = {}
        mock_svc.update_model_training_job.return_value = {}
        mock_svc.update_model_registry_status.return_value = {}

        result = tune_user_lstm("u1")
        assert result["status"] == "completed"
        mock_svc.create_model_registry.assert_called_once()
        mock_svc.create_model_training_job.assert_called_once()
        mock_svc.create_optuna_study.assert_called_once()
        assert mock_svc.create_optuna_trial.call_count >= 1
        mock_svc.insert_model_metric.assert_called_once()
        mock_svc.update_model_training_job.assert_called_once_with("j2", "completed")
        mock_svc.update_model_registry_status.assert_called_once_with("m1", "active")
        metric = mock_svc.insert_model_metric.call_args[0][0]
        assert metric["model_type"] == "lstm"
        assert metric["metric_type"] == "optuna_tuning"
