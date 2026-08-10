#!/usr/bin/env python3
"""Merge a word-to-coach mapping with all rows in an Eudic CSV export."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path

from coach_fields import fuse_pos_into_meaning, normalize_word_key

SCRIPT_DIR = Path(__file__).resolve().parent


def _load_build_module():
    path = SCRIPT_DIR / "build_dia_json_from_csv.py"
    spec = importlib.util.spec_from_file_location("build_dia", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load build_dia_json_from_csv.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--coach-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tags-from", type=Path)
    args = parser.parse_args()

    coach_raw = json.loads(args.coach_json.read_text(encoding="utf-8"))
    if not isinstance(coach_raw, dict):
        raise SystemExit("coach-json must map word -> fields")
    coaches = {normalize_word_key(word): value for word, value in coach_raw.items()}
    build = _load_build_module()
    notes: list[dict] = []
    with args.csv.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            word = str(row.get("word") or "").strip()
            if not word:
                continue
            coach = coaches.get(normalize_word_key(word))
            if coach is None:
                raise SystemExit(f"Missing coach entry for word: {word!r}")
            pos = str(
                coach.get("part_of_speech")
                or coach.get("pos")
                or coach.get("词性")
                or ""
            ).strip()
            notes.append(
                {
                    "word": word,
                    "pronunciation": str(coach.get("pronunciation") or "")
                    or build.clean_eudic_phon(str(row.get("phon") or ""), word=word),
                    "part_of_speech": pos,
                    "meaning": fuse_pos_into_meaning(_list(coach.get("meaning")), pos),
                    "english_definition": coach.get("english_definition", ""),
                    "word_family": coach.get("word_family", ""),
                    "card_sentence": coach.get("card_sentence", ""),
                    "sentence_origin": coach.get("sentence_origin", ""),
                    "source_chunk": coach.get("source_chunk", ""),
                    "source_chunk_meaning": coach.get("source_chunk_meaning", ""),
                    "learning_group": coach.get("learning_group", ""),
                    "audio_html": coach.get("audio_html", ""),
                    "source": "eudic cloud",
                    "source_context": build.clean_context_line(
                        row.get("context_line") or ""
                    ),
                    "category_id": row.get("category_id", ""),
                    "category_name": row.get("category_name", ""),
                    "add_time_utc": row.get("add_time_utc", ""),
                    "add_time_local": row.get("add_time_local", ""),
                    "tags": [],
                }
            )
    args.output.write_text(
        json.dumps({"notes": notes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(notes)} encounters to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
