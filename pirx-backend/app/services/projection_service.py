from app.ml.projection_engine import ProjectionEngine, ProjectionState
from app.ml.event_scaling import EventScaler
from app.ml.baseline_estimator import estimate_5k_baseline
from app.ml.reference_population import estimate_5k_cold_start_knn
from app.services.supabase_client import SupabaseService
from app.services.driver_service import DriverService
from app.services.embedding_service import EmbeddingService
from app.services.notification_service import NotificationService
from app.services.model_orchestrator import ModelOrchestrator
from typing import Optional
import logging

logger = logging.getLogger(__name__)

STANDARD_EVENTS = {
    "1500": 1500, "3000": 3000, "5000": 5000,
    "10000": 10000, "21097": 21097, "42195": 42195,
}


class ProjectionService:
    """Orchestrates projection recomputation end-to-end."""

    def __init__(self):
        self.db = SupabaseService()
        self.driver_service = DriverService()
        self.engine = ProjectionEngine()
        self.orchestrator = ModelOrchestrator()

    def recompute(self, user_id: str, event: str, features: dict) -> Optional[ProjectionState]:
        """Full recompute pipeline for a single event.

        1. Load baseline and previous projection
        2. Compute new projection + drivers
        3. Check structural shift (>= 2s)
        4. If shifted: store, embed, notify
        """
        try:
            user_data = self.db.get_user(user_id) or {}
            manual_baseline = user_data.get("baseline_time_seconds")
            baseline_event = user_data.get("baseline_event") or "5000"
            baseline_source = user_data.get("baseline_source") or ""

            ml_baseline = self._estimate_baseline(user_id)
            ml_is_default = abs(ml_baseline - 1500.0) < 1

            if ml_is_default and manual_baseline:
                raw_baseline = manual_baseline
            elif not ml_is_default:
                raw_baseline = ml_baseline
                baseline_event = "5000"
            elif manual_baseline:
                raw_baseline = manual_baseline
            else:
                raw_baseline = ml_baseline
                baseline_event = "5000"
        except Exception:
            raw_baseline = self._estimate_baseline(user_id)
            baseline_event = "5000"

        baseline_distance = STANDARD_EVENTS.get(baseline_event, 5000)
        target_distance = STANDARD_EVENTS.get(event, 5000)
        if baseline_distance != target_distance:
            baseline_time = EventScaler.riegel_scale(
                raw_baseline, baseline_distance, target_distance,
            )
        else:
            baseline_time = raw_baseline

        try:
            prev_row = self.db.get_latest_projection(user_id, event)
            if prev_row and prev_row.get("midpoint_seconds"):
                previous_state = ProjectionState(
                    projected_time_seconds=prev_row["midpoint_seconds"],
                    supported_range_low=prev_row.get("range_low_seconds") or 0,
                    supported_range_high=prev_row.get("range_high_seconds") or 0,
                    baseline_time_seconds=prev_row.get("baseline_seconds") or baseline_time,
                )
            else:
                previous_state = None
        except Exception:
            previous_state = None

        model_decision = self.orchestrator.select_projection_model(
            user_id=user_id,
            event=event,
            features=features,
        )
        if model_decision.model_type != "deterministic":
            logger.info(
                "Model '%s' selected for user=%s event=%s but not yet enabled in projection serving; using deterministic fallback",
                model_decision.model_type,
                user_id,
                event,
            )

        new_state, driver_states = self.driver_service.compute_and_store_drivers(
            user_id=user_id,
            event=event,
            baseline_time_s=baseline_time,
            features=features,
            previous_projection=previous_state,
        )

        if self.engine.check_structural_shift(new_state, previous_state):
            old_time = previous_state.projected_time_seconds if previous_state else baseline_time
            improvement = old_time - new_state.projected_time_seconds

            try:
                embed_svc = EmbeddingService()
                embed_svc.embed_projection_change(
                    user_id=user_id,
                    event=event,
                    old_time_s=old_time,
                    new_time_s=new_state.projected_time_seconds,
                    improvement_s=improvement,
                )
            except Exception:
                logger.warning("Failed to embed projection change", exc_info=True)

            try:
                notif_svc = NotificationService()
                payload = notif_svc.check_projection_update(
                    user_id=user_id,
                    event=event,
                    old_time_s=old_time,
                    new_time_s=new_state.projected_time_seconds,
                )
                if payload:
                    notif_svc.dispatch(user_id, payload)
            except Exception:
                logger.warning("Failed to send projection notification", exc_info=True)

        return new_state

    def _estimate_baseline(self, user_id: str) -> float:
        """Estimate a 5K race-pace baseline from recent activities.

        Uses multi-signal tiered estimation (race detection, sustained effort,
        P10 pace, adjusted median) instead of naive median training pace.
        """
        try:
            activities = self.db.get_recent_activities(user_id, days=180)
            baseline = estimate_5k_baseline(activities)
            if abs(baseline - 1500.0) < 1:
                knn_cold_start = estimate_5k_cold_start_knn(activities)
                if knn_cold_start is not None:
                    return knn_cold_start
            return baseline
        except Exception:
            logger.warning("Failed to estimate baseline for user %s, using default", user_id)
            return 1500.0

    def recompute_all_events(self, user_id: str, features: dict) -> dict:
        """Recompute projections for all 6 events."""
        events = ["1500", "3000", "5000", "10000", "21097", "42195"]
        results = {}
        for event in events:
            try:
                state = self.recompute(user_id, event, features)
                if state:
                    results[event] = {
                        "status": "updated",
                        "projected_time": state.projected_time_seconds,
                    }
                else:
                    results[event] = {"status": "failed"}
            except Exception as e:
                results[event] = {"status": "error", "error": str(e)}
        return results
