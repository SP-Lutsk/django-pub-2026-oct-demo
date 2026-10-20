from __future__ import annotations


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    units = _units(text)
    if not units:
        stripped = text.strip()
        return [stripped] if stripped else []

    chunks: list[str] = []
    current = ""
    for unit in units:
        if len(unit) > size:
            if current:
                chunks.append(current.strip())
                current = ""
            if _is_fence(unit):
                chunks.append(unit)
            else:
                chunks.extend(_split_long(unit, size, overlap))
            continue
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) <= size:
            current = candidate
            continue
        chunks.append(current.strip())
        tail = current[-overlap:].strip() if overlap else ""
        if tail.count("```") % 2 == 1:
            tail = ""
        current = f"{tail}\n\n{unit}".strip() if tail else unit
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _units(text: str) -> list[str]:
    units: list[str] = []
    prose: list[str] = []
    fence: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            if not in_fence:
                units.extend(_prose_units("\n".join(prose)))
                prose = []
                fence = [line]
                in_fence = True
            else:
                fence.append(line)
                units.append("\n".join(fence).strip())
                fence = []
                in_fence = False
            continue
        if in_fence:
            fence.append(line)
        else:
            prose.append(line)
    if fence:
        units.append("\n".join(fence).strip())
    units.extend(_prose_units("\n".join(prose)))
    return [unit for unit in units if unit.strip()]


def _prose_units(text: str) -> list[str]:
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def _is_fence(unit: str) -> bool:
    return unit.startswith("```")


def _split_long(paragraph: str, size: int, overlap: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    step = max(size - overlap, 1)
    while start < len(paragraph):
        pieces.append(paragraph[start : start + size].strip())
        start += step
    return [piece for piece in pieces if piece]
