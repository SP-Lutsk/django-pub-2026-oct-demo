import pytest
from langchain_core.messages import AIMessage, SystemMessage

from assistant.graph import _format_context, graph
from assistant.prompts import REFUSAL


class _FakeChat:
    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        assert any(isinstance(message, SystemMessage) for message in messages)
        assert REFUSAL in messages[0].content
        assert "[1]" not in messages[0].content
        return AIMessage(content="Вітаю! Я офіційний асистент Django Pub AI Edition.")


@pytest.mark.django_db
async def test_empty_retrieval_still_calls_the_model(monkeypatch):
    async def no_hits(question):
        return [], 0.0

    monkeypatch.setattr("assistant.graph.search_chunks", no_hits)
    monkeypatch.setattr("assistant.graph.get_chat_model", lambda: _FakeChat())
    result = await graph.ainvoke(
        {
            "messages": [],
            "question": "привіт",
            "context_docs": [],
            "top_score": 0.0,
        }
    )
    assert result["messages"][-1].content.startswith("Вітаю!")
    assert result["context_docs"] == []


def test_context_has_no_chunk_numbers():
    text = _format_context(
        [
            {"content": "перший фрагмент"},
            {"content": "другий фрагмент"},
        ]
    )
    assert "[1]" not in text
    assert "[2]" not in text
    assert "перший фрагмент\n\n---\n\nдругий фрагмент" == text
