from __future__ import annotations

import asyncio
import logging
import time

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from assistant.graph import graph
from conference.models import ChatLog

logger = logging.getLogger(__name__)

MAX_CHARS = 2000
RATE_WINDOW_SECONDS = 10
RATE_MAX = 8
HISTORY_LIMIT = 6
STREAM_NODES = {"agent"}


def message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "".join(parts)
    return ""


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.task: asyncio.Task | None = None
        self.timestamps: list[float] = []
        await self.accept()

    async def disconnect(self, code):
        if self.task and not self.task.done():
            self.task.cancel()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "stop":
            if self.task and not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            await self.send_json({"type": "stopped"})
            return
        question = str(content.get("question") or "").strip()
        if not question or len(question) > MAX_CHARS:
            await self.send_json(
                {"type": "error", "message": "Запитання має містити від 1 до 2000 символів."}
            )
            return
        now = time.monotonic()
        self.timestamps = [stamp for stamp in self.timestamps if now - stamp < RATE_WINDOW_SECONDS]
        if len(self.timestamps) >= RATE_MAX:
            await self.send_json(
                {"type": "error", "message": "Забагато запитів. Зачекайте кілька секунд."}
            )
            return
        self.timestamps.append(now)
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        history = content.get("history") if isinstance(content.get("history"), list) else []
        self.task = asyncio.create_task(self._generate(question, history))

    async def _generate(self, question: str, history: list) -> None:
        await self.send_json({"type": "start"})
        messages = _history_messages(history)
        messages.append(HumanMessage(content=question))
        inputs = {
            "messages": messages,
            "question": question,
            "context_docs": [],
            "top_score": 0.0,
        }
        answer_parts: list[str] = []
        grounded = False
        top_score = 0.0
        try:
            async for item in graph.astream(
                inputs,
                stream_mode=["messages", "updates"],
                config={"recursion_limit": 8},
            ):
                mode, data = _normalize_stream_item(item)
                if mode == "updates":
                    grounded, top_score = await self._handle_updates(
                        data, grounded, top_score, answer_parts
                    )
                elif mode == "messages":
                    await self._handle_message(data, answer_parts)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("chat generation failed")
            await self.send_json(
                {"type": "error", "message": "Не вдалося згенерувати відповідь. Спробуйте ще раз."}
            )
            return

        answer = "".join(answer_parts).strip()
        await ChatLog.objects.acreate(
            question=question,
            answer=answer,
            top_similarity=top_score if grounded else None,
            grounded=grounded,
        )
        await self.send_json({"type": "end"})

    async def _handle_updates(self, data, grounded: bool, top_score: float, answer_parts: list[str]):
        if not isinstance(data, dict):
            return grounded, top_score
        retrieved = data.get("retrieve") or {}
        docs = retrieved.get("context_docs") or []
        if docs:
            grounded = True
            top_score = float(retrieved.get("top_score") or 0.0)
        if "tools" in data:
            for message in data["tools"].get("messages") or []:
                await self.send_json(
                    {
                        "type": "tool",
                        "name": getattr(message, "name", "") or "tool",
                        "status": "ok",
                    }
                )
        return grounded, top_score

    async def _handle_message(self, data, answer_parts: list[str]) -> None:
        if not isinstance(data, tuple) or len(data) != 2:
            return
        chunk, metadata = data
        node = (metadata or {}).get("langgraph_node")
        if node not in STREAM_NODES:
            return
        if not isinstance(chunk, (AIMessageChunk, AIMessage)):
            return
        text = message_text(chunk)
        if not text:
            return
        answer_parts.append(text)
        await self.send_json({"type": "token", "text": text})


def _history_messages(history: list):
    messages = []
    for item in history[-HISTORY_LIMIT:]:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "")[:4000]
        if not content:
            continue
        if item.get("role") == "user":
            messages.append(HumanMessage(content=content))
        elif item.get("role") == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _normalize_stream_item(item):
    if (
        isinstance(item, tuple)
        and len(item) == 2
        and item[0] in {"messages", "updates", "values", "custom"}
    ):
        return item
    return "updates", item
