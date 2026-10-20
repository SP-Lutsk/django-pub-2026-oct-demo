from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from django.db.models import Q
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from conference.models import Session

logger = logging.getLogger(__name__)


class ListSessionsInput(BaseModel):
    block: int | None = Field(
        default=None,
        description="Номер блоку: 1, 2 або 3. Не передавай поле, якщо потрібна вся програма.",
    )


def build_tools():
    @tool(args_schema=ListSessionsInput)
    async def list_sessions(block: int | None = None) -> str:
        return await _format_sessions(block)

    return [list_sessions]


async def _format_sessions(block: int | None) -> str:
    queryset = (
        Session.objects.prefetch_related("speakers")
        .exclude(kind=Session.Kind.REFERENCE)
        .order_by("position", "block_number")
    )
    if block is not None:
        queryset = queryset.filter(block_number=block)
    lines = []
    async for session in queryset:
        names = []
        for speaker in session.speakers.all():
            label = speaker.name
            if speaker.is_placeholder:
                label += " (ім'я ще не підтверджено)"
            names.append(label)
        speaker_line = ", ".join(names) if names else "не вказано"
        lines.append(
            f"- Блок {session.block_number}, {session.get_kind_display()}, {session.duration_min} хв: "
            f"{session.title}. Спікери: {speaker_line}. Стек: {session.stack or 'не вказано'}."
        )
    if not lines:
        return "Сесій за цим фільтром немає."
    return "\n".join(lines)
