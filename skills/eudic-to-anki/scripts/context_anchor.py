"""Pure context-anchor encounter and field-merging logic."""

from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

from coach_fields import (
    CARD_SENTENCE_KEYS,
    LEARNING_GROUP_VALUES,
    SENTENCE_ORIGIN_KEYS,
    SOURCE_CHUNK_KEYS,
    SOURCE_CHUNK_MEANING_KEYS,
    SOURCE_CONTEXT_KEYS,
    WORD_FAMILY_KEYS,
    first_text_field,
    fuse_pos_into_meaning,
    normalize_learning_group,
    normalize_word_key,
)

HISTORY_LIMIT = 3


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text == "-" else text


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split("|") if part.strip()]


def note_learning_group(note: dict[str, Any], *, default: str = "") -> str:
    for key in ("learning_group", "学习分组", "group"):
        if note.get(key) not in (None, ""):
            group = normalize_learning_group(note[key])
            if group not in LEARNING_GROUP_VALUES:
                raise ValueError(
                    f"learning_group must be one of {', '.join(LEARNING_GROUP_VALUES)} "
                    f"(got {note[key]!r})"
                )
            return group
    if default in LEARNING_GROUP_VALUES:
        return default
    raise ValueError(
        f"learning_group must be one of {', '.join(LEARNING_GROUP_VALUES)} (got empty)"
    )


def _normalized_identity_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def encounter_id(note: dict[str, Any]) -> str:
    explicit = normalize_text(note.get("encounter_id"))
    if explicit:
        return explicit
    identity = {
        "category": normalize_text(
            note.get("category_id") or note.get("category_name")
        ),
        "word": normalize_word_key(note.get("word") or note.get("单词")),
        "time": normalize_text(
            note.get("add_time_utc")
            or note.get("add_time_local")
            or note.get("encountered_at")
        ),
        "source": _normalized_identity_text(
            first_text_field(note, SOURCE_CONTEXT_KEYS)
        ),
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def encounter_from_note(note: dict[str, Any]) -> dict[str, str]:
    return {
        "id": encounter_id(note),
        "at": normalize_text(
            note.get("add_time_utc")
            or note.get("add_time_local")
            or note.get("encountered_at")
        ),
        "raw_source": first_text_field(note, SOURCE_CONTEXT_KEYS),
        "card_sentence": first_text_field(note, CARD_SENTENCE_KEYS),
        "origin": first_text_field(note, SENTENCE_ORIGIN_KEYS),
    }


def parse_encounters(value: Any) -> list[dict[str, str]]:
    if isinstance(value, dict):
        value = value.get("value")
    if not value:
        return []
    try:
        raw = json.loads(str(value))
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("遇见记录 is not valid JSON") from exc
    if not isinstance(raw, list):
        raise ValueError("遇见记录 must be a JSON array")
    records: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError("遇见记录 contains an invalid record")
        records.append(
            {
                "id": normalize_text(item.get("id")),
                "at": normalize_text(item.get("at")),
                "raw_source": normalize_text(item.get("raw_source")),
                "card_sentence": normalize_text(item.get("card_sentence")),
                "origin": normalize_text(item.get("origin")),
            }
        )
    return records


def _field(existing_fields: dict[str, Any] | None, name: str) -> str:
    if not existing_fields:
        return ""
    raw = existing_fields.get(name)
    if isinstance(raw, dict):
        raw = raw.get("value")
    return normalize_text(raw)


def _sorted_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    indexed = list(enumerate(records))
    indexed.sort(key=lambda item: (item[1].get("at", ""), item[0]))
    return [record for _index, record in indexed]


def _history(records: list[dict[str, str]], latest_id: str) -> str:
    visible: list[str] = []
    for record in _sorted_records(records):
        if record["id"] == latest_id or record.get("origin") == "generated":
            continue
        sentence = record.get("card_sentence") or record.get("raw_source")
        if sentence and sentence not in visible:
            visible.append(sentence)
    return "<br>".join(html.escape(item) for item in visible[-HISTORY_LIMIT:])


def build_fields(
    note: dict[str, Any],
    audio_html: str,
    *,
    existing_fields: dict[str, Any] | None = None,
    forced_group: str | None = None,
) -> tuple[dict[str, str], bool]:
    """Build Anki fields and report whether this is a distinct encounter."""
    record = encounter_from_note(note)
    existing_records = parse_encounters(
        existing_fields.get("遇见记录") if existing_fields else None
    )
    if record["id"] in {item["id"] for item in existing_records}:
        return {
            name: _field(existing_fields, name) for name in CONTEXT_ANCHOR_FIELDS
        }, False

    records = _sorted_records([*existing_records, record])
    latest_record = records[-1]
    word = first_text_field(note, ("word", "单词"))
    meanings = normalize_list(
        note.get("meaning") or note.get("语境释义") or note.get("释义")
    )
    pos = first_text_field(note, ("part_of_speech", "pos", "词性"))
    meanings = fuse_pos_into_meaning(meanings, pos)
    group = forced_group or note_learning_group(note)
    latest_at = latest_record["at"] or _field(existing_fields, "最近遇见")
    incoming_is_latest = latest_record["id"] == record["id"]
    fields = {
        "单词": word,
        "规范词形": normalize_word_key(word),
        "音标": first_text_field(note, ("pronunciation", "音标")),
        "语境释义": "；".join(meanings),
        "英英": first_text_field(note, ("english_definition", "definition_en", "英英")),
        "原始来源": record["raw_source"],
        "卡片例句": record["card_sentence"],
        "例句来源": record["origin"],
        "来源词块": first_text_field(note, SOURCE_CHUNK_KEYS),
        "词块释义": first_text_field(note, SOURCE_CHUNK_MEANING_KEYS),
        "词族构词": first_text_field(note, WORD_FAMILY_KEYS),
        "历史语境": _history(records, latest_record["id"]),
        "遇见次数": str(
            max(len(records), int(_field(existing_fields, "遇见次数") or "0") + 1)
        ),
        "最近遇见": latest_at,
        "遇见记录": json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        "学习分组": group,
        "发音": audio_html
        or _field(existing_fields, "发音")
        or first_text_field(note, ("audio_html", "发音")),
    }
    if existing_fields and not incoming_is_latest:
        for name in (
            "单词",
            "规范词形",
            "音标",
            "语境释义",
            "英英",
            "原始来源",
            "卡片例句",
            "例句来源",
            "来源词块",
            "词块释义",
            "词族构词",
        ):
            fields[name] = _field(existing_fields, name)
    return fields, True


CONTEXT_ANCHOR_FIELDS = (
    "单词",
    "规范词形",
    "音标",
    "语境释义",
    "英英",
    "原始来源",
    "卡片例句",
    "例句来源",
    "来源词块",
    "词块释义",
    "词族构词",
    "历史语境",
    "遇见次数",
    "最近遇见",
    "遇见记录",
    "学习分组",
    "发音",
)
