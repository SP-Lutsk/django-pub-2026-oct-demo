from __future__ import annotations

from typing import Annotated, TypedDict

from django.conf import settings
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from assistant.prompts import REFUSAL, SYSTEM_PROMPT
from assistant.retrieval import mentions_speaker, search_chunks
from assistant.tools import TOOLS
from conference.models import Session


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
    # Питання про конкретного спікера відповідаємо лише з нотаток його виступу,
    # щоб модель не приписувала спікеру текст технічного довідника.
    talks_only = await mentions_speaker(state["question"])
    docs, top_score = await search_chunks(state["question"], talks_only=talks_only)
    return {"context_docs": docs, "top_score": top_score}


def _format_context(docs: list[dict]) -> str:
    if not docs:
        return "(немає додаткових нотаток; для фактів про захід користуйся list_sessions)"
    talks = [doc["content"] for doc in docs if doc.get("kind") != Session.Kind.REFERENCE]
    references = [doc["content"] for doc in docs if doc.get("kind") == Session.Kind.REFERENCE]
    parts = []
    if talks and references:
        parts.append(
            "НОТАТКИ ВИСТУПІВ. Лише тут те, що спікери говорили зі сцени.\n\n"
            + "\n\n---\n\n".join(talks)
        )
    elif talks:
        parts.append("\n\n---\n\n".join(talks))
    if references:
        parts.append(
            "ТЕХНІЧНИЙ ДОВІДНИК. Цього спікери зі сцени не говорили. На питання «що радив / "
            "розповідав спікер» не використовуй цю секцію; її можна дати лише окремим абзацом "
            "«Додатково з практики…».\n\n" + "\n\n---\n\n".join(references)
        )
    return "\n\n=====\n\n".join(parts)


async def agent(state: GraphState) -> dict:
    model = get_chat_model().bind_tools(TOOLS)
    system = SystemMessage(
        content=SYSTEM_PROMPT.format(
            refusal=REFUSAL,
            context=_format_context(state["context_docs"]),
        )
    )
    response = await model.ainvoke([system, *state["messages"]])
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile()


graph = build_graph()
