"""PIRX Chat API — streaming conversation with the LangGraph agent."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import json
import uuid

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

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


def _get_or_create_thread(db: SupabaseService, thread_id: Optional[str], user_id: str) -> str:
    if thread_id:
        existing = db.get_chat_thread(thread_id)
        if existing:
            if existing["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Not authorized for this thread")
            return thread_id
    new_id = thread_id or str(uuid.uuid4())
    db.create_chat_thread(user_id, new_id)
    return new_id


def _load_thread_messages(db: SupabaseService, thread_id: str) -> list[dict]:
    return db.get_chat_messages(thread_id)


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatMessage,
    user: dict = Depends(get_current_user),
):
    from langchain_core.messages import HumanMessage, AIMessage
    from app.chat.agent import get_agent

    db = SupabaseService()
    thread_id = _get_or_create_thread(db, body.thread_id, user["user_id"])

    db.insert_chat_message(thread_id, "user", body.message)

    stored_messages = _load_thread_messages(db, thread_id)

    try:
        agent = get_agent()

        messages = []
        for msg in stored_messages:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        result = await agent.ainvoke({
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

        db.insert_chat_message(thread_id, "assistant", response_text)

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
        db.insert_chat_message(thread_id, "assistant", fallback)
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
    from langchain_core.messages import HumanMessage, AIMessage
    from app.chat.agent import get_agent

    db = SupabaseService()
    thread_id = _get_or_create_thread(db, body.thread_id, user["user_id"])

    db.insert_chat_message(thread_id, "user", body.message)

    stored_messages = _load_thread_messages(db, thread_id)

    async def event_generator():
        try:
            agent = get_agent()

            messages = []
            for msg in stored_messages:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

            full_response = ""

            async for event in agent.astream(
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
                    if hasattr(last, "tool_calls") and last.tool_calls:
                        tool_names = [tc.get("name", "") for tc in last.tool_calls if isinstance(tc, dict)]
                        if tool_names:
                            yield f"data: {json.dumps({'tools': tool_names, 'thread_id': thread_id})}\n\n"

            db_inner = SupabaseService()
            db_inner.insert_chat_message(thread_id, "assistant", full_response)

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
    db = SupabaseService()
    thread = db.get_chat_thread(thread_id)
    if not thread or thread["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = db.get_chat_messages(thread_id)
    return {"thread_id": thread_id, "messages": messages}


@router.post("/thread", response_model=ThreadResponse)
async def create_thread(user: dict = Depends(get_current_user)):
    db = SupabaseService()
    thread_id = str(uuid.uuid4())
    db.create_chat_thread(user["user_id"], thread_id)
    return ThreadResponse(
        thread_id=thread_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.delete("/thread/{thread_id}")
async def delete_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    db = SupabaseService()
    thread = db.get_chat_thread(thread_id)
    if not thread or thread["user_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Thread not found")
    db.delete_chat_thread(thread_id)
    return {"status": "deleted", "thread_id": thread_id}
