import logging
from datetime import datetime, timedelta, timezone

from app.tasks import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.sync_tasks.process_activity")
def process_activity(user_id: str, raw_payload: dict, source: str = "unknown") -> dict:
    from app.services.cleaning_service import CleaningService
    from app.services.supabase_client import SupabaseService
    from app.models.activities import NormalizedActivity

    result = {"user_id": user_id, "source": source, "status": "processed"}

    if source == "strava":
        from app.services.strava_service import StravaService
        if "activity_id" in raw_payload and len(raw_payload) <= 2:
            import httpx
            from app.services.supabase_client import SupabaseService as _SB
            _db = _SB()
            conns = _db.get_wearable_connections(user_id)
            strava_conn = next((c for c in conns if c.get("provider") == "strava" and c.get("is_active")), None)
            if strava_conn and strava_conn.get("access_token"):
                with httpx.Client() as http:
                    resp = http.get(
                        f"https://www.strava.com/api/v3/activities/{raw_payload['activity_id']}",
                        headers={"Authorization": f"Bearer {strava_conn['access_token']}"},
                    )
                    if resp.status_code == 200:
                        raw_payload = resp.json()
                    else:
                        logger.warning("Failed to fetch Strava activity %s: %s", raw_payload["activity_id"], resp.status_code)
                        result["status"] = "fetch_failed"
                        return result
            else:
                logger.warning("No active Strava connection for user %s", user_id)
                result["status"] = "no_connection"
                return result
        activity = StravaService.normalize_activity(raw_payload)
    elif source in ("terra", "garmin", "fitbit", "suunto", "coros"):
        from app.services.terra_service import TerraService
        activity = TerraService.normalize_activity(raw_payload)
    else:
        try:
            activity = NormalizedActivity(**raw_payload)
        except Exception as e:
            result["status"] = "normalization_failed"
            result["error"] = str(e)
            return result

    cleaned = CleaningService.clean_activity(activity)
    if cleaned is None:
        result["status"] = "filtered_out"
        result["reason"] = "Failed cleaning pipeline"
        return result

    try:
        db = SupabaseService()
        db.insert_activity(user_id, {
            "source": source,
            "timestamp": cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat(),
            "started_at": cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat(),
            "duration_seconds": cleaned.duration_seconds,
            "distance_meters": cleaned.distance_meters,
            "avg_hr": cleaned.avg_hr,
            "max_hr": cleaned.max_hr,
            "avg_pace_sec_per_km": cleaned.avg_pace_sec_per_km,
            "elevation_gain_m": cleaned.elevation_gain_m,
            "calories": cleaned.calories,
            "activity_type": cleaned.activity_type,
            "hr_zones": cleaned.hr_zones,
            "laps": cleaned.laps,
        })
    except Exception:
        logger.exception("Failed to store activity for user %s", user_id)

    try:
        if (cleaned.distance_meters or 0) > 10000 or cleaned.activity_type == "race":
            from app.services.embedding_service import EmbeddingService
            EmbeddingService().embed_activity_summary(
                user_id=user_id,
                activity_type=cleaned.activity_type or "unknown",
                distance_km=round((cleaned.distance_meters or 0) / 1000, 1),
                duration_min=round((cleaned.duration_seconds or 0) / 60, 1),
                avg_hr=cleaned.avg_hr,
            )
    except Exception:
        logger.warning("Activity embedding failed for user %s", user_id, exc_info=True)

    if cleaned.activity_type == "race":
        from app.tasks.projection_tasks import recompute_all_events
        recompute_all_events.delay(user_id)

        # Auto-replace baseline with race result
        try:
            distance = cleaned.distance_meters or 0
            duration = cleaned.duration_seconds or 0
            race_date = (cleaned.timestamp.strftime("%Y-%m-%d") if cleaned.timestamp else None)

            DISTANCE_TO_EVENT = {
                (1400, 1600): "1500", (2900, 3100): "3000",
                (4900, 5100): "5000", (9800, 10200): "10000",
                (20500, 21700): "21097", (41000, 43000): "42195",
            }
            matched_event = None
            for (low, high), ev in DISTANCE_TO_EVENT.items():
                if low <= distance <= high:
                    matched_event = ev
                    break

            if matched_event and duration > 0:
                db.client.table("users").update({
                    "baseline_event": matched_event,
                    "baseline_time_seconds": duration,
                    "baseline_race_date": race_date,
                    "baseline_source": "race",
                }).eq("user_id", user_id).execute()

                db.insert_notification(
                    user_id,
                    "projection_update",
                    "Model Recalibrated",
                    f"Your baseline has been updated based on your recent {matched_event}m race.",
                    deep_link=f"/event/{matched_event}",
                )
        except Exception:
            logger.exception("Failed to update baseline from race for user %s", user_id)
    else:
        from app.tasks.feature_engineering import compute_features
        compute_features.delay(user_id)

    result["activity_type"] = cleaned.activity_type
    result["distance_meters"] = cleaned.distance_meters
    return result


