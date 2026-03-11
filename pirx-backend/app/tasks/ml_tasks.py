from datetime import datetime, timezone
import logging

from app.tasks import celery_app

logger = logging.getLogger(__name__)


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
        return {"status": "completed", "user_id": user_id, "trials": 0}
    except Exception as e:
        logger.exception("tune_user_lstm failed")
        return {"status": "error", "user_id": user_id, "error": str(e)}
