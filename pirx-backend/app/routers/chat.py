"""PIRX Chat API — streaming conversation with the LangGraph agent.

Supports:
- POST /chat — send message, get streaming response
- GET /chat/history — get conversation history for a thread
- POST /chat/thread — create a new conversation thread
- DELETE /chat/thread/{thread_id} — delete a thread
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import json
import uuid

from app.dependencies import get_current_user

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    tool_calls: list[dict] = []


class ThreadResponse(BaseModel):
    thread_id: str
    created_at: str


# In-memory thread store (TODO: Replace with Supabase or LangGraph PostgresSaver)
# Structure: { "thread_id": { "user_id": "...", "messages": [...] } }
_threads: dict[str, dict] = {}


def _get_or_create_thread(thread_id: Optional[str], user_id: str) -> str:
    """Get existing thread (with ownership check) or create new one."""
    if thread_id and thread_id in _threads:
        if _threads[thread_id]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized for this thread")
        return thread_id
    new_id = thread_id or str(uuid.uuid4())
    _threads[new_id] = {"user_id": user_id, "messages": []}
    return new_id


def _get_thread_messages(thread_id: str) -> list[dict]:
    """Get messages list from a thread."""
    return _threads[thread_id]["messages"]


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatMessage,
    user: dict = Depends(get_current_user),
):
    """Send a message to the PIRX AI agent and get a response.

    For non-streaming responses. Use POST /chat/stream for streaming.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.chat.agent import get_agent

    thread_id = _get_or_create_thread(body.thread_id, user["user_id"])
    messages_list = _get_thread_messages(thread_id)

    messages_list.append({
        "role": "user",
        "content": body.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        agent = get_agent()

        messages = []
        for msg in messages_list:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        result = agent.invoke({
            "messages": messages,
            "user_id": user["user_id"],
        })

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content]
        response_text = ai_messages[-1].content if ai_messages else "I could not generate a response."

        tool_calls = []
        for m in result["messages"]:
            if hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    tool_calls.append({
                        "tool": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    })

        messages_list.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_calls": tool_calls,
        })

        return ChatResponse(
            response=response_text,
            thread_id=thread_id,
            tool_calls=tool_calls,
        )
    except Exception:
        fallback = (
            "I am currently unable to process your request. "
            "This could be because the AI service is not configured. "
            "Please ensure an API key is set in the environment."
        )
        messages_list.append({
            "role": "assistant",
            "content": fallback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return ChatResponse(
            response=fallback,
            thread_id=thread_id,
            tool_calls=[],
        )


@router.post("/stream")
async def chat_stream(
    body: ChatMessage,
    user: dict = Depends(get_current_user),
):
    """Send a message and get a streaming response.

    Returns Server-Sent Events (SSE) with token-by-token responses.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.chat.agent import get_agent

    thread_id = _get_or_create_thread(body.thread_id, user["user_id"])
    messages_list = _get_thread_messages(thread_id)

    messages_list.append({
        "role": "user",
        "content": body.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    async def event_generator():
        try:
            agent = get_agent()

            messages = []
            for msg in messages_list:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

            full_response = ""

            for event in agent.stream(
                {"messages": messages, "user_id": user["user_id"]},
                stream_mode="values",
            ):
                if "messages" in event:
                    last = event["messages"][-1]
                    if isinstance(last, AIMessage) and last.content:
                        new_content = last.content
                        if new_content != full_response:
                            delta = new_content[len(full_response):]
                            full_response = new_content
                            yield f"data: {json.dumps({'delta': delta, 'thread_id': thread_id})}\n\n"

            messages_list.append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"

        except Exception:
            yield f"data: {json.dumps({'error': 'An error occurred', 'thread_id': thread_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def get_chat_history(
    thread_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Get conversation history for a thread."""
    if thread_id not in _threads or _threads[thread_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread_id": thread_id, "messages": _threads[thread_id]["messages"]}


@router.post("/thread", response_model=ThreadResponse)
async def create_thread(user: dict = Depends(get_current_user)):
    """Create a new conversation thread."""
    thread_id = str(uuid.uuid4())
    _threads[thread_id] = {"user_id": user["user_id"], "messages": []}
    return ThreadResponse(
        thread_id=thread_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.delete("/thread/{thread_id}")
async def delete_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a conversation thread."""
    if thread_id not in _threads or _threads[thread_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Thread not found")
    del _threads[thread_id]
    return {"status": "deleted", "thread_id": thread_id}
