from datetime import datetime, timezone
import logging

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ml_tasks.train_user_gb")
def train_user_gb(user_id: str) -> dict:
    """Train per-user Gradient Boosting projection model using real sklearn.

    Uses GradientBoostingRegressor with Huber loss, cross-validated on
    user feature history paired with performance anchors.
    """
    model_id = None
    job_id = None
    db = None
    try:
        from app.services.supabase_client import SupabaseService
        from app.ml.gb_projection_model import GBProjectionModel, MIN_TRAINING_SAMPLES

        db = SupabaseService()
        if user_id == "all":
            users = db.get_onboarded_users()
            dispatched = 0
            for row in users:
                uid = row.get("user_id")
                if not uid:
                    continue
                train_user_gb.delay(uid)
                dispatched += 1
            return {"status": "queued", "users_dispatched": dispatched}

        activities = db.get_recent_activities(user_id, days=180)
        if not activities or len(activities) < MIN_TRAINING_SAMPLES:
            return {"status": "no_data", "user_id": user_id,
                    "samples": len(activities) if activities else 0}

        feature_rows, targets = _build_gb_training_data(db, user_id, activities)
        if len(feature_rows) < MIN_TRAINING_SAMPLES:
            return {"status": "insufficient_training_data", "user_id": user_id,
                    "samples": len(feature_rows)}

        gb_model = GBProjectionModel()
        train_result = gb_model.train(feature_rows, targets)

        if train_result.get("status") != "trained":
            return {"status": "training_failed", "user_id": user_id,
                    "detail": train_result}

        now_iso = datetime.now(timezone.utc).isoformat()
        version = datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
        model = db.create_model_registry({
            "user_id": user_id,
            "event": "5000",
            "model_family": "gb",
            "version": version,
            "status": "training",
            "metadata": {
                "source": "ml_tasks.train_user_gb",
                "cv_mae": train_result.get("cv_mae"),
                "feature_importances": train_result.get("feature_importances"),
            },
        })
        model_id = model.get("model_id")
        job = db.create_model_training_job({
            "model_id": model_id,
            "user_id": user_id,
            "job_type": "gb_train",
            "status": "running",
            "trigger_source": "scheduled",
            "started_at": now_iso,
        })
        job_id = job.get("job_id")

        model_bytes = gb_model.serialize()
        db.add_model_artifact({
            "model_id": model_id,
            "job_id": job_id,
            "artifact_type": "weights",
            "storage_uri": f"local://models/{user_id}/gb/{version}.joblib",
            "metadata": {
                "status": "trained",
                "train_mae": train_result.get("train_mae"),
                "cv_mae": train_result.get("cv_mae"),
                "cv_std": train_result.get("cv_std"),
                "samples": train_result.get("samples"),
                "features_version": "v1",
                "model_bytes_size": len(model_bytes),
            },
        })

        db.insert_model_metric({
            "user_id": user_id,
            "metric_date": datetime.now(timezone.utc).date().isoformat(),
            "model_type": "gb",
            "metric_type": "gb_training",
            "sample_size": len(feature_rows),
            "computed_at": now_iso,
        })

        if job_id:
            db.update_model_training_job(job_id, "completed")
        if model_id:
            db.deactivate_active_models(
                user_id=user_id, event="5000", model_family="gb",
                exclude_model_id=model_id,
            )
            db.update_model_registry_status(model_id, "active", {
                "cv_mae": train_result.get("cv_mae"),
                "promotion_confidence": round(
                    max(0.0, min(1.0, 1.0 - (train_result.get("cv_mae", 100) / 100))),
                    4,
                ),
            })

        return {
            "status": "completed",
            "user_id": user_id,
            "samples": train_result.get("samples"),
            "cv_mae": train_result.get("cv_mae"),
        }
    except Exception as e:
        logger.exception("train_user_gb failed")
        if db and job_id:
            try:
                db.update_model_training_job(job_id, "failed")
            except Exception:
                pass
        if db and model_id:
            try:
                db.update_model_registry_status(model_id, "failed")
            except Exception:
                pass
        return {"status": "error", "user_id": user_id, "error": str(e)}


