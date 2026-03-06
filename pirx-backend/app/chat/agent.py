"""PIRX LangGraph Chat Agent.

Stateful conversational agent with 8 tools for querying user data.
Uses intent classification to route queries efficiently.
"""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.chat.prompts import PIRX_SYSTEM_PROMPT
from app.chat.tools import ALL_TOOLS
from app.config import settings


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str


def create_agent(model_name: str = "gpt-4o-mini"):
    """Create a PIRX chat agent graph.

    Args:
        model_name: OpenAI model to use. Default gpt-4o-mini for cost efficiency.

    Returns:
        Compiled LangGraph StateGraph
    """
    llm = ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key or "sk-mock-key",
        temperature=0.3,
        streaming=True,
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def chatbot(state: AgentState) -> dict:
        """Main chatbot node — calls LLM with tools bound."""
        messages = list(state["messages"])

        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=PIRX_SYSTEM_PROMPT)] + messages

        user_id = state.get("user_id", "unknown")
        context_msg = SystemMessage(
            content=f"Current user_id for tool calls: {user_id}"
        )
        messages_with_context = messages + [context_msg]

        response = llm_with_tools.invoke(messages_with_context)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Decide whether to call tools or end."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("chatbot")
    graph.add_conditional_edges(
        "chatbot", should_continue, {"tools": "tools", END: END}
    )
    graph.add_edge("tools", "chatbot")

    return graph.compile()


_agent = None


def get_agent():
    """Get or create the singleton agent."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
