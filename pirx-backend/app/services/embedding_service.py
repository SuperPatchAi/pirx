"""Embedding service for PIRX RAG pipeline.

Handles:
1. Generating embeddings via OpenAI text-embedding-3-small
2. Storing embeddings in user_embeddings table
3. Semantic search via the query_embeddings database function
4. Embed-on-write hooks for projection changes, driver shifts, etc.
"""
from typing import Optional

from app.config import settings
from app.services.supabase_client import SupabaseService


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Manages embeddings for the RAG pipeline."""

    def __init__(self):
        self.db = SupabaseService()
        self._client = None

    @property
    def openai_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=settings.openai_api_key or "sk-mock")
        return self._client

    def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        if not settings.openai_api_key:
            return [0.0] * EMBEDDING_DIMENSIONS

        response = self.openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    def store_embedding(
        self,
        user_id: str,
        content: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Generate and store an embedding for content."""
        embedding = self.generate_embedding(content)

        data = {
            "user_id": user_id,
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {},
            "embedding": embedding,
        }

        result = self.db.client.table("user_embeddings").insert(data).execute()
        return result.data[0] if result.data else data

    def search(
        self,
        user_id: str,
        query: str,
        match_count: int = 5,
    ) -> list[dict]:
        """Search for similar embeddings using cosine similarity.

        Uses the query_embeddings database function.
        """
        query_embedding = self.generate_embedding(query)

        result = self.db.client.rpc(
            "query_embeddings",
            {
                "query_embedding": query_embedding,
                "match_user_id": user_id,
                "match_count": match_count,
            },
        ).execute()

        return result.data if result.data else []

    # --- Embed-on-write hooks ---

    def embed_projection_change(
        self,
        user_id: str,
        event: str,
        old_time_s: float,
        new_time_s: float,
        improvement_s: float,
    ) -> dict:
        """Embed a projection change event."""
        delta = old_time_s - new_time_s
        direction = "improved" if delta > 0 else "regressed"

        content = (
            f"Projection {direction} for {event}m: "
            f"moved from {self._format_time(old_time_s)} to {self._format_time(new_time_s)} "
            f"({abs(delta):.1f}s {direction}). "
            f"Total improvement since baseline: {improvement_s:.1f}s."
        )

        return self.store_embedding(
            user_id=user_id,
            content=content,
            content_type="projection_change",
            metadata={
                "event": event,
                "old_time_s": old_time_s,
                "new_time_s": new_time_s,
                "delta_s": delta,
            },
        )

    def embed_driver_shift(
        self,
        user_id: str,
        driver_name: str,
        old_contribution_s: float,
        new_contribution_s: float,
    ) -> dict:
        """Embed a driver shift event."""
        delta = new_contribution_s - old_contribution_s
        direction = "increased" if delta > 0 else "decreased"

        display_names = {
            "aerobic_base": "Aerobic Base",
            "threshold_density": "Threshold Density",
            "speed_exposure": "Speed Exposure",
            "load_consistency": "Load Consistency",
            "running_economy": "Running Economy",
        }
        display = display_names.get(driver_name, driver_name)

        content = (
            f"{display} driver {direction}: "
            f"contribution moved from {old_contribution_s:.1f}s to {new_contribution_s:.1f}s "
            f"({abs(delta):.1f}s shift)."
        )

        return self.store_embedding(
            user_id=user_id,
            content=content,
            content_type="driver_shift",
            metadata={"driver_name": driver_name, "delta_s": delta},
        )

    def embed_insight(
        self,
        user_id: str,
        insight_text: str,
        insight_type: str = "pattern",
    ) -> dict:
        """Embed a generated insight."""
        return self.store_embedding(
            user_id=user_id,
            content=insight_text,
            content_type="insight",
            metadata={"insight_type": insight_type},
        )

    def embed_activity_summary(
        self,
        user_id: str,
        activity_type: str,
        distance_km: float,
        duration_min: float,
        avg_hr: Optional[int] = None,
    ) -> dict:
        """Embed an activity summary for RAG retrieval."""
        hr_str = f", avg HR {avg_hr}bpm" if avg_hr else ""
        content = (
            f"{activity_type.title()} run: {distance_km:.1f}km in {duration_min:.0f} minutes{hr_str}."
        )

        return self.store_embedding(
            user_id=user_id,
            content=content,
            content_type="activity_summary",
            metadata={
                "activity_type": activity_type,
                "distance_km": distance_km,
                "duration_min": duration_min,
            },
        )

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
