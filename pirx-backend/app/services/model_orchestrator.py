"""Model selection orchestration for projection serving.

Current production policy is deterministic-first while ML paths are rolled out.
This service provides a single decision seam for gradual enablement.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelDecision:
    model_type: str
    reason: str
    confidence: Optional[float] = None


class ModelOrchestrator:
    """Selects which projection model path should be used."""

    def select_projection_model(
        self,
        user_id: str,
        event: str,
        features: dict,
    ) -> ModelDecision:
        # Deterministic is the active production path; ML paths are phased in.
        return ModelDecision(
            model_type="deterministic",
            reason="default_production_path",
            confidence=None,
        )
