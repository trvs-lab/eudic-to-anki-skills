"""Shared field helpers for context-anchor vocabulary notes."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_POS_LEAD_RE = re.compile(r"^[a-z]{1,12}\.", re.I)

LEARNING_GROUP_VALUES = ("learn", "defer", "skip", "reject")
MANAGED_LEARNING_GROUPS = ("learn", "defer", "skip")
SENTENCE_ORIGIN_VALUES = ("source", "adapted", "generated")

CARD_SENTENCE_KEYS = ("card_sentence", "卡片例句", "example", "例句")
SENTENCE_ORIGIN_KEYS = ("sentence_origin", "例句来源")
SOURCE_CONTEXT_KEYS = ("source_context", "原始来源")
SOURCE_CHUNK_KEYS = ("source_chunk", "来源词块")
SOURCE_CHUNK_MEANING_KEYS = ("source_chunk_meaning", "词块释义")
WORD_FAMILY_KEYS = ("word_family", "词族构词", "root", "词根")


def first_text_field(note: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = note.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def normalize_optional_text(value: Any) -> str:
    """Normalize an optional authored field without preserving placeholders."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text == "-" else text


def normalize_string_list(value: Any, *, separator: str | None = None) -> list[str]:
    """Return non-empty strings from a scalar or authored list value."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = normalize_optional_text(value)
    if not text:
        return []
    if separator is None:
        return [text]
    return [part.strip() for part in text.split(separator) if part.strip()]


def normalize_word_key(value: object) -> str:
    """Return the stable identity used for one-word-one-note matching."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", text.strip()).casefold()


def normalize_learning_group(value: object, *, default: str = "") -> str:
    text = str(value or "").strip().lower()
    return text or default


def meaning_line_has_pos_prefix(line: str) -> bool:
    return bool(_POS_LEAD_RE.match(line.strip()))


def fuse_pos_into_meaning(meaning_values: list[str], pos: str) -> list[str]:
    """Prepend a legacy POS value to the first meaning line when useful."""
    pos_stripped = (pos or "").strip()
    if not pos_stripped or pos_stripped == "-":
        return list(meaning_values)
    fused: list[str] = []
    for raw in meaning_values:
        line = raw.strip()
        if not line:
            continue
        if not fused and not meaning_line_has_pos_prefix(line):
            fused.append(f"{pos_stripped} {line}".strip())
        else:
            fused.append(line)
    return fused or [pos_stripped]
