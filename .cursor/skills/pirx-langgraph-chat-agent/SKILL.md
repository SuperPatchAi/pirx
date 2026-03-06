---
name: pirx-langgraph-chat-agent
description: LangGraph 1.0+ stateful chat agent for PIRX conversational AI interface. Covers agent graph structure, intent routing, 8 custom tools, RAG pipeline with pgvector semantic search, streaming via Vercel AI SDK and FastAPI WebSocket, AsyncPostgresSaver thread persistence, and PIRX locked terminology enforcement. Use when building the PIRX chat feature, agent nodes, tool definitions, embedding pipeline, or frontend chat integration.
---

# PIRX LangGraph Chat Agent

## PIRX Context

PIRX users interact with their running data through a conversational interface. The chat agent is a **read-only observer** — it queries projections, drivers, training history, and insights but NEVER modifies projection state. Only the projection engine writes to projection state.

## Architecture Overview

LangGraph 1.0+ stateful agent with:
- **AsyncPostgresSaver** for conversation persistence (Supabase Postgres)
- Conditional routing based on intent classification
- 8 custom tools for data access
- RAG pipeline with pgvector for semantic search over embedded insights
- Streaming via Vercel AI SDK (`useChat` hook) + FastAPI WebSocket

## Agent Graph Structure

```
START → classify_intent
  ├── projection_query  (RAG + tools)
  ├── training_analysis (SQL + tools)
  └── general_chat      (direct LLM)
All → generate_response (PIRX terminology enforcement) → END
```

## LangGraph Implementation Pattern

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain.chat_models import init_chat_model
from typing import Literal

model = init_chat_model("gpt-4.1", temperature=0)

def classify_intent(state: MessagesState) -> Literal["projection_query", "training_analysis", "general_chat"]:
    last_msg = state["messages"][-1].content.lower()
    if any(term in last_msg for term in ["projection", "projected time", "race time", "supported range"]):
        return "projection_query"
    elif any(term in last_msg for term in ["training", "mileage", "workout", "pace", "heart rate"]):
        return "training_analysis"
    return "general_chat"

builder = StateGraph(MessagesState)
builder.add_node("classify_intent", classify_intent_node)
builder.add_node("projection_query", projection_query_node)
builder.add_node("training_analysis", training_analysis_node)
builder.add_node("general_chat", general_chat_node)
builder.add_node("generate_response", generate_response_node)

builder.add_edge(START, "classify_intent")
builder.add_conditional_edges(
    "classify_intent",
    classify_intent,
    ["projection_query", "training_analysis", "general_chat"],
)
builder.add_edge("projection_query", "generate_response")
builder.add_edge("training_analysis", "generate_response")
builder.add_edge("general_chat", "generate_response")
builder.add_edge("generate_response", END)

DB_URI = os.getenv("SUPABASE_DB_URL")

async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
```

## Agent Tools

8 tools available to the agent for data access:

| Tool | Description | Returns |
|---|---|---|
| `get_projection` | Current projection state | midpoint, range_lower, range_upper, confidence, change_21d |
| `get_drivers` | Driver breakdown with trends | driver_seconds per driver, 21_day_trend per driver |
| `get_training_history` | Query activities by date/type | List of activities with pace, HR, distance |
| `get_readiness` | Event Readiness scores | scores per event distance |
| `get_physiology` | HR, HRV, sleep trends | trend arrays |
| `search_insights` | Semantic search over embedded insights | top-k matching insight texts |
| `compare_periods` | Compare two training blocks | DTW-aligned comparison metrics |
| `explain_driver` | SHAP-based driver explanation | feature attributions with directional arrows |

All tools are **read-only**. None modify projection state.

## RAG Pipeline

### Embed on Write

Every projection change, notable workout, and driver shift is embedded and stored:
- Model: `text-embedding-3-small` (1536 dimensions)
- Stored in `user_embeddings` table with pgvector

### Retrieve on Query

1. User question → embed via `text-embedding-3-small`
2. Cosine similarity search in pgvector → top-k context
3. LLM receives retrieved context + user question + PIRX terminology system prompt

### pgvector Table

```sql
CREATE TABLE user_embeddings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES users(user_id),
  content_type TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  embedding extensions.vector(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE user_embeddings ENABLE ROW LEVEL SECURITY;
CREATE INDEX ON user_embeddings USING hnsw (embedding vector_cosine_ops);
```

Valid `content_type` values: `activity_summary`, `projection_change`, `insight`, `driver_shift`.

## PIRX Terminology Guard Rails

The `generate_response` node MUST enforce locked terminology before returning any message:

| Correct Term | Banned Alternatives |
|---|---|
| **Projected Time** | predicted time, estimated time, forecast |
| **Supported Range** | confidence interval, error range |
| **Structural Drivers** | factors, variables |
| **Event Readiness** | race readiness, fitness score |
| **Volatility** | uncertainty, noise |

Additional rules:
- The chat agent **observes and explains** — it NEVER coaches or prescribes training
- Projections expressed in **seconds** as the unit of measurement
- No percentages on primary performance changes
- Calm, confident tone — never hype or alarm

## Frontend Chat Integration

### Client Component (Vercel AI SDK)

```tsx
'use client';
import { useChat } from '@ai-sdk/react';

export function PirxChat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
  });
  // Render messages with PIRX dark-theme styling
}
```

### API Route (streams from FastAPI backend)

```typescript
import { streamText, convertToModelMessages, UIMessage } from 'ai';

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  const result = streamText({
    model: 'openai/gpt-4.1',
    messages: await convertToModelMessages(messages),
  });
  return result.toUIMessageStreamResponse();
}
```

## Thread Management

- Each user gets a unique `thread_id` per conversation
- AsyncPostgresSaver persists full conversation history across sessions
- Config pattern:

```python
config = {"configurable": {"thread_id": f"pirx-{user_id}-{conversation_id}"}}
response = await graph.ainvoke({"messages": [user_message]}, config=config)
```

## Dependencies

`langchain`, `langgraph`, `langgraph-checkpoint-postgres`, `langchain-openai`, `langchain-anthropic`, `openai`, `tiktoken`, `ai` (Vercel AI SDK)

## Non-Interference Rule

The chat agent is **read-only** for projection state. It can query projections, drivers, readiness, and training history but NEVER modifies them. Only the projection engine writes to projection state.