def _backfill_terra_physiology(
    db, user_id: str, terra_user_id: str, _settings, start_date, end_date,
) -> dict:
    """Backfill sleep, body, and daily physiology data from Terra REST API."""
    import httpx
    from app.services.terra_service import TerraService

    headers = {
        "x-api-key": _settings.terra_api_key,
        "dev-id": _settings.terra_dev_id,
    }
    params_base = {
        "user_id": terra_user_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "to_webhook": "false",
    }
    totals = {"sleep": 0, "body": 0, "daily": 0}

    for data_type, normalizer in [
        ("sleep", TerraService.normalize_sleep_entry),
        ("body", TerraService.normalize_body_entry),
        ("daily", TerraService.normalize_daily_entry),
    ]:
        try:
            with httpx.Client(timeout=30) as http:
                resp = http.get(
                    f"https://api.tryterra.co/v2/{data_type}",
                    headers=headers,
                    params=params_base,
                )
            if resp.status_code != 200:
                logger.warning(
                    "Terra backfill %s returned %s for user %s",
                    data_type, resp.status_code, user_id,
                )
                continue
            entries = resp.json().get("data", [])
            for raw_entry in entries:
                try:
                    normalized = normalizer(raw_entry)
                    has_data = (
                        normalized.get("sleep_score") is not None
                        or normalized.get("resting_hr") is not None
                        or normalized.get("hrv") is not None
                    )
                    custom = normalized.get("custom_fields") or {}
                    has_body = (
                        custom.get("weight_kg") is not None
                        or custom.get("body_fat_percentage") is not None
                    )
                    if has_data or has_body:
                        db.insert_wearable_physiology(user_id, normalized)
                        totals[data_type] += 1
                except Exception:
                    logger.exception(
                        "Failed to process Terra %s backfill entry for user %s",
                        data_type, user_id,
                    )
        except Exception:
            logger.exception(
                "Terra %s backfill request failed for user %s", data_type, user_id,
            )

    logger.warning(
        "Terra physiology backfill: user=%s sleep=%d body=%d daily=%d",
        user_id, totals["sleep"], totals["body"], totals["daily"],
    )
    return totals


