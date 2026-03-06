from app.tasks import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.social_tasks.compute_cohort_benchmarks")
def compute_cohort_benchmarks() -> dict:
    """Weekly cron: compute cohort percentile benchmarks per event."""
    from app.services.supabase_client import SupabaseService
    import numpy as np

    try:
        db = SupabaseService()
        events = ["1500", "3000", "5000", "10000", "21097", "42195"]
        computed = 0

        for event in events:
            result = (
                db.client.table("projection_state")
                .select("user_id, midpoint_seconds")
                .eq("event", event)
                .not_.is_("midpoint_seconds", "null")
                .order("computed_at", desc=True)
                .execute()
            )

            if not result.data or len(result.data) < 5:
                continue

            seen_users: set[str] = set()
            times: list[float] = []
            for row in result.data:
                uid = row.get("user_id")
                if uid and uid in seen_users:
                    continue
                if uid:
                    seen_users.add(uid)
                t = row.get("midpoint_seconds")
                if t and t > 0:
                    times.append(t)

            if len(times) < 5:
                continue

            arr = np.array(times)
            db.client.table("cohort_benchmarks").insert({
                "event": event,
                "percentile_10": round(float(np.percentile(arr, 10)), 1),
                "percentile_25": round(float(np.percentile(arr, 25)), 1),
                "percentile_50": round(float(np.percentile(arr, 50)), 1),
                "percentile_75": round(float(np.percentile(arr, 75)), 1),
                "percentile_90": round(float(np.percentile(arr, 90)), 1),
                "sample_size": len(times),
            }).execute()
            computed += 1

        return {"status": "completed", "events_computed": computed}
    except Exception as e:
        logger.exception("compute_cohort_benchmarks failed")
        return {"status": "error", "error": str(e)}
