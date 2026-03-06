import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
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
    @patch("app.routers.chat.SupabaseService")
    @patch("app.chat.agent.get_agent")
    def test_chat_returns_response(self, mock_agent_fn, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.get_chat_thread.return_value = None
        mock_db.create_chat_thread.return_value = {}
        mock_db.insert_chat_message.return_value = {}
        mock_db.get_chat_messages.return_value = [
            {"role": "user", "content": "What is my projection?"},
        ]
        mock_db_cls.return_value = mock_db

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="Your 5K Projected Time is 19:42."),
            ]
        })
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "What is my projection?"})
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "thread_id" in data
        assert "19:42" in data["response"]

    @patch("app.routers.chat.SupabaseService")
    @patch("app.chat.agent.get_agent")
    def test_chat_creates_thread(self, mock_agent_fn, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.get_chat_thread.return_value = None
        mock_db.create_chat_thread.return_value = {}
        mock_db.insert_chat_message.return_value = {}
        mock_db.get_chat_messages.return_value = []
        mock_db_cls.return_value = mock_db

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [AIMessage(content="Hello!")]
        })
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 200
        assert r.json()["thread_id"]

    @patch("app.routers.chat.SupabaseService")
    def test_chat_fallback_on_error(self, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.get_chat_thread.return_value = None
        mock_db.create_chat_thread.return_value = {}
        mock_db.insert_chat_message.return_value = {}
        mock_db.get_chat_messages.return_value = []
        mock_db_cls.return_value = mock_db

        with patch("app.chat.agent.get_agent", side_effect=Exception("No API key")):
            r = client.post("/chat", json={"message": "hello"})
            assert r.status_code == 200
            assert "unable" in r.json()["response"].lower()


class TestThreadManagement:
    @patch("app.routers.chat.SupabaseService")
    def test_create_thread(self, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.create_chat_thread.return_value = {}
        mock_db_cls.return_value = mock_db

        r = client.post("/chat/thread")
        assert r.status_code == 200
        assert "thread_id" in r.json()

    @patch("app.routers.chat.SupabaseService")
    def test_get_history_empty(self, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.create_chat_thread.return_value = {}
        mock_db_cls.return_value = mock_db

        r = client.post("/chat/thread")
        thread_id = r.json()["thread_id"]

        mock_db.get_chat_thread.return_value = {"thread_id": thread_id, "user_id": "test-user"}
        mock_db.get_chat_messages.return_value = []

        r2 = client.get(f"/chat/history?thread_id={thread_id}")
        assert r2.status_code == 200
        assert r2.json()["messages"] == []

    @patch("app.routers.chat.SupabaseService")
    def test_delete_thread(self, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.create_chat_thread.return_value = {}
        mock_db_cls.return_value = mock_db

        r = client.post("/chat/thread")
        thread_id = r.json()["thread_id"]

        mock_db.get_chat_thread.return_value = {"thread_id": thread_id, "user_id": "test-user"}
        mock_db.delete_chat_thread.return_value = None

        r2 = client.delete(f"/chat/thread/{thread_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"

    @patch("app.routers.chat.SupabaseService")
    @patch("app.chat.agent.get_agent")
    def test_history_has_messages_after_chat(self, mock_agent_fn, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.get_chat_thread.return_value = None
        mock_db.create_chat_thread.return_value = {}
        mock_db.insert_chat_message.return_value = {}
        mock_db.get_chat_messages.return_value = [
            {"role": "user", "content": "test"},
        ]
        mock_db_cls.return_value = mock_db

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [AIMessage(content="Response")]
        })
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "test"})
        thread_id = r.json()["thread_id"]

        mock_db.get_chat_thread.return_value = {"thread_id": thread_id, "user_id": "test-user"}
        mock_db.get_chat_messages.return_value = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "Response"},
        ]

        r2 = client.get(f"/chat/history?thread_id={thread_id}")
        msgs = r2.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"


