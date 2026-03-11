from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.config import settings
from app.services.supabase_client import SupabaseService

router = APIRouter()


@router.get("/config")
async def get_rollout_config():
    return {
        "enable_lstm_serving": settings.enable_lstm_serving,
        "enable_knn_serving": settings.enable_knn_serving,
        "lstm_serving_rollout_percentage": settings.lstm_serving_rollout_percentage,
    }


@router.get("/metrics")
async def get_serving_metrics(days: int = Query(default=7, ge=1, le=90)):
    db = SupabaseService()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        db.client.table("model_metrics")
        .select("metric_type,model_type,event")
        .eq("metric_type", "model_serving_decision")
        .gte("computed_at", since)
        .order("computed_at", desc=True)
        .limit(5000)
        .execute()
    )
    rows = result.data or []

    event_counts: dict[str, int] = {}
    model_type_counts: dict[str, int] = {}
    for row in rows:
        event = str(row.get("event") or "unknown")
        model_type = str(row.get("model_type") or "unknown")
        event_counts[event] = event_counts.get(event, 0) + 1
        model_type_counts[model_type] = model_type_counts.get(model_type, 0) + 1

    return {
        "window_days": days,
        "total_decisions": len(rows),
        "event_counts": event_counts,
        "model_type_counts": model_type_counts,
    }


@router.get("/release-readiness")
async def get_release_readiness(days: int = Query(default=7, ge=1, le=90)):
    metrics = await get_serving_metrics(days=days)
    gates = {
        "enable_lstm_serving": settings.enable_lstm_serving,
        "enable_knn_serving": settings.enable_knn_serving,
        "lstm_serving_rollout_percentage": settings.lstm_serving_rollout_percentage,
    }
    checks = {
        "has_serving_decisions": metrics["total_decisions"] > 0,
        "lstm_flag_enabled": bool(gates["enable_lstm_serving"]),
        "rollout_percentage_valid": 0 <= int(gates["lstm_serving_rollout_percentage"]) <= 100,
    }
    return {
        "gates": gates,
        "serving_metrics": metrics,
        "checks": checks,
        "ready": all(checks.values()),
    }
