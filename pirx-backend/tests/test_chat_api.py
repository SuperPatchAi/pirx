import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.dependencies import get_current_user


@pytest.fixture(autouse=True)
def mock_auth():
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user", "email": "test@test.com"}
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestChatEndpoint:
    @patch("app.chat.agent.get_agent")
    def test_chat_returns_response(self, mock_agent_fn, client):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="Your 5K Projected Time is 19:42."),
            ]
        }
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "What is my projection?"})
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "thread_id" in data
        assert "19:42" in data["response"]

    @patch("app.chat.agent.get_agent")
    def test_chat_creates_thread(self, mock_agent_fn, client):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [AIMessage(content="Hello!")]
        }
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 200
        assert r.json()["thread_id"]

    def test_chat_fallback_on_error(self, client):
        with patch("app.chat.agent.get_agent", side_effect=Exception("No API key")):
            r = client.post("/chat", json={"message": "hello"})
            assert r.status_code == 200
            assert "unable" in r.json()["response"].lower()


class TestThreadManagement:
    def test_create_thread(self, client):
        r = client.post("/chat/thread")
        assert r.status_code == 200
        assert "thread_id" in r.json()

    def test_get_history_empty(self, client):
        r = client.post("/chat/thread")
        thread_id = r.json()["thread_id"]
        r2 = client.get(f"/chat/history?thread_id={thread_id}")
        assert r2.status_code == 200
        assert r2.json()["messages"] == []

    def test_delete_thread(self, client):
        r = client.post("/chat/thread")
        thread_id = r.json()["thread_id"]
        r2 = client.delete(f"/chat/thread/{thread_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"

    @patch("app.chat.agent.get_agent")
    def test_history_has_messages_after_chat(self, mock_agent_fn, client):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [AIMessage(content="Response")]
        }
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "test"})
        thread_id = r.json()["thread_id"]

        r2 = client.get(f"/chat/history?thread_id={thread_id}")
        msgs = r2.json()["messages"]
        assert len(msgs) == 2  # user + assistant
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"


class TestStreamEndpoint:
    @patch("app.chat.agent.get_agent")
    def test_stream_returns_sse(self, mock_agent_fn, client):
        mock_agent = MagicMock()
        mock_agent.stream.return_value = [
            {"messages": [AIMessage(content="Hello")]},
            {"messages": [AIMessage(content="Hello world")]},
        ]
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat/stream", json={"message": "hi"})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
