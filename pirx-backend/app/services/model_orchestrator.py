"""Model selection orchestration for projection serving.

Current production policy is deterministic-first while ML paths are rolled out.
This service provides a single decision seam for gradual enablement.
"""

from dataclasses import dataclass
from typing import Optional

from app.services.supabase_client import SupabaseService


@dataclass
class ModelDecision:
    model_type: str
    reason: str
    confidence: Optional[float] = None


class ModelOrchestrator:
    """Selects which projection model path should be used."""

    def __init__(self):
        self.db = SupabaseService()

    def select_projection_model(
        self,
        user_id: str,
        event: str,
        features: dict,
    ) -> ModelDecision:
        # Deterministic is the active production path; ML paths are phased in.
        try:
            active = self.db.get_active_model(user_id, event)
            if active:
                family = active.get("model_family")
                if family in {"lstm", "knn"}:
                    return ModelDecision(
                        model_type=family,
                        reason="active_model_registry",
                        confidence=None,
                    )
        except Exception:
            return ModelDecision(model_type="deterministic", reason="selector_error", confidence=None)

        return ModelDecision(model_type="deterministic", reason="default_production_path", confidence=None)
