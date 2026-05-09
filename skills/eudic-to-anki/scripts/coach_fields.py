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
