from app.tasks import celery_app


@celery_app.task(name="app.tasks.projection_tasks.recompute_projection")
def recompute_projection(user_id: str, event: str = "3000") -> dict:
    """Recompute projection for a user after feature update.

    Steps:
    1. Load latest feature snapshot
    2. Run projection engine for specified event
    3. Compute driver decomposition
    4. Apply volatility dampening
    5. Store immutable projection_state row
    6. Broadcast via Supabase Realtime if delta >= 2 seconds
    """
    return {"status": "not_implemented", "user_id": user_id, "event": event}


@celery_app.task(name="app.tasks.projection_tasks.recompute_all_events")
def recompute_all_events(user_id: str) -> dict:
    """Recompute projections for all registered events after race sync."""
    return {"status": "not_implemented", "user_id": user_id}
