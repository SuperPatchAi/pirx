"""PIRX Chat Agent tools — 8 data retrieval tools for the LangGraph agent."""

from typing import Optional

from langchain_core.tools import tool


@tool
def get_projection(user_id: str, event: str = "5000") -> dict:
    """Get the current projection for a specific event distance.

    Returns projected time, supported range, improvement since baseline,
    21-day change, and status.
    """
    from app.services.supabase_client import SupabaseService

    db = SupabaseService()
    proj = db.get_latest_projection(user_id, event)
    if proj:
        return {
            "event": event,
            "projected_time_seconds": proj["midpoint_seconds"],
            "supported_range": (
                f"{proj.get('range_low_seconds', proj.get('range_lower', 0)):.1f}s – {proj.get('range_high_seconds', proj.get('range_upper', 0)):.1f}s"
            ),
            "improvement_since_baseline": proj.get(
                "improvement_since_baseline", 0
            ),
            "twenty_one_day_change": proj.get("twenty_one_day_change", 0),
            "status": proj.get("status", "Holding"),
            "last_updated": proj.get("computed_at"),
        }
    return {"event": event, "status": "No projection data available yet"}


@tool
def get_drivers(user_id: str) -> dict:
    """Get the current structural driver breakdown.

    Returns all 5 drivers: Aerobic Base, Threshold Density, Speed Exposure,
    Load Consistency, Running Economy — with contributions and trends.
    """
    from app.services.supabase_client import SupabaseService

    db = SupabaseService()
    rows = db.get_latest_drivers(user_id)
    if rows:
        row = rows[0]
        driver_names = {
            "aerobic_base": "Aerobic Base",
            "threshold_density": "Threshold Density",
            "speed_exposure": "Speed Exposure",
            "load_consistency": "Load Consistency",
            "running_economy": "Running Economy",
        }
        drivers = []
        for key, display in driver_names.items():
            drivers.append(
                {
                    "name": display,
                    "contribution_seconds": row.get(f"{key}_seconds", 0),
                }
            )
        return {"drivers": drivers, "computed_at": row.get("computed_at")}
    return {"drivers": [], "status": "No driver data available yet"}


@tool
def get_training_history(
    user_id: str, days: int = 14, activity_type: Optional[str] = None
) -> dict:
    """Get recent training history with activity summaries.

    Can filter by activity type: easy, threshold, interval, race, cross-training.
    """
    from app.services.supabase_client import SupabaseService

    db = SupabaseService()
    activities = db.get_activities(user_id, limit=50, days=days)
    if activity_type:
        activities = [
            a for a in activities if a.get("activity_type") == activity_type
        ]

    summary = {
        "period_days": days,
        "total_activities": len(activities),
        "total_distance_km": round(
            sum(a.get("distance_meters", 0) for a in activities) / 1000, 1
        ),
        "total_duration_hours": round(
            sum(a.get("duration_seconds", 0) for a in activities) / 3600, 1
        ),
        "activity_breakdown": {},
    }
    for a in activities:
        atype = a.get("activity_type", "unknown")
        summary["activity_breakdown"][atype] = (
            summary["activity_breakdown"].get(atype, 0) + 1
        )

    return summary


