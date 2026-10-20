import asyncio

import pytest
from channels.testing import WebsocketCommunicator
from langchain_core.messages import AIMessageChunk

from assistant.consumers import ChatConsumer
from conference.models import ChatLog


@pytest.mark.django_db(transaction=True)
async def test_consumer_streams_tokens(monkeypatch):
    async def fake_astream(inputs, stream_mode=None, config=None):
        yield (
            "updates",
            {
                "retrieve": {
                    "context_docs": [
                        {
                            "session_title": "LLM, RAG і AI-агенти",
                            "block_number": 3,
                            "speakers": [{"name": "Влад Гетьманенко", "placeholder": False}],
                            "similarity": 0.82,
                            "content": "Блок 3 веде Влад Гетьманенко.",
                        }
                    ],
                    "top_score": 0.82,
                }
            },
        )
        yield (
            "messages",
            (AIMessageChunk(content="Влад веде блок 3."), {"langgraph_node": "agent"}),
        )

    monkeypatch.setattr("assistant.consumers.graph.astream", fake_astream)
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"question": "Що розказував Влад?"})

    events = []
    while True:
        event = await communicator.receive_json_from(timeout=2)
        events.append(event)
        if event["type"] in {"end", "error"}:
            break

    kinds = [event["type"] for event in events]
    assert kinds[0] == "start"
    assert "sources" not in kinds
    assert any(event.get("text") == "Влад веде блок 3." for event in events)
    assert kinds[-1] == "end"
    rows = [row async for row in ChatLog.objects.filter(question="Що розказував Влад?")]
    assert len(rows) == 1
    assert rows[0].question == "Що розказував Влад?"
    assert rows[0].grounded is True
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_consumer_stops_generation(monkeypatch):
    started = asyncio.Event()

    async def fake_astream(inputs, stream_mode=None, config=None):
        started.set()
        await asyncio.sleep(30)
        yield (
            "messages",
            (AIMessageChunk(content="пізно"), {"langgraph_node": "agent"}),
        )

    monkeypatch.setattr("assistant.consumers.graph.astream", fake_astream)
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"question": "Що розказував Влад?"})

    event = await communicator.receive_json_from(timeout=2)
    assert event["type"] == "start"
    await started.wait()
    await communicator.send_json_to({"type": "stop"})

    event = await communicator.receive_json_from(timeout=2)
    assert event["type"] == "stopped"
    assert communicator.output_queue.empty()

    rows = [row async for row in ChatLog.objects.filter(question="Що розказував Влад?")]
    assert rows == []
    await communicator.disconnect()
