from app.tasks import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.projection_tasks.recompute_projection")
def recompute_projection(user_id: str, event: str = "5000") -> dict:
    """Recompute projection for a user after feature update."""
    try:
        from app.services.projection_service import ProjectionService
        from app.services.supabase_client import SupabaseService

        svc = ProjectionService()
        db = SupabaseService()
        activities_raw = db.get_recent_activities(user_id, days=90)

        if not activities_raw:
            return {"status": "no_data", "user_id": user_id, "event": event}

        from app.services.feature_service import FeatureService
        from app.services.cleaning_service import CleaningService
        from app.models.activities import NormalizedActivity

        activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]
        avg_pace = CleaningService.compute_runner_avg_pace(activities)
        cleaned = CleaningService.clean_batch(activities, avg_pace)

        if not cleaned:
            return {"status": "no_valid_activities", "user_id": user_id}

        features = FeatureService.compute_all_features(cleaned)
        state = svc.recompute(user_id, event, features)

        if state and state.projected_time_seconds:
            try:
                from app.services.embedding_service import EmbeddingService
                old_proj = db.get_latest_projection(user_id, event)
                old_time = old_proj.get("midpoint_seconds", state.projected_time_seconds) if old_proj else state.projected_time_seconds
                if abs(old_time - state.projected_time_seconds) > 2.0:
                    EmbeddingService().embed_projection_change(
                        user_id=user_id, event=event,
                        old_time_s=old_time, new_time_s=state.projected_time_seconds,
                        improvement_s=state.projected_time_seconds,
                    )
            except Exception:
                logger.debug("Embedding failed for projection change")

        return {
            "status": "updated",
            "user_id": user_id,
            "event": event,
            "projected_time": state.projected_time_seconds if state else None,
        }
    except Exception as e:
        logger.exception("recompute_projection failed")
        return {"status": "error", "user_id": user_id, "error": str(e)}


@celery_app.task(name="app.tasks.projection_tasks.recompute_all_events")
def recompute_all_events(user_id: str) -> dict:
    """Recompute projections for all events after race sync or major change."""
    events = ["1500", "3000", "5000", "10000", "21097", "42195"]
    results = {}
    for event in events:
        results[event] = recompute_projection(user_id, event)
    return {"user_id": user_id, "events": results}


@celery_app.task(name="app.tasks.projection_tasks.structural_decay_check")
def structural_decay_check() -> dict:
    """Daily cron: apply decay for inactive users.

    - >10 days inactive: widen supported range by 5%, insert notification
    - >21 days inactive: mark projection as "Declining" (stale)
    """
    from datetime import datetime, timedelta, timezone
    from app.services.supabase_client import SupabaseService

    try:
        db = SupabaseService()
        users = db.get_onboarded_users()

        now = datetime.now(timezone.utc)
        ten_days_ago = (now - timedelta(days=10)).isoformat()
        twenty_one_days_ago = (now - timedelta(days=21)).isoformat()

        users_checked = 0
        users_decayed = 0
        users_stale = 0

        for user_row in users:
            user_id = user_row["user_id"]
            users_checked += 1

            recent = db.get_recent_activities(user_id, days=25)
            if not recent:
                last_ts = None
            else:
                last_ts = recent[0].get("timestamp")

            if last_ts is None or last_ts < twenty_one_days_ago:
                for event in ("1500", "3000", "5000", "10000", "21097", "42195"):
                    proj = db.get_latest_projection(user_id, event)
                    if proj and proj.get("status") != "Declining":
                        db.insert_projection({
                            "user_id": user_id,
                            "event": event,
                            "midpoint_seconds": proj.get("midpoint_seconds"),
                            "range_lower": proj.get("range_lower"),
                            "range_upper": proj.get("range_upper"),
                            "range_low_seconds": proj.get("range_low_seconds"),
                            "range_high_seconds": proj.get("range_high_seconds"),
                            "confidence_score": max((proj.get("confidence_score") or 0.5) - 0.1, 0.1),
                            "volatility_score": proj.get("volatility_score", 0),
                            "status": "Declining",
                        })
                db.insert_notification(
                    user_id,
                    "intervention",
                    "Projection Declining",
                    "No activity logged in 21+ days. Your projection is now marked as declining.",
                    deep_link="/projection",
                )
                users_stale += 1
                users_decayed += 1

            elif last_ts < ten_days_ago:
                for event in ("1500", "3000", "5000", "10000", "21097", "42195"):
                    proj = db.get_latest_projection(user_id, event)
                    if proj:
                        low = proj.get("range_lower") or 0
                        high = proj.get("range_upper") or 0
                        span = high - low if high > low else 0
                        widened_low = low - span * 0.05
                        widened_high = high + span * 0.05
                        db.insert_projection({
                            "user_id": user_id,
                            "event": event,
                            "midpoint_seconds": proj.get("midpoint_seconds"),
                            "range_lower": widened_low,
                            "range_upper": widened_high,
                            "range_low_seconds": widened_low,
                            "range_high_seconds": widened_high,
                            "confidence_score": max((proj.get("confidence_score") or 0.5) - 0.05, 0.1),
                            "volatility_score": proj.get("volatility_score", 0),
                            "status": "Holding",
                        })
                db.insert_notification(
                    user_id,
                    "intervention",
                    "Projection Holding",
                    "No activity logged in 10+ days. Your supported range is widening.",
                    deep_link="/projection",
                )
                users_decayed += 1

        return {
            "status": "completed",
            "users_checked": users_checked,
            "users_decayed": users_decayed,
            "users_stale": users_stale,
        }
    except Exception as e:
        logger.exception("structural_decay_check failed")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.projection_tasks.weekly_summary")
