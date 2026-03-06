from app.tasks import celery_app


@celery_app.task(name="app.tasks.projection_tasks.recompute_projection")
def recompute_projection(user_id: str, event: str = "3000") -> dict:
    """Recompute projection for a user after feature update.

    Steps:
    1. Load latest features from cache/DB
    2. Run projection engine (LMC/KNN/LSTM depending on maturity)
    3. Compute 5 driver states (MUST sum to total improvement)
    4. Apply volatility dampening: smoothed = alpha * new + (1-alpha) * previous
    5. Check if delta >= 2 seconds vs current projection
    6. If yes: store immutable Projection_State + Driver_State rows
    7. Generate embedding for chat RAG
    8. Supabase Realtime notifies frontend
    """
    # TODO: Implement with projection engine (Group 4)
    return {"status": "not_implemented", "user_id": user_id, "event": event}


@celery_app.task(name="app.tasks.projection_tasks.recompute_all_events")
def recompute_all_events(user_id: str) -> dict:
    """Recompute projections for all events after race sync or major change."""
    events = ["1500", "3000", "5000", "10000"]
    results = {}
    for event in events:
        results[event] = recompute_projection(user_id, event)
    return {"user_id": user_id, "events": results}


@celery_app.task(name="app.tasks.projection_tasks.structural_decay_check")
def structural_decay_check() -> dict:
    """Daily cron: check all users for inactivity-based decay.

    If no activity for >= 10 days:
    - Apply bounded decay factor to projection
    - Widen Supported Range (increase volatility)
    - Decrease Readiness score
    """
    # TODO: Load all users, check last activity date
    return {"status": "not_implemented", "task": "structural_decay_check"}


@celery_app.task(name="app.tasks.projection_tasks.weekly_summary")
def weekly_summary() -> dict:
    """Weekly cron (Monday): generate summary for all active users.

    Summary includes:
    - Projection changes this week
    - Driver shifts
    - Training volume recap
    - Send push notification
    """
    # TODO: Load active users, compute summaries
    return {"status": "not_implemented", "task": "weekly_summary"}


@celery_app.task(name="app.tasks.projection_tasks.bias_correction")
def bias_correction() -> dict:
    """Monthly cron: iterative bias correction (Biro et al. 2024).

    epsilon = 0.01 convergence threshold:
    while True:
        bias = mean(predicted - actual)
        corrected = predicted - bias
        new_error = mean(abs(corrected - actual))
        if abs(new_error - prev_error) < epsilon: break
    """
    # TODO: Load users with race results, run correction loop
    return {"status": "not_implemented", "task": "bias_correction"}
