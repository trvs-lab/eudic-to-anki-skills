#!/usr/bin/env python3
"""Build final week import JSON: merge minimal coach mapping + optional CSV metadata.

The default `eudic-to-anki` skill path is agent-written IPA only; this helper still
applies Eudic `phon` when building from `minimal_coach_week.json` unless you change it to rely on
agent-filled `pronunciation` in the mapping instead. It also preserves `context_line` as
`source_context` for source-first examples.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path

from coach_fields import fuse_pos_into_meaning

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def _load_build_module():
    path = SCRIPT_DIR / "build_dia_json_from_csv.py"
    spec = importlib.util.spec_from_file_location("build_dia", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load build_dia_json_from_csv.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def phon_map_first_row(csv_path: Path, build_mod) -> dict[str, str]:
    first: dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip()
            if not w or w in first:
                continue
            first[w] = build_mod.clean_eudic_phon(str(row.get("phon") or ""), word=w)
    return first


def source_context_map_first_row(csv_path: Path, build_mod) -> dict[str, str]:
    first: dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip()
            if not w or w in first:
                continue
            first[w] = build_mod.clean_context_line(row.get("context_line") or "")
    return first


def note_pos(note: dict) -> str:
    for key in ("part_of_speech", "pos", "词性"):
        value = note.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--coach-json", type=Path, required=True, help="Word -> coach fields (minimal)")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--tags-from",
        type=Path,
        default=None,
        help="Optional previous import JSON to copy source/tags per word",
    )
    args = p.parse_args()

    coach = json.loads(args.coach_json.read_text(encoding="utf-8"))
    if not isinstance(coach, dict):
        raise SystemExit("coach-json must be an object mapping word -> fields")

    build_mod = _load_build_module()
    phon = phon_map_first_row(args.csv, build_mod)
    source_contexts = source_context_map_first_row(args.csv, build_mod)

    tags_meta: dict[str, dict] = {}
    if args.tags_from and args.tags_from.exists():
        prev = json.loads(args.tags_from.read_text(encoding="utf-8"))
        for n in prev.get("notes", []):
            w = str(n.get("word") or "").strip()
            if w:
                tags_meta[w] = {
                    "source": n.get("source", "eudic cloud"),
                    "source_context": n.get("source_context", ""),
                    "tags": n.get("tags", []),
                }

    notes: list[dict] = []
    seen: set[str] = set()
    with args.csv.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip()
            if not w or w in seen:
                continue
            seen.add(w)
            if w not in coach:
                raise SystemExit(f"Missing coach entry for word: {w!r}")
            c = coach[w]
            meta = tags_meta.get(
                w, {"source": "eudic cloud", "tags": ["english", "vocab", "eudic"]}
            )
            ipa = phon.get(w, "")
            raw_meaning = c.get("meaning") or []
            if not isinstance(raw_meaning, list):
                meaning_list = [str(raw_meaning).strip()] if str(raw_meaning).strip() else []
            else:
                meaning_list = [str(x).strip() for x in raw_meaning if str(x).strip()]
            pos = note_pos(c)
            meaning = fuse_pos_into_meaning(meaning_list, pos)
            notes.append(
                {
                    "word": w,
                    "pronunciation": ipa or str(c.get("pronunciation") or ""),
                    "part_of_speech": pos,
                    "meaning": meaning,
                    "english_definition": c["english_definition"],
                    "root": c["root"],
                    "example": c["example"],
                    "collocations": c["collocations"],
                    "audio_html": "",
                    "source": meta["source"],
                    "source_context": meta.get("source_context") or source_contexts.get(w, ""),
                    "tags": meta["tags"],
                }
            )

    args.output.write_text(
        json.dumps({"notes": notes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(notes)} notes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
