import logging

from app.ml.projection_engine import ProjectionEngine, ProjectionState, DriverState, DRIVER_NAMES
from app.ml.shap_explainer import SHAPExplainer
from app.services.supabase_client import SupabaseService
from typing import Optional

logger = logging.getLogger(__name__)


class DriverService:
    """Computes driver contributions and stores immutable driver states."""

    def __init__(self):
        self.db = SupabaseService()
        self.engine = ProjectionEngine()

    def compute_and_store_drivers(
        self,
        user_id: str,
        event: str,
        baseline_time_s: float,
        features: dict,
        previous_projection=None,
        model_type: str = "deterministic",
        fallback_reason: str | None = None,
        model_confidence: float | None = None,
        projected_time_override: float | None = None,
    ) -> tuple:
        """Compute projection + drivers and store to DB.

        Only stores a new row when the projection has shifted by >= 2 seconds
        from the previous value, preventing the dampening feedback loop that
        causes projections to drift on repeated recomputes of unchanged data.

        Returns (ProjectionState, list[DriverState])
        """
        projection_state, driver_states = self.engine.compute_projection(
            user_id=user_id,
            event=event,
            baseline_time_s=baseline_time_s,
            features=features,
            previous_state=previous_projection,
        )

        if projected_time_override is not None:
            projection_state, driver_states = self._apply_projection_override(
                projection_state=projection_state,
                driver_states=driver_states,
                baseline_time_s=baseline_time_s,
                projected_time_override=projected_time_override,
                previous_projection=previous_projection,
            )

        if not self.engine.validate_driver_sum(
            driver_states, projection_state.total_improvement_seconds
        ):
            raise ValueError(
                f"Driver sum validation failed: drivers sum to "
                f"{sum(d.contribution_seconds for d in driver_states)}, "
                f"expected {projection_state.total_improvement_seconds}"
            )

        if not self.engine.check_structural_shift(projection_state, previous_projection):
            logger.info(
                "Projection for user %s event %s unchanged (<2s shift), skipping storage",
                user_id, event,
            )
            return projection_state, driver_states

        twenty_one_day_change = None
        try:
            from datetime import datetime, timedelta, timezone
            cutoff = (datetime.now(timezone.utc) - timedelta(days=21)).isoformat()
            old_proj = (
                self.db.client.table("projection_state")
                .select("midpoint_seconds")
                .eq("user_id", user_id)
                .eq("event", event)
                .lte("computed_at", cutoff)
                .order("computed_at", desc=True)
                .limit(1)
                .execute()
            )
            old_time = None
            if old_proj.data:
                candidate = old_proj.data[0].get("midpoint_seconds")
                if candidate:
                    old_time = candidate
            elif previous_projection and previous_projection.projected_time_seconds:
                # Fallback when 21-day anchor is not available yet (newly created
                # event rows): use the prior snapshot so UI can show a real delta.
                old_time = previous_projection.projected_time_seconds

            if old_time and old_time > 0:
                twenty_one_day_change = round(
                    old_time - projection_state.projected_time_seconds, 2
                )
        except Exception:
            pass

        projection_id = None
        try:
            proj_result = self.db.insert_projection({
                "user_id": user_id,
                "event": event,
                "model_type": model_type,
                "model_confidence": model_confidence,
                "fallback_reason": fallback_reason,
                "midpoint_seconds": projection_state.projected_time_seconds,
                "range_low_seconds": projection_state.supported_range_low,
                "range_high_seconds": projection_state.supported_range_high,
                "range_lower": projection_state.supported_range_low,
                "range_upper": projection_state.supported_range_high,
                "baseline_seconds": projection_state.baseline_time_seconds,
                "improvement_since_baseline": projection_state.total_improvement_seconds,
                "volatility": projection_state.volatility,
                "volatility_score": projection_state.volatility,
                "confidence_score": max(0.0, 1.0 - projection_state.volatility / (projection_state.projected_time_seconds or 1)),
                "twenty_one_day_change": twenty_one_day_change,
            })
            projection_id = proj_result.get("projection_id")
        except Exception:
            logger.exception("Failed to insert projection state for user %s", user_id)

        if not projection_id:
            logger.warning(
                "Skipping driver_state insert for user %s event %s — no projection_id",
                user_id, event,
            )
            return projection_state, driver_states

        driver_row = {"user_id": user_id, "event": event, "projection_id": projection_id}
        for ds in driver_states:
            driver_row[f"{ds.driver_name}_seconds"] = ds.contribution_seconds
            driver_row[f"{ds.driver_name}_score"] = ds.score
            driver_row[f"{ds.driver_name}_trend"] = ds.trend

        try:
            self.db.insert_driver_state(driver_row)
        except Exception:
            logger.exception("Failed to insert driver state for user %s", user_id)

        return projection_state, driver_states

    def _apply_projection_override(
        self,
        projection_state: ProjectionState,
        driver_states: list[DriverState],
        baseline_time_s: float,
        projected_time_override: float,
        previous_projection=None,
    ) -> tuple[ProjectionState, list[DriverState]]:
        target_projected = max(60.0, float(projected_time_override))
        target_improvement = round(baseline_time_s - target_projected, 2)

        if not driver_states:
            return projection_state, driver_states

        current_total = sum(d.contribution_seconds for d in driver_states)
        updated_drivers: list[DriverState] = []

        if abs(current_total) < 1e-6:
            even = round(target_improvement / len(driver_states), 2)
            running = 0.0
            for idx, state in enumerate(driver_states):
                if idx == len(driver_states) - 1:
                    contrib = round(target_improvement - running, 2)
                else:
                    contrib = even
                    running += contrib
                updated_drivers.append(
                    DriverState(
                        user_id=state.user_id,
                        event=state.event,
                        driver_name=state.driver_name,
                        contribution_seconds=contrib,
                        score=state.score,
                        trend=state.trend,
                    )
                )
        else:
            scale = target_improvement / current_total
            running = 0.0
            for idx, state in enumerate(driver_states):
                if idx == len(driver_states) - 1:
                    contrib = round(target_improvement - running, 2)
                else:
                    contrib = round(state.contribution_seconds * scale, 2)
                    running += contrib
                updated_drivers.append(
                    DriverState(
                        user_id=state.user_id,
                        event=state.event,
                        driver_name=state.driver_name,
                        contribution_seconds=contrib,
                        score=state.score,
                        trend=state.trend,
                    )
                )

        width = max(0.0, projection_state.supported_range_high - projection_state.supported_range_low)
        range_half = width / 2.0
        volatility = 0.0
        if previous_projection and previous_projection.projected_time_seconds:
            volatility = abs(target_projected - previous_projection.projected_time_seconds)

        adjusted_state = ProjectionState(
            user_id=projection_state.user_id,
            event=projection_state.event,
            projected_time_seconds=round(target_projected, 2),
            supported_range_low=round(max(60.0, target_projected - range_half), 2),
            supported_range_high=round(target_projected + range_half, 2),
            baseline_time_seconds=baseline_time_s,
            total_improvement_seconds=round(target_improvement, 2),
            volatility=round(volatility, 2),
        )
        return adjusted_state, updated_drivers

    def get_driver_explanation(
        self,
        driver_name: str,
        features: dict,
        previous_features: Optional[dict] = None,
    ):
        return SHAPExplainer.explain_driver(driver_name, features, previous_features)

    def classify_stability(self, driver_name: str, history: list[dict]) -> str:
        """Classify driver stability from history: Stable / Active / Declining."""
        if len(history) < 3:
            return "Active"
        scores = [h.get(f"{driver_name}_score") or 50 for h in history[-6:]]
        if len(scores) < 2:
            return "Active"
        import numpy as np

        std = np.std(scores)
        trend = scores[-1] - scores[0]
        if std < 3:
            return "Stable"
        elif trend < -5:
            return "Declining"
        return "Active"
