import pytest
from unittest.mock import MagicMock, patch

from app.services.embedding_service import EMBEDDING_DIMENSIONS, EmbeddingService


@pytest.fixture
def mock_openai():
    with patch("app.services.embedding_service.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        yield mock_settings


@pytest.fixture
def mock_db():
    with patch("app.services.embedding_service.SupabaseService") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1}
        ]
        mock_instance.client.rpc.return_value.execute.return_value.data = [
            {
                "id": 1,
                "content": "test content",
                "content_type": "insight",
                "similarity": 0.95,
            }
        ]
        mock_cls.return_value = mock_instance
        yield mock_instance


class TestEmbeddingGeneration:
    def test_no_api_key_returns_zeros(self, mock_openai, mock_db):
        svc = EmbeddingService()
        embedding = svc.generate_embedding("test")
        assert len(embedding) == EMBEDDING_DIMENSIONS
        assert all(v == 0.0 for v in embedding)

    def test_embedding_dimensions(self, mock_openai, mock_db):
        svc = EmbeddingService()
        embedding = svc.generate_embedding("test text")
        assert len(embedding) == 1536


class TestStoreEmbedding:
    def test_store_calls_insert(self, mock_openai, mock_db):
        svc = EmbeddingService()
        result = svc.store_embedding("u1", "content", "insight")
        assert result["id"] == 1
        mock_db.client.table.assert_called_with("user_embeddings")


class TestSearch:
    def test_search_calls_rpc(self, mock_openai, mock_db):
        svc = EmbeddingService()
        results = svc.search("u1", "why did my projection improve?")
        assert len(results) == 1
        assert results[0]["similarity"] == 0.95
        mock_db.client.rpc.assert_called_once()


class TestEmbedOnWrite:
    def test_embed_projection_change(self, mock_openai, mock_db):
        svc = EmbeddingService()
        result = svc.embed_projection_change("u1", "5000", 1260, 1200, 60)
        assert result["id"] == 1

    def test_embed_driver_shift(self, mock_openai, mock_db):
        svc = EmbeddingService()
        result = svc.embed_driver_shift("u1", "aerobic_base", 10.0, 15.0)
        assert result["id"] == 1

    def test_embed_insight(self, mock_openai, mock_db):
        svc = EmbeddingService()
        result = svc.embed_insight("u1", "Your Aerobic Base has been consistently improving")
        assert result["id"] == 1

    def test_embed_activity_summary(self, mock_openai, mock_db):
        svc = EmbeddingService()
        result = svc.embed_activity_summary("u1", "easy", 10.0, 55, avg_hr=140)
        assert result["id"] == 1

    def test_projection_content_format(self, mock_openai, mock_db):
        svc = EmbeddingService()
        svc.store_embedding = MagicMock(return_value={"id": 1})
        svc.embed_projection_change("u1", "5000", 1260, 1200, 60)
        call_args = svc.store_embedding.call_args
        content = (
            call_args[1]["content"]
            if "content" in call_args[1]
            else call_args[0][1]
        )
        assert "improved" in content
        assert "5000m" in content

    def test_driver_shift_content_format(self, mock_openai, mock_db):
        svc = EmbeddingService()
        svc.store_embedding = MagicMock(return_value={"id": 1})
        svc.embed_driver_shift("u1", "threshold_density", 5.0, 10.0)
        call_args = svc.store_embedding.call_args
        content = (
            call_args[1]["content"]
            if "content" in call_args[1]
            else call_args[0][1]
        )
        assert "Threshold Density" in content
        assert "increased" in content


class TestFormatTime:
    def test_format_time(self):
        assert EmbeddingService._format_time(1182) == "19:42"
        assert EmbeddingService._format_time(300) == "5:00"
        assert EmbeddingService._format_time(90) == "1:30"
