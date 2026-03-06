"""PIRX LangGraph Chat Agent.

Stateful conversational agent with intent routing, 8 read-only tools,
PIRX terminology enforcement, and AsyncPostgresSaver for persistence.
"""

import re
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.chat.prompts import PIRX_SYSTEM_PROMPT, TERMINOLOGY_GUARD
from app.chat.tools import ALL_TOOLS
from app.config import settings


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str


def _get_llm():
    """Get LLM based on available API keys."""
    if settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.google_api_key,
            temperature=0.3,
        )
    elif settings.openai_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4.1",
            api_key=settings.openai_api_key,
            temperature=0.3,
        )
    else:
        raise RuntimeError("No LLM API key configured (GOOGLE_API_KEY or OPENAI_API_KEY)")


_TERMINOLOGY_REPLACEMENTS = {
    "predicted time": "Projected Time",
    "estimated time": "Projected Time",
    "forecast": "Projected Time",
    "confidence interval": "Supported Range",
    "error range": "Supported Range",
    "factors": "Structural Drivers",
    "variables": "Structural Drivers",
    "race readiness": "Event Readiness",
    "fitness score": "Event Readiness",
    "uncertainty": "Volatility",
}


def create_agent():
    """Create the PIRX chat agent graph with intent routing."""

    def classify_intent(state: AgentState) -> dict:
        """Classify user intent for routing."""
        last_msg = ""
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                last_msg = m.content.lower()
                break

        projection_terms = ["projection", "projected time", "race time", "supported range", "how fast", "improvement"]
        training_terms = ["training", "mileage", "workout", "pace", "heart rate", "volume", "intensity", "session"]

        intent = "general_chat"
        if any(term in last_msg for term in projection_terms):
            intent = "projection_query"
        elif any(term in last_msg for term in training_terms):
            intent = "training_analysis"

        return {"messages": [SystemMessage(content=f"[INTENT: {intent}]")]}

    def agent_node(state: AgentState) -> dict:
        """Main agent node — calls LLM with tools bound."""
        llm = _get_llm()
        llm_with_tools = llm.bind_tools(ALL_TOOLS)

        user_id = state.get("user_id", "unknown")
        messages = list(state["messages"])
        if not any(isinstance(m, SystemMessage) and PIRX_SYSTEM_PROMPT[:30] in m.content for m in messages):
            messages = [SystemMessage(content=PIRX_SYSTEM_PROMPT)] + messages

        messages.append(SystemMessage(
            content=f"When calling any tool, always pass user_id='{user_id}' as the first argument."
        ))

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_use_tools(state: AgentState) -> str:
        """Route to tools or to response generation."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "generate_response"

    def generate_response(state: AgentState) -> dict:
        """Final response node — enforce PIRX terminology."""
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.content:
            content = last_msg.content
            for banned, correct in _TERMINOLOGY_REPLACEMENTS.items():
                if banned.lower() in content.lower():
                    content = re.sub(re.escape(banned), correct, content, flags=re.IGNORECASE)
            if content != last_msg.content:
                return {"messages": [AIMessage(content=content)]}
        return {"messages": []}

    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "agent")
    graph.add_conditional_edges("agent", should_use_tools, {"tools": "tools", "generate_response": "generate_response"})
    graph.add_edge("tools", "agent")
    graph.add_edge("generate_response", END)

    return graph.compile()


_agent = None


def get_agent():
    """Get or create the singleton agent."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
