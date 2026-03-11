from app.tasks import celery_app
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DISTANCE_TO_EVENT = {
    (1400, 1600): "1500",
    (2900, 3100): "3000",
    (4900, 5200): "5000",
    (9800, 10200): "10000",
    (20900, 21300): "21097",
    (41900, 42500): "42195",
}


@celery_app.task(name="app.tasks.accuracy_tasks.compute_model_accuracy")
def compute_model_accuracy() -> dict:
    """Weekly cron: compute model accuracy metrics across all users with race results."""
    from app.services.supabase_client import SupabaseService
    import numpy as np

    try:
        db = SupabaseService()
        users = db.get_onboarded_users()

        event_errors: dict[str, list[float]] = {}
        event_biases: dict[str, list[float]] = {}
        global_errors: list[float] = []
        global_biases: list[float] = []

        for user_row in users:
            user_id = user_row["user_id"]
            races = db.get_race_activities(user_id)
            if not races:
                continue

            for race in races:
                distance = race.get("distance_meters", 0)
                actual_time = race.get("duration_seconds", 0)
                if not distance or not actual_time:
                    continue

                event = None
                for (low, high), ev in DISTANCE_TO_EVENT.items():
                    if low <= distance <= high:
                        event = ev
                        break
                if not event:
                    continue

                proj = db.get_latest_projection(user_id, event)
                if not proj or not proj.get("midpoint_seconds"):
                    continue

                projected = proj["midpoint_seconds"]
                error = abs(actual_time - projected)
                bias = actual_time - projected

                global_errors.append(error)
                global_biases.append(bias)

                if event not in event_errors:
                    event_errors[event] = []
                if event not in event_biases:
                    event_biases[event] = []
                event_errors[event].append(error)
                event_biases[event].append(bias)

        if not global_errors:
            return {"status": "no_data"}

        now = datetime.now(timezone.utc).isoformat()

        global_mae = float(np.mean(global_errors))
        global_bias = float(np.mean(global_biases))
        global_std = float(np.std(global_biases))
        ba_lower = global_bias - 1.96 * global_std
        ba_upper = global_bias + 1.96 * global_std

        db.insert_model_metric({
            "metric_date": now[:10],
            "model_type": "global",
            "mae_seconds": round(global_mae, 2),
            "bias_seconds": round(global_bias, 2),
            "bland_altman_lower": round(ba_lower, 2),
            "bland_altman_upper": round(ba_upper, 2),
            "sample_size": len(global_errors),
        })

        for event, errors in event_errors.items():
            if len(errors) >= 2:
                biases_ev = event_biases.get(event, [])
                mae_ev = float(np.mean(errors))
                bias_ev = float(np.mean(biases_ev)) if biases_ev else 0
                std_ev = float(np.std(biases_ev)) if biases_ev else 0
                db.insert_model_metric({
                    "metric_date": now[:10],
                    "model_type": f"event_{event}",
                    "mae_seconds": round(mae_ev, 2),
                    "bias_seconds": round(bias_ev, 2),
                    "bland_altman_lower": round(bias_ev - 1.96 * std_ev, 2),
                    "bland_altman_upper": round(bias_ev + 1.96 * std_ev, 2),
                    "sample_size": len(errors),
                })

        return {
            "status": "completed",
            "global_mae": round(global_mae, 2),
            "global_bias": round(global_bias, 2),
            "sample_size": len(global_errors),
            "events_computed": list(event_errors.keys()),
        }
    except Exception as e:
        logger.exception("compute_model_accuracy failed")
        return {"status": "error", "error": str(e)}
