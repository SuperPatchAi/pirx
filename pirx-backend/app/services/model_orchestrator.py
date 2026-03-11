"""Model selection orchestration for projection serving.

Current production policy is deterministic-first while ML paths are rolled out.
This service provides a single decision seam for gradual enablement.
"""

from dataclasses import dataclass
from typing import Optional
import hashlib

from app.config import settings
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
                    if family == "lstm":
                        if not settings.enable_lstm_serving:
                            return ModelDecision(
                                model_type="deterministic",
                                reason="lstm_feature_disabled",
                                confidence=None,
                            )
                        if not self._is_user_in_rollout(
                            user_id, settings.lstm_serving_rollout_percentage
                        ):
                            return ModelDecision(
                                model_type="deterministic",
                                reason="lstm_rollout_gate",
                                confidence=None,
                            )
                    if family == "knn" and not settings.enable_knn_serving:
                        return ModelDecision(
                            model_type="deterministic",
                            reason="knn_feature_disabled",
                            confidence=None,
                        )
                    metadata = active.get("metadata") or {}
                    return ModelDecision(
                        model_type=family,
                        reason="active_model_registry",
                        confidence=metadata.get("promotion_confidence"),
                    )
        except Exception:
            return ModelDecision(model_type="deterministic", reason="selector_error", confidence=None)

        return ModelDecision(model_type="deterministic", reason="default_production_path", confidence=None)

    @staticmethod
    def _is_user_in_rollout(user_id: str, rollout_percentage: int) -> bool:
        pct = max(0, min(int(rollout_percentage), 100))
        if pct >= 100:
            return True
        if pct <= 0:
            return False
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < pct
