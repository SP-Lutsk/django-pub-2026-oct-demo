from __future__ import annotations

from typing import Annotated, TypedDict

from django.conf import settings
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from assistant.prompts import REFUSAL, SYSTEM_PROMPT
from assistant.retrieval import search_chunks
from assistant.tools import build_tools


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    question: str
    context_docs: list
    top_score: float


def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_CHAT_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
        streaming=True,
    )


async def retrieve(state: GraphState) -> dict:
    docs, top_score = await search_chunks(state["question"])
    return {"context_docs": docs, "top_score": top_score}


def _format_context(docs: list[dict]) -> str:
    if not docs:
        return "(немає додаткових нотаток; для фактів про захід користуйся list_sessions)"
    return "\n\n---\n\n".join(doc["content"] for doc in docs)


async def agent(state: GraphState) -> dict:
    tools = build_tools()
    model = get_chat_model().bind_tools(tools)
    system = SystemMessage(
        content=SYSTEM_PROMPT.format(
            refusal=REFUSAL,
            context=_format_context(state["context_docs"]),
        )
    )
    response = await model.ainvoke([system, *state["messages"]])
    return {"messages": [response]}


tool_node = ToolNode(build_tools())


def build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("agent", agent)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile()


graph = build_graph()
