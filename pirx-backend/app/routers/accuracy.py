import logging

import numpy as np
from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()

BENCHMARK_MAE = 7.0

DISTANCE_TO_EVENT = {
    (1400, 1600): "1500",
    (2900, 3100): "3000",
    (4900, 5200): "5000",
    (9800, 10200): "10000",
    (20900, 21300): "21097",
    (41900, 42500): "42195",
}


@router.get("")
async def get_global_accuracy():
    """Get latest global model accuracy metrics."""
    try:
        db = SupabaseService()
        result = (
            db.client.table("model_metrics")
            .select("*")
            .eq("model_type", "global")
            .order("metric_date", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            return {
                "mae_seconds": row.get("mae_seconds"),
                "bias_seconds": row.get("bias_seconds"),
                "bland_altman_lower": row.get("bland_altman_lower"),
                "bland_altman_upper": row.get("bland_altman_upper"),
                "sample_size": row.get("sample_size"),
                "meets_benchmark": (row.get("mae_seconds") or 999) <= BENCHMARK_MAE,
                "benchmark_target": BENCHMARK_MAE,
                "metric_date": row.get("metric_date"),
            }
        return {"mae_seconds": None, "sample_size": 0, "meets_benchmark": False, "benchmark_target": BENCHMARK_MAE}
    except Exception:
        logger.exception("Failed to get accuracy metrics")
        return {"mae_seconds": None, "sample_size": 0, "meets_benchmark": False, "benchmark_target": BENCHMARK_MAE}


@router.get("/user")
async def get_user_accuracy(user: dict = Depends(get_current_user)):
    """Get user-specific prediction accuracy."""
    try:
        db = SupabaseService()
        races = db.get_race_activities(user["user_id"])
        if not races:
            return {"races": [], "mae_seconds": None, "sample_size": 0}

        comparisons = []
        errors = []

        for race in races[:20]:
            distance = race.get("distance_meters", 0)
            actual = race.get("duration_seconds", 0)
            if not distance or not actual:
                continue

            event = None
            for (low, high), ev in DISTANCE_TO_EVENT.items():
                if low <= distance <= high:
                    event = ev
                    break
            if not event:
                continue

            proj = db.get_latest_projection(user["user_id"], event)
            if not proj or not proj.get("midpoint_seconds"):
                continue

            projected = proj["midpoint_seconds"]
            error = actual - projected
            errors.append(abs(error))

            comparisons.append({
                "race_date": race.get("timestamp", "")[:10],
                "event": event,
                "actual_seconds": actual,
                "projected_seconds": projected,
                "error_seconds": round(error, 1),
            })

        mae = float(np.mean(errors)) if errors else None

        return {
            "races": comparisons,
            "mae_seconds": round(mae, 1) if mae else None,
            "sample_size": len(errors),
            "meets_benchmark": (mae or 999) <= BENCHMARK_MAE,
        }
    except Exception:
        logger.exception("Failed to get user accuracy")
        return {"races": [], "mae_seconds": None, "sample_size": 0}
