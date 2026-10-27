import pytest

from assistant.tools import list_sessions
from conference.models import Session, Speaker


@pytest.mark.django_db(transaction=True)
async def test_list_sessions_skips_reference_topics():
    speaker = await Speaker.objects.acreate(
        slug="students",
        name="Студенти ЛНТУ",
        is_placeholder=True,
    )
    session = await Session.objects.acreate(
        slug="block-1",
        block_number=1,
        position=1,
        kind=Session.Kind.TALK,
        title="Data Science і Classical ML",
        stack="NumPy, Pandas",
        duration_min=35,
        body="Про NumPy.",
    )
    await session.speakers.aadd(speaker)
    reference = await Session.objects.acreate(
        slug="ref-numpy",
        block_number=1,
        position=100,
        kind=Session.Kind.REFERENCE,
        title="NumPy — векторизація",
        stack="NumPy",
        duration_min=0,
        body="Довідник, не доповідь.",
    )
    await reference.speakers.aadd(speaker)
    result = await list_sessions.ainvoke({"block": 1})
    assert "NumPy, Pandas" in result
    assert "ім'я ще не підтверджено" in result
    assert "Довідник, не доповідь" not in result
    assert "векторизація" not in result
