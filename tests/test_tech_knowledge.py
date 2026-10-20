from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TECH = ROOT / "fixtures" / "tech_knowledge.yaml"
AGENDA = ROOT / "fixtures" / "event_materials.yaml"

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


def _topics():
    data = yaml.safe_load(TECH.read_text(encoding="utf-8"))
    return data["topics"]


def test_topics_are_unique_and_code_backed():
    topics = _topics()
    agenda = yaml.safe_load(AGENDA.read_text(encoding="utf-8"))
    slugs = [topic["slug"] for topic in topics]
    session_slugs = {row["slug"] for row in agenda["sessions"]}
    known = {row["slug"] for row in agenda["speakers"]}
    assert len(slugs) == len(set(slugs))
    assert len(topics) >= 20
    for topic in topics:
        assert topic["slug"] not in session_slugs
        assert topic["block_number"] in {1, 2, 3}
        assert set(topic["speakers"]) <= known
        body = "\n\n".join(topic["paragraphs"])
        assert body.count("```") >= 2
        assert "kind" not in topic


def test_every_featured_technology_is_covered():
    blob = TECH.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED if name not in blob]
    assert missing == []