@celery_app.task(name="app.tasks.sync_tasks.backfill_history", bind=True)
def backfill_history(self, user_id: str, provider: str) -> dict:
    try:
        import redis
        r = redis.from_url(settings.redis_url or "redis://localhost:6379/0")
        lock_key = f"pirx:lock:backfill:{user_id}:{provider}"
        if not r.set(lock_key, "1", nx=True, ex=300):
            logger.info("backfill_history skipped for user %s provider %s (dedup)", user_id, provider)
            return {"status": "deduplicated", "user_id": user_id}
    except Exception:
        logger.warning("Redis dedup lock unavailable for backfill user=%s, proceeding anyway", user_id, exc_info=True)

    from app.services.supabase_client import SupabaseService
    from app.services.cleaning_service import CleaningService
    from app.models.activities import NormalizedActivity

    db = SupabaseService()
    imported = 0
    valid = 0

    try:
        db.register_task(user_id, "backfill_history", self.request.id or "unknown")
        db.update_task_status(self.request.id or "unknown", "running")
    except Exception:
        logger.warning("Could not register backfill task for user %s", user_id)

    try:
        if provider == "strava":
            connections = db.get_wearable_connections(user_id)
            strava_conn = next(
                (c for c in connections if c.get("provider") == "strava" and c.get("is_active")),
                None,
            )
            if not strava_conn:
                return {"status": "error", "user_id": user_id, "error": "No active Strava connection"}

            access_token = strava_conn.get("access_token")
            if not access_token:
                return {"status": "error", "user_id": user_id, "error": "No Strava access token"}

            import httpx
            from app.services.strava_service import StravaService

            six_months_ago = int((datetime.now(timezone.utc) - timedelta(days=180)).timestamp())
            page = 1
            per_page = 100
            all_activities = []

            while True:
                try:
                    with httpx.Client(timeout=30) as client:
                        resp = client.get(
                            "https://www.strava.com/api/v3/athlete/activities",
                            headers={"Authorization": f"Bearer {access_token}"},
                            params={"after": six_months_ago, "page": page, "per_page": per_page},
                        )
                    if resp.status_code != 200:
                        logger.warning("Strava API returned %d for user %s", resp.status_code, user_id)
                        break
                    batch = resp.json()
                    if not batch:
                        break
                    all_activities.extend(batch)
                    page += 1
                    if len(batch) < per_page:
                        break
                except Exception:
                    logger.exception("Strava API error during backfill for user %s page %d", user_id, page)
                    break

            for raw in all_activities:
                imported += 1
                try:
                    normalized = StravaService.normalize_activity(raw)

                    if raw.get("id") and not normalized.hr_zones:
                        try:
                            with httpx.Client(timeout=15) as stream_client:
                                streams_resp = stream_client.get(
                                    f"https://www.strava.com/api/v3/activities/{raw['id']}/streams",
                                    headers={"Authorization": f"Bearer {access_token}"},
                                    params={"keys": "heartrate,time", "key_type": "stream"},
                                )
                            if streams_resp.status_code == 200:
                                streams = {s["type"]: s["data"] for s in streams_resp.json()}
                                if "heartrate" in streams:
                                    hr_zones = StravaService.compute_hr_zones(
                                        streams["heartrate"],
                                        max_hr=normalized.max_hr or 190,
                                    )
                                    normalized = NormalizedActivity(
                                        **{**normalized.__dict__, "hr_zones": hr_zones}
                                    )
                        except Exception:
                            logger.debug("Failed to fetch HR streams for activity %s", raw.get("id"))

                    cleaned = CleaningService.clean_activity(normalized)
                    if cleaned is None:
                        continue
                    db.insert_activity(user_id, {
                        "source": "strava",
                        "external_id": str(raw.get("id", "")),
                        "timestamp": cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat(),
                        "started_at": cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat(),
                        "duration_seconds": cleaned.duration_seconds,
                        "distance_meters": cleaned.distance_meters,
                        "avg_hr": cleaned.avg_hr,
                        "max_hr": cleaned.max_hr,
                        "avg_pace_sec_per_km": cleaned.avg_pace_sec_per_km,
                        "elevation_gain_m": cleaned.elevation_gain_m,
                        "calories": cleaned.calories,
                        "activity_type": cleaned.activity_type,
                        "hr_zones": cleaned.hr_zones,
                    })
                    valid += 1
                except Exception:
                    logger.exception("Failed to process Strava activity for user %s", user_id)

        elif provider in ("terra", "garmin", "fitbit", "suunto", "coros"):
            from app.config import settings as _settings
            if not _settings.terra_api_key or not _settings.terra_dev_id:
                logger.warning("Terra API credentials not configured for provider %s", provider)
            else:
                import httpx
                from app.services.terra_service import TerraService

                connections = db.get_wearable_connections(user_id)
                terra_conn = next(
                    (c for c in connections if c.get("provider") == provider and c.get("is_active")),
                    None,
                )
                terra_user_id = terra_conn.get("terra_user_id") if terra_conn else None
                if not terra_user_id:
                    logger.warning("No terra_user_id found for user %s provider %s", user_id, provider)
                    return {"status": "error", "user_id": user_id, "error": f"No terra_user_id for {provider}"}

                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=180)
                try:
                    with httpx.Client() as http:
                        resp = http.get(
                            "https://api.tryterra.co/v2/activity",
                            headers={
                                "x-api-key": _settings.terra_api_key,
                                "dev-id": _settings.terra_dev_id,
                            },
                            params={
                                "user_id": terra_user_id,
                                "start_date": start_date.strftime("%Y-%m-%d"),
                                "end_date": end_date.strftime("%Y-%m-%d"),
                                "to_webhook": "false",
                            },
                        )
                        if resp.status_code == 200:
                            resp_json = resp.json()
                            activities_data = resp_json.get("data", [])
                            logger.warning(
                                "Terra backfill response: user=%s terra_user=%s activities=%d keys=%s",
                                user_id, terra_user_id, len(activities_data),
                                list(resp_json.keys()),
                            )
                            for raw_act in activities_data:
                                imported += 1
                                try:
                                    activity = TerraService.normalize_activity(raw_act)
                                    cleaned = CleaningService.clean_activity(activity)
                                    if cleaned is None:
                                        continue
                                    if not cleaned.duration_seconds or cleaned.duration_seconds < 60:
                                        continue
                                    ts_iso = cleaned.timestamp.isoformat() if cleaned.timestamp else datetime.now(timezone.utc).isoformat()
                                    db.insert_activity(user_id, {
                                        "source": provider,
                                        "external_id": raw_act.get("id", ""),
                                        "timestamp": ts_iso,
                                        "started_at": ts_iso,
                                        "duration_seconds": cleaned.duration_seconds,
                                        "distance_meters": cleaned.distance_meters,
                                        "avg_hr": cleaned.avg_hr,
                                        "max_hr": cleaned.max_hr,
                                        "avg_pace_sec_per_km": cleaned.avg_pace_sec_per_km,
                                        "elevation_gain_m": cleaned.elevation_gain_m,
                                        "calories": cleaned.calories,
                                        "activity_type": cleaned.activity_type,
                                        "hr_zones": cleaned.hr_zones,
                                    })
                                    valid += 1
                                except Exception:
                                    logger.exception("Failed to process Terra activity for user %s", user_id)
                        else:
                            logger.warning("Terra API returned %s for user %s", resp.status_code, user_id)
                except Exception:
                    logger.exception("Terra backfill failed for user %s provider %s", user_id, provider)

                try:
                    phys_totals = _backfill_terra_physiology(
                        db, user_id, terra_user_id, _settings, start_date, end_date,
                    )
                    logger.warning("Physiology backfill result for user %s: %s", user_id, phys_totals)
                except Exception:
                    logger.exception("_backfill_terra_physiology failed for user %s", user_id)

        if valid > 0:
            from app.tasks.feature_engineering import compute_features
            compute_features.delay(user_id)

        try:
            db.update_task_status(self.request.id or "unknown", "completed")
        except Exception:
            logger.warning("Task status update failed for task %s", self.request.id, exc_info=True)

        return {
            "status": "completed",
            "user_id": user_id,
            "provider": provider,
            "activities_imported": imported,
            "activities_valid": valid,
        }
    except Exception as e:
        try:
            db.update_task_status(self.request.id or "unknown", "failed", str(e))
        except Exception:
            pass
        return {"status": "error", "user_id": user_id, "error": str(e)}
