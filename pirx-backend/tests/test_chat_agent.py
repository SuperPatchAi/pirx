"""Tests for PIRX Chat Agent: tools, prompts, and agent graph structure."""

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.chat.tools import (
    get_projection,
    get_drivers,
    get_training_history,
    get_readiness,
    get_physiology,
    search_insights,
    compare_periods,
    explain_driver,
    ALL_TOOLS,
)
from app.chat.prompts import PIRX_SYSTEM_PROMPT, INTENT_CLASSIFICATION_PROMPT


class TestTools:
    def test_all_tools_defined(self):
        assert len(ALL_TOOLS) == 8

    def test_tool_names(self):
        names = {t.name for t in ALL_TOOLS}
        assert names == {
            "get_projection",
            "get_drivers",
            "get_training_history",
            "get_readiness",
            "get_physiology",
            "search_insights",
            "compare_periods",
            "explain_driver",
        }

    def test_explain_driver_returns_data(self):
        result = explain_driver.invoke(
            {"user_id": "test", "driver_name": "aerobic_base"}
        )
        assert result["driver"] == "Aerobic Base"
        assert "description" in result

    def test_explain_driver_all_drivers(self):
        for name in [
            "aerobic_base",
            "threshold_density",
            "speed_exposure",
            "load_consistency",
            "running_economy",
        ]:
            result = explain_driver.invoke(
                {"user_id": "test", "driver_name": name}
            )
            assert "driver" in result

    def test_explain_driver_unknown_falls_back(self):
        result = explain_driver.invoke(
            {"user_id": "test", "driver_name": "nonexistent"}
        )
        assert result["driver"] == "Aerobic Base"

    @patch("app.services.embedding_service.EmbeddingService")
    def test_search_insights_stub(self, mock_emb_cls):
        mock_emb = MagicMock()
        mock_emb_cls.return_value = mock_emb
        mock_emb.search.return_value = []
        result = search_insights.invoke(
            {"user_id": "test", "query": "why did my projection improve?"}
        )
        assert "query" in result
        assert result["query"] == "why did my projection improve?"
        assert result["results"] == []

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_readiness_returns_score(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = get_readiness.invoke({"user_id": "test"})
        assert "score" in result
        assert 0 <= result["score"] <= 100
        assert "label" in result
        assert "components" in result
        assert "factors" in result

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_projection_no_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = get_projection.invoke({"user_id": "test", "event": "5000"})
        assert "No projection" in result.get("status", "")

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_projection_with_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "midpoint_seconds": 1182,
                "range_lower": 1155,
                "range_upper": 1208,
                "improvement_since_baseline": 78,
                "twenty_one_day_change": 5,
                "status": "Improving",
                "computed_at": "2026-03-05",
            }
        ]

        result = get_projection.invoke({"user_id": "test", "event": "5000"})
        assert result["projected_time_seconds"] == 1182
        assert result["status"] == "Improving"
        assert "supported_range" in result

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_drivers_no_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = get_drivers.invoke({"user_id": "test"})
        assert result["drivers"] == []

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_drivers_with_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "aerobic_base_seconds": -30,
                "threshold_density_seconds": -15,
                "speed_exposure_seconds": -5,
                "load_consistency_seconds": -10,
                "running_economy_seconds": -8,
                "computed_at": "2026-03-05",
            }
        ]

        result = get_drivers.invoke({"user_id": "test"})
        assert len(result["drivers"]) == 5
        names = [d["name"] for d in result["drivers"]]
        assert "Aerobic Base" in names
        assert "Threshold Density" in names

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_training_history(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "distance_meters": 5000,
                "duration_seconds": 1800,
                "activity_type": "easy",
            },
            {
                "distance_meters": 8000,
                "duration_seconds": 2400,
                "activity_type": "threshold",
            },
        ]

        result = get_training_history.invoke({"user_id": "test", "days": 7})
        assert result["total_activities"] == 2
        assert result["total_distance_km"] == 13.0
        assert "easy" in result["activity_breakdown"]

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_training_history_filtered(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "distance_meters": 5000,
                "duration_seconds": 1800,
                "activity_type": "easy",
            },
            {
                "distance_meters": 8000,
                "duration_seconds": 2400,
                "activity_type": "threshold",
            },
        ]

        result = get_training_history.invoke(
            {"user_id": "test", "days": 7, "activity_type": "easy"}
        )
        assert result["total_activities"] == 1

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_physiology_no_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = get_physiology.invoke({"user_id": "test"})
        assert result["entries"] == []

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_physiology_with_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"resting_hr": 52, "hrv": 65, "sleep_score": 82},
            {"resting_hr": 54, "hrv": 60, "sleep_score": 75},
        ]

        result = get_physiology.invoke({"user_id": "test", "days": 7})
        assert result["entries_count"] == 2
        assert result["latest"]["resting_hr"] == 52

    @patch("app.services.supabase_client.get_supabase_client")
    def test_compare_periods(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = compare_periods.invoke(
            {
                "user_id": "test",
                "period1_days_ago": 28,
                "period2_days_ago": 0,
                "window_days": 14,
            }
        )
        assert "period_1" in result
        assert "period_2" in result
        assert "sessions" in result["period_1"]


class TestPrompts:
    def test_system_prompt_has_terminology(self):
        assert "Projected Time" in PIRX_SYSTEM_PROMPT
        assert "Supported Range" in PIRX_SYSTEM_PROMPT
        assert "Structural Drivers" in PIRX_SYSTEM_PROMPT

    def test_system_prompt_has_driver_names(self):
        assert "Aerobic Base" in PIRX_SYSTEM_PROMPT
        assert "Threshold Density" in PIRX_SYSTEM_PROMPT
        assert "Speed Exposure" in PIRX_SYSTEM_PROMPT
        assert "Load Consistency" in PIRX_SYSTEM_PROMPT
        assert "Running Economy" in PIRX_SYSTEM_PROMPT

    def test_system_prompt_has_banned_terms(self):
        assert "Banned Terms" in PIRX_SYSTEM_PROMPT
        assert "VO2max" in PIRX_SYSTEM_PROMPT

    def test_system_prompt_no_coaching_tone(self):
        assert "NEVER coach" in PIRX_SYSTEM_PROMPT

    def test_intent_prompt_has_categories(self):
        assert "projection" in INTENT_CLASSIFICATION_PROMPT
        assert "training" in INTENT_CLASSIFICATION_PROMPT
        assert "readiness" in INTENT_CLASSIFICATION_PROMPT
        assert "drivers" in INTENT_CLASSIFICATION_PROMPT
        assert "physiology" in INTENT_CLASSIFICATION_PROMPT
        assert "comparison" in INTENT_CLASSIFICATION_PROMPT
        assert "explanation" in INTENT_CLASSIFICATION_PROMPT
        assert "general" in INTENT_CLASSIFICATION_PROMPT

    def test_intent_prompt_is_formattable(self):
        formatted = INTENT_CLASSIFICATION_PROMPT.format(
            message="How fast am I?"
        )
        assert "How fast am I?" in formatted


class TestAgentStructure:
    @patch("app.chat.agent.settings")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_agent_creates(self, mock_client_fn, mock_settings):
        mock_client_fn.return_value = MagicMock()
        mock_settings.google_api_key = "test-key"
        from app.chat.agent import create_agent

        agent = create_agent()
        assert agent is not None

    @patch("app.chat.agent.settings")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_agent_singleton(self, mock_client_fn, mock_settings):
        mock_client_fn.return_value = MagicMock()
        mock_settings.google_api_key = "test-key"
        import app.chat.agent as agent_module

        agent_module._agent = None
        a1 = agent_module.get_agent()
        a2 = agent_module.get_agent()
        assert a1 is a2
        agent_module._agent = None

    @patch("app.chat.agent.settings")
    @patch("app.services.supabase_client.get_supabase_client")
    def test_agent_has_nodes(self, mock_client_fn, mock_settings):
        mock_client_fn.return_value = MagicMock()
        mock_settings.google_api_key = "test-key"
        from app.chat.agent import create_agent

        agent = create_agent()
        graph_nodes = agent.get_graph().nodes
        assert "agent" in graph_nodes
        assert "tools" in graph_nodes
        assert "classify_intent" in graph_nodes
        assert "generate_response" in graph_nodes

    def test_agent_state_type(self):
        from app.chat.agent import AgentState

        assert "messages" in AgentState.__annotations__
        assert "user_id" in AgentState.__annotations__
