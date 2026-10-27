import gzip
import json
from pathlib import Path

import pytest
import yaml
from django.conf import settings
from django.core.management import call_command

from conference.models import KnowledgeChunk, Session, Speaker

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "fixtures" / "knowledge.json.gz"
SOURCES = ROOT / "documents"
TECH = SOURCES / "tech_knowledge.yaml"
AGENDA = SOURCES / "event_materials.yaml"

SPEAKERS = {"Орест Новосад", "Олександр Шипулін", "Влад Гетманенко"}

REQUIRED = [
    "NumPy",
    "Pandas",
    "Polars",
    "scikit-learn",
    "OpenCV",
    "Matplotlib",
    "Plotly",
    "Jupyter",
    "PyTorch",
    "Hugging Face",
    "ONNX",
    "MLflow",
    "BentoML",
    "TorchServe",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Celery",
    "Redis",
    "LangChain",
    "LangGraph",
    "LlamaIndex",
    "pgvector",
    "PostgreSQL",
    "OpenAI",
    "Claude",
    "Ollama",
    "Django Channels",
]

needs_sources = pytest.mark.skipif(
    not AGENDA.exists(), reason="Вихідні матеріали лежать лише локально в documents/."
)


def _dump_rows(model: str) -> list[dict]:
    rows = json.loads(gzip.decompress(DUMP.read_bytes()))
    return [row for row in rows if row["model"] == model]


def test_dump_has_real_speakers_and_every_session_is_indexed():
    speakers = {row["fields"]["name"] for row in _dump_rows("conference.speaker")}
    assert SPEAKERS <= speakers
    chunks = _dump_rows("conference.knowledgechunk")
    indexed = {row["fields"]["session"] for row in chunks}
    sessions = _dump_rows("conference.session")
    assert sessions
    assert all(row["pk"] in indexed for row in sessions)
    vector = chunks[0]["fields"]["embedding"]
    assert vector.count(",") + 1 == settings.EMBEDDING_DIMENSIONS


def test_dump_covers_every_featured_technology():
    blob = "\n".join(row["fields"]["content"] for row in _dump_rows("conference.knowledgechunk"))
    missing = [name for name in REQUIRED if name not in blob]
    assert missing == []


@pytest.mark.django_db
def test_load_knowledge_restores_dump_once():
    call_command("load_knowledge")
    total = KnowledgeChunk.objects.count()
    assert total == len(_dump_rows("conference.knowledgechunk"))
    assert set(Speaker.objects.values_list("name", flat=True)) >= SPEAKERS

    KnowledgeChunk.objects.first().delete()
    call_command("load_knowledge")
    assert KnowledgeChunk.objects.count() == total - 1
    call_command("load_knowledge", force=True)
    assert KnowledgeChunk.objects.count() == total


@pytest.mark.django_db
def test_seed_event_prunes_sessions_missing_from_sources(tmp_path, settings, monkeypatch):
    (tmp_path / "event_materials.yaml").write_text(
        yaml.safe_dump(
            {
                "speakers": [{"slug": "vlad", "name": "Влад Гетманенко"}],
                "sessions": [
                    {
                        "slug": "block-3",
                        "block_number": 3,
                        "kind": "talk",
                        "title": "LLM, RAG і AI-агенти",
                        "speakers": ["vlad"],
                        "paragraphs": ["Блок 3 веде Влад Гетманенко."],
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "tech_knowledge.yaml").write_text("topics: []\n", encoding="utf-8")
    settings.KNOWLEDGE_SOURCE_DIR = tmp_path
    settings.OPENAI_API_KEY = "test"
    monkeypatch.setattr(
        "conference.management.commands.seed_event.embed_documents",
        lambda texts: [[0.0] * settings.EMBEDDING_DIMENSIONS for _ in texts],
    )
    stale = Session.objects.create(
        slug="old", block_number=1, kind=Session.Kind.TALK, title="Стара", body="Стара сесія."
    )
    Speaker.objects.create(slug="block1", name="Спікер Блоку 1 (уточнюється)")
    KnowledgeChunk.objects.create(
        session=stale, content="Стара сесія.", content_hash="c" * 64, embedding=[0.0] * 1536
    )

    call_command("seed_event")

    assert list(Session.objects.values_list("slug", flat=True)) == ["block-3"]
    assert list(Speaker.objects.values_list("slug", flat=True)) == ["vlad"]
    assert not KnowledgeChunk.objects.filter(content_hash="c" * 64).exists()
    assert KnowledgeChunk.objects.filter(session__slug="block-3").exists()


@needs_sources
def test_sources_are_unique_and_code_backed():
    topics = yaml.safe_load(TECH.read_text(encoding="utf-8"))["topics"]
    agenda = yaml.safe_load(AGENDA.read_text(encoding="utf-8"))
    slugs = [topic["slug"] for topic in topics]
    session_slugs = {row["slug"] for row in agenda["sessions"]}
    known = {row["slug"] for row in agenda["speakers"]}
    assert {row["name"] for row in agenda["speakers"]} >= SPEAKERS
    assert len(slugs) == len(set(slugs))
    assert len(topics) >= 20
    for topic in topics:
        assert topic["slug"] not in session_slugs
        assert topic["block_number"] in {1, 2, 3}
        assert set(topic["speakers"]) <= known
        body = "\n\n".join(topic["paragraphs"])
        assert body.count("```") >= 2
        assert "kind" not in topic
    for session in agenda["sessions"]:
        assert set(session["speakers"]) <= known
