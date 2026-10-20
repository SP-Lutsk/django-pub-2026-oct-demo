from __future__ import annotations

import logging

from django.conf import settings
from langchain_openai import OpenAIEmbeddings
from pgvector.django import CosineDistance

from conference.models import KnowledgeChunk

logger = logging.getLogger(__name__)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    embeddings = get_embeddings()
    vectors: list[list[float]] = []
    batch_size = 64
    for start in range(0, len(texts), batch_size):
        vectors.extend(embeddings.embed_documents(texts[start : start + batch_size]))
    if vectors and len(vectors[0]) != settings.EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Очікувалась розмірність {settings.EMBEDDING_DIMENSIONS}, отримано {len(vectors[0])}."
        )
    logger.info(
        "embedded %s chunks model=%s dimensions=%s",
        len(vectors),
        settings.OPENAI_EMBEDDING_MODEL,
        settings.EMBEDDING_DIMENSIONS if vectors else 0,
    )
    return vectors


async def embed_query(text: str) -> list[float]:
    return await get_embeddings().aembed_query(text)


def similarity_from_distance(distance: float) -> float:
    return 1.0 - float(distance)


async def search_chunks(question: str) -> tuple[list[dict], float]:
    query_vector = await embed_query(question)
    queryset = (
        KnowledgeChunk.objects.select_related("session")
        .prefetch_related("session__speakers")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[: settings.RAG_TOP_K]
    )
    ranked: list[tuple[float, KnowledgeChunk]] = []
    async for chunk in queryset:
        ranked.append((float(chunk.distance), chunk))
    logger.info(
        "retrieval question=%r cutoff=%s candidates=%s",
        question,
        settings.RAG_MAX_DISTANCE,
        [
            {
                "distance": round(distance, 4),
                "session": chunk.session.title,
                "kept": distance <= settings.RAG_MAX_DISTANCE,
            }
            for distance, chunk in ranked
        ]
        or "none",
    )
    docs: list[dict] = []
    for distance, chunk in ranked:
        if distance > settings.RAG_MAX_DISTANCE:
            continue
        speakers = [
            {
                "name": speaker.name,
                "placeholder": speaker.is_placeholder,
            }
            for speaker in chunk.session.speakers.all()
        ]
        docs.append(
            {
                "content": chunk.content,
                "distance": distance,
                "similarity": similarity_from_distance(distance),
                "session_title": chunk.session.title,
                "block_number": chunk.session.block_number,
                "speakers": speakers,
            }
        )
    top_score = docs[0]["similarity"] if docs else 0.0
    return docs, top_score