def weekly_summary() -> dict:
    """Weekly cron: generate summaries for active users.

    For each onboarded user:
    1. Get activities from last 7 days
    2. Get latest projection and drivers
    3. Build summary text
    4. Insert notification_log entry
    """
    from datetime import datetime, timedelta, timezone
    from app.services.supabase_client import SupabaseService

    try:
        db = SupabaseService()
        users = db.get_onboarded_users()
        summaries_sent = 0

        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        for user_row in users:
            user_id = user_row["user_id"]

            activities = db.get_activities_since(user_id, seven_days_ago)
            if not activities:
                continue

            total_distance_km = sum(a.get("distance_meters", 0) for a in activities) / 1000
            total_duration_min = sum(a.get("duration_seconds", 0) for a in activities) / 60
            run_count = len(activities)

            proj_5k = db.get_latest_projection(user_id, "5000")
            proj_text = ""
            if proj_5k:
                t = proj_5k.get("midpoint_seconds")
                if t:
                    mins = int(t // 60)
                    secs = int(t % 60)
                    proj_text = f"5K projection: {mins}:{secs:02d}"
                    status = proj_5k.get("status", "")
                    if status:
                        proj_text += f" ({status})"

            drivers = db.get_latest_drivers(user_id)
            driver_text = ""
            if drivers:
                d = drivers[0]
                parts = []
                for key in ("aerobic_base", "threshold_density", "speed_exposure", "load_consistency", "running_economy"):
                    val = d.get(f"{key}_seconds")
                    if val is not None:
                        parts.append(f"{key}: {val:.1f}")
                if parts:
                    driver_text = "Drivers — " + ", ".join(parts)

            body_lines = [
                f"This week: {run_count} runs, {total_distance_km:.1f} km, {total_duration_min:.0f} min total",
            ]
            if proj_text:
                body_lines.append(proj_text)
            if driver_text:
                body_lines.append(driver_text)

            db.insert_notification(
                user_id,
                "weekly_summary",
                "Your Weekly Summary",
                "\n".join(body_lines),
                deep_link="/dashboard",
            )
            try:
                from app.services.embedding_service import EmbeddingService
                EmbeddingService().embed_insight(user_id, "\n".join(body_lines), "weekly_summary")
            except Exception:
                pass
            summaries_sent += 1

        return {"status": "completed", "summaries_sent": summaries_sent}
    except Exception as e:
        logger.exception("weekly_summary failed")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.projection_tasks.bias_correction")
def bias_correction() -> dict:
    """Monthly cron: iterative bias correction for users with race results.

    For each user with race activities:
    1. Compare most recent race time vs projected time at that distance
    2. Compute bias = actual - projected
    3. If |bias| > 10 seconds: log to model_metrics table
    """
    from datetime import datetime, timezone
    from app.services.supabase_client import SupabaseService

    DISTANCE_TO_EVENT = {
        (1400, 1600): "1500",
        (2900, 3100): "3000",
        (4900, 5100): "5000",
        (9800, 10200): "10000",
    }

    try:
        db = SupabaseService()
        users = db.get_onboarded_users()
        users_corrected = 0
        biases_logged = 0
        bias_threshold = 10.0

        for user_row in users:
            user_id = user_row["user_id"]
            races = db.get_race_activities(user_id)
            if not races:
                continue

            race = races[0]
            race_distance = race.get("distance_meters", 0)
            race_time = race.get("duration_seconds", 0)
            if not race_distance or not race_time:
                continue

            event = None
            for (low, high), ev in DISTANCE_TO_EVENT.items():
                if low <= race_distance <= high:
                    event = ev
                    break

            if event is None:
                continue

            proj = db.get_latest_projection(user_id, event)
            if not proj or not proj.get("midpoint_seconds"):
                continue

            projected = proj["midpoint_seconds"]
            bias = race_time - projected

            if abs(bias) > bias_threshold:
                db.insert_model_metric({
                    "user_id": user_id,
                    "metric_type": "bias_correction",
                    "event": event,
                    "actual_seconds": race_time,
                    "projected_seconds": projected,
                    "bias_seconds": bias,
                    "race_timestamp": race.get("timestamp"),
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                })
                biases_logged += 1

            users_corrected += 1

        return {
            "status": "completed",
            "users_corrected": users_corrected,
            "biases_logged": biases_logged,
        }
    except Exception as e:
        logger.exception("bias_correction failed")
        return {"status": "error", "error": str(e)}
