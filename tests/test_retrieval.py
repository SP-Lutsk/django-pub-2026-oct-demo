import pytest
from django.db import connection

from assistant.retrieval import search_chunks
from conference.models import KnowledgeChunk, Session


@pytest.mark.django_db
async def test_cosine_search_returns_nearest_chunk(monkeypatch):
    if connection.vendor != "postgresql":
        pytest.skip("Потрібен PostgreSQL з pgvector.")

    async def fake_embed(question):
        return [1.0, 0.0] + [0.0] * 1534

    monkeypatch.setattr("assistant.retrieval.embed_query", fake_embed)
    session = await Session.objects.acreate(
        slug="block-3",
        block_number=3,
        position=1,
        kind=Session.Kind.TALK,
        title="Блок Влада",
        stack="pgvector",
        duration_min=15,
        body="Про pgvector.",
    )
    await KnowledgeChunk.objects.acreate(
        session=session,
        content="Близький фрагмент про pgvector і Django.",
        content_hash="a" * 64,
        embedding=[1.0, 0.0] + [0.0] * 1534,
    )
    await KnowledgeChunk.objects.acreate(
        session=session,
        content="Далекий фрагмент про погоду.",
        content_hash="b" * 64,
        embedding=[0.0, 1.0] + [0.0] * 1534,
    )

    docs, top_score = await search_chunks("що таке pgvector")
    assert len(docs) == 1
    assert "pgvector" in docs[0]["content"]
    assert top_score == pytest.approx(1.0)
