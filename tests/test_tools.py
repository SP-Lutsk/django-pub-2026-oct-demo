import pytest
from django.contrib.auth.models import AnonymousUser

from assistant.tools import build_tools
from conference.models import Session, Speaker


def _tools():
    return {tool.name: tool for tool in build_tools()}


@pytest.mark.django_db
async def test_anonymous_can_list_sessions():
    speaker = await Speaker.objects.acreate(
        slug="block1",
        name="Спікер Блоку 1 (уточнюється)",
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
    result = await _tools()["list_sessions"].ainvoke({"block": 1})
    assert "NumPy, Pandas" in result
    assert "ім'я ще не підтверджено" in result
    assert "Довідник, не доповідь" not in result
    assert "векторизація" not in result
