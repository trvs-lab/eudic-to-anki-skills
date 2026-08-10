#!/usr/bin/env python3
"""Merge agent-authored coaching fields with every exported Eudic encounter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coach_fields import (
    fuse_pos_into_meaning,
    normalize_string_list,
    normalize_word_key,
)

COACH_FIELDS = (
    "pronunciation",
    "part_of_speech",
    "english_definition",
    "word_family",
    "card_sentence",
    "sentence_origin",
    "source_chunk",
    "source_chunk_meaning",
    "learning_group",
    "audio_html",
)
ENCOUNTER_FIELDS = (
    "source",
    "source_context",
    "category_id",
    "category_name",
    "add_time_utc",
    "add_time_local",
    "tags",
)


def _pos(note: dict) -> str:
    return str(
        note.get("part_of_speech") or note.get("pos") or note.get("词性") or ""
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", type=Path, required=True)
    parser.add_argument("--coach", type=Path, action="append", required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    partial = json.loads(args.partial.read_text(encoding="utf-8"))
    encounters = partial.get("notes", [])
    coaches: dict[str, list[dict]] = {}
    for path in args.coach:
        data = json.loads(path.read_text(encoding="utf-8"))
        for note in data.get("notes", []):
            key = normalize_word_key(note.get("word"))
            if key:
                coaches.setdefault(key, []).append(note)

    output: list[dict] = []
    positions: dict[str, int] = {}
    for encounter in encounters:
        word = str(encounter.get("word") or "").strip()
        key = normalize_word_key(word)
        candidates = coaches.get(key, [])
        if not candidates:
            print(f"missing coach for {word!r}", file=sys.stderr)
            return 1
        position = positions.get(key, 0)
        coach = candidates[position] if position < len(candidates) else candidates[-1]
        positions[key] = position + 1
        if len(candidates) == 1 and position > 0:
            origin = str(coach.get("sentence_origin") or "")
            if origin == "adapted":
                print(
                    f"{word!r} has multiple source encounters but only one adapted coach; "
                    "author one coach entry per encounter",
                    file=sys.stderr,
                )
                return 1
        pos = _pos(coach)
        merged = {
            "word": word,
            "meaning": fuse_pos_into_meaning(
                normalize_string_list(coach.get("meaning")), pos
            ),
        }
        for field in COACH_FIELDS:
            if field == "part_of_speech":
                merged[field] = pos
            else:
                merged[field] = coach.get(field, "")
        for field in ENCOUNTER_FIELDS:
            default: object = [] if field == "tags" else ""
            merged[field] = encounter.get(field, default)
        if len(candidates) == 1 and str(coach.get("sentence_origin") or "") == "source":
            merged["card_sentence"] = merged["source_context"]
        output.append(merged)

    args.output.write_text(
        json.dumps({"notes": output}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(output)} encounter notes -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
