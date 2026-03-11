from datetime import datetime, timezone
import logging

from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _simulate_optuna_trials(sample_size: int) -> list[float]:
    """Generate deterministic trial losses for scaffolding and tests."""
    if sample_size >= 120:
        return [0.29, 0.31, 0.33]
    if sample_size >= 60:
        return [0.32, 0.34, 0.36]
    return [0.35, 0.37, 0.39]


@celery_app.task(name="app.tasks.ml_tasks.train_user_lstm")
def train_user_lstm(user_id: str) -> dict:
    """Train per-user LSTM model (scaffold).

    Current implementation logs lifecycle metrics while deterministic projection
    remains active in production serving.
    """
    try:
        from app.services.supabase_client import SupabaseService

        db = SupabaseService()
        if user_id == "all":
            users = db.get_onboarded_users()
            dispatched = 0
            for row in users:
                uid = row.get("user_id")
                if not uid:
                    continue
                train_user_lstm.delay(uid)
                dispatched += 1
            return {"status": "queued", "users_dispatched": dispatched}

        activities = db.get_recent_activities(user_id, days=180)
        if not activities:
            return {"status": "no_data", "user_id": user_id}

        now_iso = datetime.now(timezone.utc).isoformat()
        version = datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
        model = db.create_model_registry(
            {
                "user_id": user_id,
                "event": "5000",
                "model_family": "lstm",
                "version": version,
                "status": "training",
                "metadata": {"source": "ml_tasks.train_user_lstm"},
            }
        )
        model_id = model.get("model_id")
        job = db.create_model_training_job(
            {
                "model_id": model_id,
                "user_id": user_id,
                "job_type": "lstm_train",
                "status": "running",
                "trigger_source": "scheduled",
                "started_at": now_iso,
            }
        )
        job_id = job.get("job_id")

        db.insert_model_metric(
            {
                "user_id": user_id,
                "metric_date": datetime.now(timezone.utc).date().isoformat(),
                "model_type": "lstm",
                "metric_type": "lstm_training",
                "sample_size": len(activities),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        db.add_model_artifact(
            {
                "model_id": model_id,
                "job_id": job_id,
                "artifact_type": "weights",
                "storage_uri": f"local://models/{user_id}/lstm/{version}.pt",
                "metadata": {
                    "status": "scaffold",
                    "validation_score": 0.72,
                    "features_version": "v1",
                },
            }
        )
        if job_id:
            db.update_model_training_job(job_id, "completed")
        if model_id:
            db.update_model_registry_status(model_id, "active")
        return {"status": "completed", "user_id": user_id, "samples": len(activities)}
    except Exception as e:
        logger.exception("train_user_lstm failed")
        return {"status": "error", "user_id": user_id, "error": str(e)}


@celery_app.task(name="app.tasks.ml_tasks.tune_user_lstm")
def tune_user_lstm(user_id: str) -> dict:
    """Run Optuna tuning for per-user LSTM (scaffold)."""
    try:
        from app.services.supabase_client import SupabaseService

        db = SupabaseService()
        if user_id == "all":
            users = db.get_onboarded_users()
            dispatched = 0
            for row in users:
                uid = row.get("user_id")
                if not uid:
                    continue
                tune_user_lstm.delay(uid)
                dispatched += 1
            return {"status": "queued", "users_dispatched": dispatched}

        activities = db.get_recent_activities(user_id, days=180)
        if not activities:
            return {"status": "no_data", "user_id": user_id}

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        version = now.strftime("v%Y%m%d%H%M%S")
        model = db.create_model_registry(
            {
                "user_id": user_id,
                "event": "5000",
                "model_family": "lstm",
                "version": version,
                "status": "training",
                "metadata": {"source": "ml_tasks.tune_user_lstm"},
            }
        )
        model_id = model.get("model_id")
        job = db.create_model_training_job(
            {
                "model_id": model_id,
                "user_id": user_id,
                "job_type": "optuna_tune",
                "status": "running",
                "trigger_source": "scheduled",
                "started_at": now_iso,
            }
        )
        job_id = job.get("job_id")
        study = db.create_optuna_study(
            {
                "job_id": job_id,
                "model_id": model_id,
                "user_id": user_id,
                "study_name": f"lstm_{user_id}_{version}",
                "direction": "minimize",
                "status": "running",
            }
        )
        study_id = study.get("study_id")
        trial_values = _simulate_optuna_trials(len(activities))
        for trial_num, trial_value in enumerate(trial_values):
            db.create_optuna_trial(
                {
                    "study_id": study_id,
                    "trial_number": trial_num,
                    "state": "COMPLETE",
                    "value": round(trial_value, 4),
                    "params": {"hidden_units": 64 + trial_num * 32, "dropout": 0.2 + trial_num * 0.05},
                }
            )
        best_trial_num = min(range(len(trial_values)), key=lambda i: trial_values[i])
        best_value = float(trial_values[best_trial_num])
        if study_id:
            db.update_optuna_study(
                study_id=study_id,
                best_value=best_value,
                best_trial_number=best_trial_num,
                status="completed",
            )

        db.insert_model_metric(
            {
                "user_id": user_id,
                "metric_date": datetime.now(timezone.utc).date().isoformat(),
                "model_type": "lstm",
                "metric_type": "optuna_tuning",
                "sample_size": len(activities),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        promotion_threshold = 0.34
        promoted = best_value <= promotion_threshold
        status = "completed"
        if promoted and model_id:
            db.deactivate_active_models(
                user_id=user_id,
                event="5000",
                model_family="lstm",
                exclude_model_id=model_id,
            )
            db.add_model_artifact(
                {
                    "model_id": model_id,
                    "job_id": job_id,
                    "artifact_type": "metrics",
                    "storage_uri": f"local://models/{user_id}/lstm/{version}.metrics.json",
                    "metadata": {
                        "best_value": best_value,
                        "best_trial_number": best_trial_num,
                        "promotion_threshold": promotion_threshold,
                        "promotion_confidence": round(max(0.0, min(1.0, 1.0 - best_value)), 4),
                    },
                }
            )
            db.update_model_registry_status(
                model_id,
                "active",
                {
                    "source": "ml_tasks.tune_user_lstm",
                    "best_value": best_value,
                    "best_trial_number": best_trial_num,
                    "promotion_threshold": promotion_threshold,
                    "promotion_confidence": round(max(0.0, min(1.0, 1.0 - best_value)), 4),
                },
            )
        elif model_id:
            db.update_model_registry_status(model_id, "inactive")
            status = "completed_no_promotion"
        if job_id:
            db.update_model_training_job(job_id, "completed")
        return {
            "status": status,
            "user_id": user_id,
            "trials": len(trial_values),
            "best_value": best_value,
            "best_trial_number": best_trial_num,
            "promoted": promoted,
        }
    except Exception as e:
        logger.exception("tune_user_lstm failed")
        return {"status": "error", "user_id": user_id, "error": str(e)}
