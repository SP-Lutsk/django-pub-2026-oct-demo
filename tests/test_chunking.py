from conference.chunking import chunk_text


def test_packs_short_paragraphs():
    text = "Альфа параграф.\n\nБета параграф."
    assert chunk_text(text, size=800) == ["Альфа параграф.\n\nБета параграф."]


def test_splits_when_size_exceeded():
    text = "А" * 50 + "\n\n" + "Б" * 50
    chunks = chunk_text(text, size=60, overlap=10)
    assert len(chunks) == 2
    assert chunks[0].startswith("А")
    assert "Б" in chunks[1]


def test_empty_text():
    assert chunk_text("   \n\n  ") == []


def test_fenced_code_with_blank_lines_stays_intact():
    text = (
        "Короткий вступ до прикладу.\n\n"
        "```python\n"
        "def score(values):\n"
        "\n"
        "    return sum(values)\n"
        "```\n\n"
        "Після прикладу йде пояснення порогу."
    )
    chunks = chunk_text(text, size=40, overlap=0)
    fences = [chunk for chunk in chunks if "def score" in chunk]
    assert len(fences) == 1
    assert "return sum(values)" in fences[0]
    assert fences[0].count("```") == 2


def test_long_code_block_is_not_split():
    body = "x = 1\n" * 80
    text = f"```python\n{body}```"
    chunks = chunk_text(text, size=50, overlap=10)
    assert chunks == [text.strip()]
