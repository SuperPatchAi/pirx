from app.ml.projection_engine import ProjectionEngine, ProjectionState
from app.ml.event_scaling import EventScaler
from app.services.supabase_client import SupabaseService
from app.services.driver_service import DriverService
from app.services.embedding_service import EmbeddingService
from app.services.notification_service import NotificationService
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

    def recompute(self, user_id: str, event: str, features: dict) -> Optional[ProjectionState]:
        """Full recompute pipeline for a single event.

        1. Load baseline and previous projection
        2. Compute new projection + drivers
        3. Check structural shift (>= 2s)
        4. If shifted: store, embed, notify
        """
        try:
            user_data = self.db.get_user(user_id) or {}
            raw_baseline = user_data.get("baseline_time_seconds")
            baseline_event = user_data.get("baseline_event") or "5000"
            if not raw_baseline:
                raw_baseline = self._estimate_baseline(user_id)
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
        """Estimate a 5K baseline from recent activity pace when onboarding hasn't been completed.

        Uses the runner's median pace over recent activities to project a 5K time.
        Falls back to 25:00 (1500s) if no usable data exists.
        """
        DEFAULT_5K = 1500.0
        try:
            activities = self.db.get_recent_activities(user_id, days=90)
            paces = []
            for a in activities:
                pace = a.get("avg_pace_sec_per_km")
                if pace is not None:
                    pace = float(pace)
                dist = float(a.get("distance_meters") or 0)
                dur = float(a.get("duration_seconds") or 0)
                if pace is None and dist > 0 and dur > 0:
                    pace = dur / (dist / 1000)
                if pace and 223 <= pace <= 900 and dist > 1600:
                    paces.append(pace)
            if len(paces) < 3:
                return DEFAULT_5K
            paces.sort()
            median_pace = paces[len(paces) // 2]
            estimated = median_pace * 5.0
            logger.info(
                "Estimated 5K baseline for user %s: %.0fs (median pace %.0f s/km from %d activities)",
                user_id, estimated, median_pace, len(paces),
            )
            return estimated
        except Exception:
            logger.warning("Failed to estimate baseline for user %s, using default", user_id)
            return DEFAULT_5K

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
