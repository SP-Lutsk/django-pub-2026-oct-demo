from __future__ import annotations

import hashlib

from assistant.retrieval import embed_documents
from conference.chunking import chunk_text
from conference.models import KnowledgeChunk, Session

KIND_LABELS = {
    Session.Kind.TALK: "доповідь",
    Session.Kind.DISCUSSION: "дискусія",
    Session.Kind.STUDENT: "виступи студентів",
    Session.Kind.REFERENCE: "технічний довідник",
}

REFERENCE_CHUNK_SIZE = 1600


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def session_prefix(session: Session) -> str:
    names = []
    for speaker in session.speakers.all():
        if speaker.is_placeholder:
            names.append(f"{speaker.name} (ім'я ще не підтверджено)")
        else:
            names.append(speaker.name)
    speaker_line = ", ".join(names) if names else "не вказано"
    stack = session.stack or "не вказано"
    if session.kind == Session.Kind.REFERENCE:
        return (
            f"Тема: {session.title}\n"
            f"Пов'язаний блок: {session.block_number}\n"
            f"Спікер блоку: {speaker_line}\n"
            f"Стек: {stack}\n"
            "Тип: технічний довідник асистента (не цитата з виступу)"
        )
    return (
        f"Сесія: {session.title}\n"
        f"Блок: {session.block_number}\n"
        f"Тип: {KIND_LABELS.get(session.kind, session.kind)}\n"
        f"Тривалість: {session.duration_min} хв\n"
        f"Спікери: {speaker_line}\n"
        f"Стек: {stack}"
    )


def chunk_rows_for_session(session: Session) -> list[dict]:
    prefix = session_prefix(session)
    size = REFERENCE_CHUNK_SIZE if session.kind == Session.Kind.REFERENCE else 800
    rows = []
    for piece in chunk_text(session.body, size=size):
        content = f"{prefix}\n\n{piece}"
        rows.append(
            {
                "session": session,
                "content": content,
                "content_hash": content_hash(content),
            }
        )
    return rows


def sync_session_chunks(session: Session) -> tuple[int, int]:
    rows = chunk_rows_for_session(session)
    hashes = [row["content_hash"] for row in rows]
    existing = set(
        KnowledgeChunk.objects.filter(session=session, content_hash__in=hashes).values_list(
            "content_hash", flat=True
        )
    )
    pending = [row for row in rows if row["content_hash"] not in existing]
    if pending:
        vectors = embed_documents([row["content"] for row in pending])
        KnowledgeChunk.objects.bulk_create(
            [
                KnowledgeChunk(
                    session=session,
                    content=row["content"],
                    content_hash=row["content_hash"],
                    embedding=vector,
                )
                for row, vector in zip(pending, vectors, strict=True)
            ]
        )
    removed, _ = (
        KnowledgeChunk.objects.filter(session=session).exclude(content_hash__in=hashes).delete()
    )
    return len(pending), removed