@tool
def get_readiness(user_id: str) -> dict:
    """Get the current Event Readiness score and components.

    Readiness is independent from projection — it indicates race-day
    preparedness, not structural fitness level.
    """
    from datetime import datetime, timezone

    from app.ml.readiness_engine import ReadinessEngine
    from app.services.supabase_client import SupabaseService

    from app.models.activities import NormalizedActivity

    db = SupabaseService()
    activities_raw = db.get_recent_activities(user_id, days=90)

    if activities_raw:
        activities = [NormalizedActivity.from_db_dict(a) for a in activities_raw]

        from app.services.feature_service import FeatureService

        features = FeatureService.compute_all_features(activities)

        now = datetime.now(timezone.utc)
        days_since_last = None
        days_since_threshold = None
        days_since_long_run = None
        days_since_race = None

        for a in activities:
            ts = a.timestamp
            if not ts:
                continue
            act_time = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            diff = (now - act_time).days
            if days_since_last is None or diff < days_since_last:
                days_since_last = diff
            if a.activity_type == "threshold" and (
                days_since_threshold is None or diff < days_since_threshold
            ):
                days_since_threshold = diff
            if a.activity_type == "long_run" and (
                days_since_long_run is None or diff < days_since_long_run
            ):
                days_since_long_run = diff
            if a.activity_type == "race" and (
                days_since_race is None or diff < days_since_race
            ):
                days_since_race = diff

        if days_since_long_run is None:
            long_runs = [a for a in activities if (a.distance_meters or 0) >= 15000]
            if long_runs:
                last_long = max(long_runs, key=lambda x: x.timestamp)
                lt = last_long.timestamp
                lt = lt if lt.tzinfo else lt.replace(tzinfo=timezone.utc)
                days_since_long_run = (now - lt).days
            else:
                days_since_long_run = 30

        physiology = db.get_recent_physiology(user_id, limit=1)
        sleep_score = (
            physiology[0].get("sleep_score", 75) if physiology else 75
        )

        result = ReadinessEngine.compute_readiness(
            features=features,
            days_since_last_activity=days_since_last or 1,
            days_since_last_threshold=days_since_threshold,
            days_since_last_long_run=days_since_long_run,
            days_since_last_race=days_since_race,
            sleep_score=sleep_score,
        )
    else:
        features = {
            "acwr_4w": 1.1,
            "weekly_load_stddev": 4000,
            "session_density_stability": 0.8,
        }
        result = ReadinessEngine.compute_readiness(
            features=features,
            days_since_last_activity=1,
            days_since_last_threshold=4,
            days_since_last_long_run=5,
            sleep_score=78,
        )

    return {
        "score": result.score,
        "label": result.label,
        "components": result.components,
        "factors": [
            {"factor": f["factor"], "impact": f["impact"]}
            for f in result.factors
        ],
    }


@tool
def get_physiology(user_id: str, days: int = 7) -> dict:
    """Get recent physiological data: resting HR, HRV, sleep trends."""
    from app.services.supabase_client import SupabaseService

    db = SupabaseService()
    entries = db.get_recent_physiology(user_id, limit=days)
    if not entries:
        return {"status": "No physiological data recorded yet", "entries": []}

    hr_entries = [e for e in entries if e.get("resting_hr")]
    avg_hr = (
        round(
            sum(e["resting_hr"] for e in hr_entries) / len(hr_entries), 1
        )
        if hr_entries
        else None
    )

    return {
        "period_days": days,
        "entries_count": len(entries),
        "latest": {
            "resting_hr": entries[0].get("resting_hr"),
            "hrv": entries[0].get("hrv"),
            "sleep_score": entries[0].get("sleep_score"),
        },
        "trends": {
            "resting_hr_avg": avg_hr,
        },
    }


@tool
def search_insights(user_id: str, query: str) -> dict:
    """Search for relevant insights using semantic similarity.

    Searches over embedded projection changes, driver shifts, and patterns
    stored in user_embeddings. Returns the most relevant context.
    """
    from app.services.embedding_service import EmbeddingService

    try:
        results = EmbeddingService().search(user_id, query, match_count=5)
        if results:
            return {
                "status": "found",
                "results": [
                    {
                        "content": r.get("content", ""),
                        "content_type": r.get("content_type", ""),
                        "created_at": r.get("created_at", ""),
                    }
                    for r in results
                ],
                "query": query,
            }
    except Exception:
        pass

    return {
        "status": "Insight search available after more training data is collected",
        "results": [],
        "query": query,
    }


