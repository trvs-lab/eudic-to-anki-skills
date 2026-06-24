"""Shared helpers for TRVS-Lab coach JSON."""

from __future__ import annotations

import re

_POS_LEAD_RE = re.compile(r"^[a-z]{1,12}\.", re.I)

LEARNING_PRIORITY_VALUES = ("focus", "passive", "ignore")
LEARNING_PRIORITY_MARKERS = {
    "focus": "★",
    "passive": "◇",
    "ignore": "×",
}
TARGET_CHUNK_KEYS = ("target_chunk", "目标短语块")
TARGET_CHUNK_MEANING_KEYS = ("target_chunk_meaning", "短语块锚点")
TARGET_CHUNK_CLOZE_KEYS = ("target_chunk_cloze", "短语块挖空")


def first_text_field(note: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = note.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def meaning_line_has_pos_prefix(line: str) -> bool:
    return bool(_POS_LEAD_RE.match(line.strip()))


def fuse_pos_into_meaning(meaning_values: list[str], pos: str) -> list[str]:
    """Prepend legacy `pos` to first meaning line when needed."""
    pos_stripped = (pos or "").strip()
    if not pos_stripped or pos_stripped == "-":
        return list(meaning_values)
    fused: list[str] = []
    for i, raw in enumerate(meaning_values):
        line = raw.strip()
        if not line:
            continue
        if i == 0 and not meaning_line_has_pos_prefix(line):
            fused.append(f"{pos_stripped} {line}".strip())
        else:
            fused.append(line)
    if not fused:
        return [pos_stripped] if pos_stripped else []
    return fused


def normalize_learning_priority(value: object, *, default: str = "") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return default
    return text


def learning_priority_marker(priority: str) -> str:
    return LEARNING_PRIORITY_MARKERS.get(priority, "")
