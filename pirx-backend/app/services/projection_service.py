from app.ml.projection_engine import ProjectionEngine, ProjectionState
from app.services.supabase_client import SupabaseService
from app.services.driver_service import DriverService
from app.services.embedding_service import EmbeddingService
from app.services.notification_service import NotificationService
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ProjectionService:
    """Orchestrates projection recomputation end-to-end."""

    def __init__(self):
        self.db = SupabaseService()
        self.driver_service = DriverService()
        self.engine = ProjectionEngine()

    def recompute(self, user_id: str, event: str, features: dict) -> Optional[ProjectionState]:
        """Full recompute pipeline for a single event.

        1. Load baseline and previous projection
        2. Compute new projection + drivers
        3. Check structural shift (>= 2s)
        4. If shifted: store, embed, notify
        """
        try:
            user_data = self.db.get_user(user_id)
            baseline_time = user_data.get("baseline_time_seconds", 1260.0) if user_data else 1260.0
        except Exception:
            baseline_time = 1260.0

        try:
            prev_row = self.db.get_latest_projection(user_id, event)
            previous_state = ProjectionState(
                projected_time_seconds=prev_row["midpoint_seconds"],
                supported_range_low=prev_row.get("range_low_seconds", 0),
                supported_range_high=prev_row.get("range_high_seconds", 0),
                baseline_time_seconds=prev_row.get("baseline_seconds", baseline_time),
            ) if prev_row else None
        except Exception:
            previous_state = None

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
                logger.warning("Failed to embed projection change")

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
                logger.warning("Failed to send projection notification")

        return new_state

    def recompute_all_events(self, user_id: str, features: dict) -> dict:
        """Recompute projections for all 4 events."""
        events = ["1500", "3000", "5000", "10000"]
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