@tool
def compare_periods(
    user_id: str,
    period1_days_ago: int = 28,
    period2_days_ago: int = 0,
    window_days: int = 14,
) -> dict:
    """Compare two training periods side by side.

    Compares volume, intensity distribution, and key metrics between two
    time windows. Useful for understanding what changed.
    """
    from datetime import datetime, timedelta, timezone

    from app.services.supabase_client import SupabaseService

    db = SupabaseService()
    activities = db.get_activities(
        user_id,
        limit=200,
        days=max(period1_days_ago + window_days, 90),
    )

    now = datetime.now(timezone.utc)

    def filter_period(start_days_ago: int, window: int):
        start = now - timedelta(days=start_days_ago + window)
        end = now - timedelta(days=start_days_ago)
        return [
            a
            for a in activities
            if start.isoformat() <= a.get("timestamp", "") <= end.isoformat()
        ]

    p1 = filter_period(period1_days_ago, window_days)
    p2 = filter_period(period2_days_ago, window_days)

    def summarize(acts):
        return {
            "sessions": len(acts),
            "total_km": round(
                sum(a.get("distance_meters", 0) for a in acts) / 1000, 1
            ),
            "total_hours": round(
                sum(a.get("duration_seconds", 0) for a in acts) / 3600, 1
            ),
        }

    return {
        "period_1": {
            "label": f"{period1_days_ago + window_days}-{period1_days_ago} days ago",
            **summarize(p1),
        },
        "period_2": {
            "label": f"Last {window_days} days",
            **summarize(p2),
        },
    }


@tool
def explain_driver(user_id: str, driver_name: str) -> dict:
    """Explain why a specific structural driver changed.

    Provides a narrative explanation of what training patterns are
    driving the change in a specific structural driver.
    """
    driver_explanations = {
        "aerobic_base": {
            "driver": "Aerobic Base",
            "description": (
                "Reflects total aerobic volume — easy and moderate "
                "running distance over rolling windows"
            ),
            "key_features": [
                "Rolling distance (7d, 21d, 42d)",
                "Zone 1 and Zone 2 time percentage",
            ],
            "typical_movers": (
                "Consistent weekly mileage increases, longer long runs, "
                "more easy-pace running"
            ),
        },
        "threshold_density": {
            "driver": "Threshold Density",
            "description": (
                "Measures time spent near lactate turnpoint pace — "
                "zone 4 intensity"
            ),
            "key_features": [
                "Threshold minutes per week",
                "Zone 4 percentage",
            ],
            "typical_movers": (
                "More tempo runs, threshold intervals, comfortably hard "
                "continuous efforts"
            ),
        },
        "speed_exposure": {
            "driver": "Speed Exposure",
            "description": (
                "Measures high-intensity exposure — zone 5 intervals "
                "and race-pace work"
            ),
            "key_features": [
                "Speed exposure minutes per week",
                "Zone 5 percentage",
            ],
            "typical_movers": (
                "Track intervals, repetition work, short hill sprints, "
                "race participation"
            ),
        },
        "load_consistency": {
            "driver": "Load Consistency",
            "description": (
                "Measures training regularity and load stability over time"
            ),
            "key_features": [
                "Weekly load standard deviation",
                "Block variance",
                "Session density stability",
                "ACWR",
            ],
            "typical_movers": (
                "Steady week-to-week volume, avoiding boom-bust cycles, "
                "regular session frequency"
            ),
        },
        "running_economy": {
            "driver": "Running Economy",
            "description": (
                "Reflects metabolic efficiency — pace output relative "
                "to heart rate input"
            ),
            "key_features": [
                "HR drift at sustained pace",
                "Late-session pace decay",
                "Matched HR band pace",
            ],
            "typical_movers": (
                "Strides, drills, consistent easy pace, reduced "
                "late-session fatigue patterns"
            ),
        },
    }

    info = driver_explanations.get(
        driver_name, driver_explanations["aerobic_base"]
    )
    return info


ALL_TOOLS = [
    get_projection,
    get_drivers,
    get_training_history,
    get_readiness,
    get_physiology,
    search_insights,
    compare_periods,
    explain_driver,
]