def _build_gb_training_data(
    db, user_id: str, activities: list[dict],
) -> tuple[list[dict], list[float]]:
    """Build feature-row / target pairs from user activity history.

    Pairs each activity's feature snapshot with its performance delta
    derived from race results or best-effort segments.
    """
    from app.services.feature_service import FeatureService
    from app.models.activities import NormalizedActivity

    feature_rows = []
    targets = []
    baseline_time_s = None

    try:
        baseline_data = db.get_baseline(user_id)
        if baseline_data:
            baseline_time_s = baseline_data.get("baseline_time_seconds")
    except Exception:
        pass

    if not baseline_time_s:
        baseline_time_s = 1500.0

    for i in range(30, len(activities)):
        window = activities[max(0, i - 90): i]
        if len(window) < 10:
            continue

        act = activities[i]
        act_time_str = act.get("start_time")
        ref_date = None
        if act_time_str:
            try:
                ref_date = datetime.fromisoformat(str(act_time_str).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        try:
            normalized = [
                NormalizedActivity(**a) if isinstance(a, dict) else a
                for a in window
            ]
            features = FeatureService.compute_all_features(
                normalized, reference_date=ref_date,
            )
        except Exception:
            continue

        pace = act.get("avg_pace_sec_per_km")
        distance = act.get("distance_meters", 0) or 0

        if pace and distance >= 3000:
            run_time_s = pace * (distance / 1000.0)
            if 4500 <= distance <= 5500:
                estimated_5k_time = run_time_s
            else:
                from app.ml.event_scaling import EventScaler
                estimated_5k_time = EventScaler.riegel_scale(
                    run_time_s, distance, 5000,
                )
            delta = baseline_time_s - estimated_5k_time
            feature_rows.append(features)
            targets.append(delta)

    return feature_rows, targets


@celery_app.task(name="app.tasks.ml_tasks.train_user_lstm")
def train_user_lstm(user_id: str) -> dict:
    """Train per-user LSTM model using real PyTorch training loop."""
    model_id = None
    job_id = None
    db = None
    try:
        from app.services.supabase_client import SupabaseService
        from app.ml.lstm_model import LSTMTrainer, MIN_LSTM_SAMPLES

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
        effective_min_lstm = max(MIN_LSTM_SAMPLES, 120)
        if not activities or len(activities) < effective_min_lstm:
            return {"status": "no_data", "user_id": user_id}

        feature_rows, targets = _build_gb_training_data(db, user_id, activities)
        if len(feature_rows) < MIN_LSTM_SAMPLES:
            return {"status": "insufficient_data", "user_id": user_id,
                    "samples": len(feature_rows)}

        trainer = LSTMTrainer(
            hidden_dim=17, dropout=0.5, learning_rate=1e-3,
            batch_size=56, seq_length=11, max_epochs=100, patience=10,
        )
        train_result = trainer.train(feature_rows, targets)

        if train_result.get("status") != "trained":
            return {"status": "training_failed", "user_id": user_id,
                    "detail": train_result}

        now_iso = datetime.now(timezone.utc).isoformat()
        version = datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
        model = db.create_model_registry({
            "user_id": user_id,
            "event": "5000",
            "model_family": "lstm",
            "version": version,
            "status": "training",
            "metadata": {"source": "ml_tasks.train_user_lstm"},
        })
        model_id = model.get("model_id")
        job = db.create_model_training_job({
            "model_id": model_id,
            "user_id": user_id,
            "job_type": "lstm_train",
            "status": "running",
            "trigger_source": "scheduled",
            "started_at": now_iso,
        })
        job_id = job.get("job_id")

        weight_bytes = trainer.serialize()
        db.add_model_artifact({
            "model_id": model_id,
            "job_id": job_id,
            "artifact_type": "weights",
            "storage_uri": f"local://models/{user_id}/lstm/{version}.pt",
            "metadata": {
                "status": "trained",
                "val_loss": train_result.get("val_loss"),
                "val_mae": train_result.get("val_mae"),
                "epochs_trained": train_result.get("epochs_trained"),
                "features_version": "v1",
                "hidden_dim": 17,
                "dropout": 0.5,
            },
        })

        db.insert_model_metric({
            "user_id": user_id,
            "metric_date": datetime.now(timezone.utc).date().isoformat(),
            "model_type": "lstm",
            "metric_type": "lstm_training",
            "sample_size": len(feature_rows),
            "computed_at": now_iso,
        })

        if job_id:
            db.update_model_training_job(job_id, "completed")
        if model_id:
            db.deactivate_active_models(
                user_id=user_id, event="5000", model_family="lstm",
                exclude_model_id=model_id,
            )
            db.update_model_registry_status(model_id, "active", {
                "val_mae": train_result.get("val_mae"),
                "promotion_confidence": round(
                    max(0.0, min(1.0, 1.0 - (train_result.get("val_loss", 1.0)))),
                    4,
                ),
            })

        return {
            "status": "completed",
            "user_id": user_id,
            "samples": train_result.get("samples"),
            "val_loss": train_result.get("val_loss"),
            "val_mae": train_result.get("val_mae"),
        }
    except Exception as e:
        logger.exception("train_user_lstm failed")
        if db and job_id:
            try:
                db.update_model_training_job(job_id, "failed")
            except Exception:
                pass
        if db and model_id:
            try:
                db.update_model_registry_status(model_id, "failed")
            except Exception:
                pass
        return {"status": "error", "user_id": user_id, "error": str(e)}


@celery_app.task(name="app.tasks.ml_tasks.tune_user_lstm")
def tune_user_lstm(user_id: str) -> dict:
    """Run real Optuna hyperparameter tuning for per-user LSTM."""
    model_id = None
    job_id = None
    db = None
    try:
        import optuna
        from app.services.supabase_client import SupabaseService
        from app.ml.lstm_model import LSTMTrainer, MIN_LSTM_SAMPLES

        optuna.logging.set_verbosity(optuna.logging.WARNING)

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
        effective_min_tune = max(MIN_LSTM_SAMPLES, 120)
        if not activities or len(activities) < effective_min_tune:
            return {"status": "no_data", "user_id": user_id}

        feature_rows, targets = _build_gb_training_data(db, user_id, activities)
        if len(feature_rows) < MIN_LSTM_SAMPLES:
            return {"status": "insufficient_data", "user_id": user_id,
                    "samples": len(feature_rows)}

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        version = now.strftime("v%Y%m%d%H%M%S")

        model = db.create_model_registry({
            "user_id": user_id,
            "event": "5000",
            "model_family": "lstm",
            "version": version,
            "status": "training",
            "metadata": {"source": "ml_tasks.tune_user_lstm"},
        })
        model_id = model.get("model_id")
        job = db.create_model_training_job({
            "model_id": model_id,
            "user_id": user_id,
            "job_type": "optuna_tune",
            "status": "running",
            "trigger_source": "scheduled",
            "started_at": now_iso,
        })
        job_id = job.get("job_id")

        db_study = db.create_optuna_study({
            "job_id": job_id,
            "model_id": model_id,
            "user_id": user_id,
            "study_name": f"lstm_{user_id}_{version}",
            "direction": "minimize",
            "status": "running",
        })
        study_id = db_study.get("study_id")

        def objective(trial):
            hidden_dim = trial.suggest_int("hidden_dim", 8, 64)
            dropout = trial.suggest_float("dropout", 0.1, 0.6)
            lr = trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True)
            batch_size = trial.suggest_categorical("batch_size", [16, 32, 56])

            trainer = LSTMTrainer(
                hidden_dim=hidden_dim,
                dropout=dropout,
                learning_rate=lr,
                batch_size=batch_size,
                seq_length=11,
                max_epochs=30,
                patience=5,
            )
            result = trainer.train(feature_rows, targets)

            val_loss = result.get("val_loss", float("inf"))

            if study_id:
                db.create_optuna_trial({
                    "study_id": study_id,
                    "trial_number": trial.number,
                    "state": "COMPLETE",
                    "value": round(val_loss, 4),
                    "params": {
                        "hidden_dim": hidden_dim,
                        "dropout": dropout,
                        "learning_rate": lr,
                        "batch_size": batch_size,
                    },
                })

            return val_loss

        n_trials = min(20, max(5, len(feature_rows) // 10))
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, timeout=300)

        best_value = float(study.best_value)
        best_trial_num = study.best_trial.number
        best_params = study.best_params

        if study_id:
            db.update_optuna_study(
                study_id=study_id,
                best_value=best_value,
                best_trial_number=best_trial_num,
                status="completed",
            )

        db.insert_model_metric({
            "user_id": user_id,
            "metric_date": datetime.now(timezone.utc).date().isoformat(),
            "model_type": "lstm",
            "metric_type": "optuna_tuning",
            "sample_size": len(feature_rows),
            "computed_at": now_iso,
        })

        promotion_threshold = 0.34
        promoted = best_value <= promotion_threshold

        if promoted and model_id:
            best_trainer = LSTMTrainer(
                hidden_dim=best_params.get("hidden_dim", 17),
                dropout=best_params.get("dropout", 0.5),
                learning_rate=best_params.get("learning_rate", 1e-3),
                batch_size=best_params.get("batch_size", 56),
                seq_length=11, max_epochs=100, patience=10,
            )
            best_trainer.train(feature_rows, targets)
            weight_bytes = best_trainer.serialize()

            db.deactivate_active_models(
                user_id=user_id, event="5000", model_family="lstm",
                exclude_model_id=model_id,
            )
            db.add_model_artifact({
                "model_id": model_id,
                "job_id": job_id,
                "artifact_type": "weights",
                "storage_uri": f"local://models/{user_id}/lstm/{version}.pt",
                "metadata": {
                    "best_value": best_value,
                    "best_trial_number": best_trial_num,
                    "best_params": best_params,
                    "promotion_threshold": promotion_threshold,
                    "promotion_confidence": round(max(0.0, min(1.0, 1.0 - best_value)), 4),
                    "hidden_dim": best_params.get("hidden_dim", 17),
                    "dropout": best_params.get("dropout", 0.5),
                },
            })
            db.update_model_registry_status(model_id, "active", {
                "source": "ml_tasks.tune_user_lstm",
                "best_value": best_value,
                "best_params": best_params,
                "promotion_confidence": round(max(0.0, min(1.0, 1.0 - best_value)), 4),
            })
            status = "completed"
        elif model_id:
            db.update_model_registry_status(model_id, "inactive")
            status = "completed_no_promotion"
        else:
            status = "completed"

        if job_id:
            db.update_model_training_job(job_id, "completed")

        return {
            "status": status,
            "user_id": user_id,
            "trials": n_trials,
            "best_value": best_value,
            "best_trial_number": best_trial_num,
            "best_params": best_params,
            "promoted": promoted,
        }
    except Exception as e:
        logger.exception("tune_user_lstm failed")
        if db and job_id:
            try:
                db.update_model_training_job(job_id, "failed")
            except Exception:
                pass
        if db and model_id:
            try:
                db.update_model_registry_status(model_id, "failed")
            except Exception:
                pass
        return {"status": "error", "user_id": user_id, "error": str(e)}