class TestStreamEndpoint:
    @patch("app.routers.chat.SupabaseService")
    @patch("app.chat.agent.get_agent")
    def test_stream_returns_sse(self, mock_agent_fn, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.get_chat_thread.return_value = None
        mock_db.create_chat_thread.return_value = {}
        mock_db.insert_chat_message.return_value = {}
        mock_db.get_chat_messages.return_value = [
            {"role": "user", "content": "hi"},
        ]
        mock_db_cls.return_value = mock_db

        mock_agent = MagicMock()

        async def fake_astream(*args, **kwargs):
            yield {"messages": [AIMessage(content="Hello")]}
            yield {"messages": [AIMessage(content="Hello world")]}

        mock_agent.astream = fake_astream
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat/stream", json={"message": "hi"})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


class TestThreadOwnership:
    @patch("app.routers.chat.SupabaseService")
    def test_user_b_cannot_read_user_a_thread(self, mock_db_cls, client):
        """C6: user B should not be able to access user A's thread."""
        mock_db = MagicMock()
        mock_db.create_chat_thread.return_value = {}
        mock_db_cls.return_value = mock_db

        r = client.post("/chat/thread")
        thread_id = r.json()["thread_id"]

        mock_db.get_chat_thread.return_value = {"thread_id": thread_id, "user_id": "test-user"}

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "user-b", "email": "b@test.com"}
        r2 = client.get(f"/chat/history?thread_id={thread_id}")
        assert r2.status_code == 404

    @patch("app.routers.chat.SupabaseService")
    def test_user_b_cannot_delete_user_a_thread(self, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.create_chat_thread.return_value = {}
        mock_db_cls.return_value = mock_db

        r = client.post("/chat/thread")
        thread_id = r.json()["thread_id"]

        mock_db.get_chat_thread.return_value = {"thread_id": thread_id, "user_id": "test-user"}

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "user-b", "email": "b@test.com"}
        r2 = client.delete(f"/chat/thread/{thread_id}")
        assert r2.status_code == 404

    @patch("app.routers.chat.SupabaseService")
    @patch("app.chat.agent.get_agent")
    def test_user_b_cannot_post_to_user_a_thread(self, mock_agent_fn, mock_db_cls, client):
        mock_db = MagicMock()
        mock_db.get_chat_thread.return_value = None
        mock_db.create_chat_thread.return_value = {}
        mock_db.insert_chat_message.return_value = {}
        mock_db.get_chat_messages.return_value = []
        mock_db_cls.return_value = mock_db

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="ok")]})
        mock_agent_fn.return_value = mock_agent

        r = client.post("/chat", json={"message": "hi"})
        thread_id = r.json()["thread_id"]

        mock_db.get_chat_thread.return_value = {"thread_id": thread_id, "user_id": "test-user"}

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "user-b", "email": "b@test.com"}
        r2 = client.post("/chat", json={"message": "hi", "thread_id": thread_id})
        assert r2.status_code == 403


class TestChatThreadDBPersistence:
    """F3: Verify chat threads persist to the DB via SupabaseService."""

    @patch("app.routers.chat.SupabaseService")
    def test_chat_thread_persistence(self, mock_cls, client):
        """Verify thread creation stores in DB."""
        inst = MagicMock()
        inst.create_chat_thread.return_value = {
            "thread_id": "new-thread-abc",
            "user_id": "test-user",
        }
        mock_cls.return_value = inst

        r = client.post("/chat/thread")
        assert r.status_code == 200
        data = r.json()
        assert "thread_id" in data

        inst.create_chat_thread.assert_called_once()
        call_args = inst.create_chat_thread.call_args[0]
        assert call_args[0] == "test-user"

    @patch("app.routers.chat.SupabaseService")
    def test_chat_history_from_db(self, mock_cls, client):
        """Verify history reads from DB."""
        inst = MagicMock()
        inst.get_chat_thread.return_value = {
            "thread_id": "thread-xyz",
            "user_id": "test-user",
        }
        inst.get_chat_messages.return_value = [
            {"role": "user", "content": "hello", "created_at": "2026-03-01T00:00:00Z"},
            {"role": "assistant", "content": "Hi there!", "created_at": "2026-03-01T00:00:01Z"},
        ]
        mock_cls.return_value = inst

        r = client.get("/chat/history?thread_id=thread-xyz")
        assert r.status_code == 200
        data = r.json()
        assert data["thread_id"] == "thread-xyz"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

        inst.get_chat_thread.assert_called_once_with("thread-xyz")
        inst.get_chat_messages.assert_called_once_with("thread-xyz")

    @patch("app.routers.chat.SupabaseService")
    def test_chat_thread_delete_from_db(self, mock_cls, client):
        """Verify deletion calls delete_chat_thread on the DB."""
        inst = MagicMock()
        inst.get_chat_thread.return_value = {
            "thread_id": "thread-del",
            "user_id": "test-user",
        }
        inst.delete_chat_thread.return_value = None
        mock_cls.return_value = inst

        r = client.delete("/chat/thread/thread-del")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "deleted"
        assert data["thread_id"] == "thread-del"

        inst.get_chat_thread.assert_called_once_with("thread-del")
        inst.delete_chat_thread.assert_called_once_with("thread-del")
