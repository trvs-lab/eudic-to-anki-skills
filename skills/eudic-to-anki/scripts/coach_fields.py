"""Shared helpers for TRVS-Lab coach JSON (meaning lines + optional legacy POS)."""

from __future__ import annotations

import re

_POS_LEAD_RE = re.compile(r"^[a-z]{1,12}\.", re.I)


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
