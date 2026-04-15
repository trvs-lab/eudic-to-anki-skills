#!/usr/bin/env python3
"""Merge coach-only JSON files with partial.json (tags, source). Coach files: {"notes":[...]}."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coach_fields import fuse_pos_into_meaning


def _normalize_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _note_pos(note: dict) -> str:
    for key in ("part_of_speech", "pos", "词性"):
        value = note.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--partial", type=Path, required=True)
    p.add_argument("--coach", type=Path, action="append", required=True)
    p.add_argument("-o", "--output", type=Path, required=True)
    args = p.parse_args()

    partial = json.loads(args.partial.read_text(encoding="utf-8"))
    meta = {n["word"]: {"source": n.get("source"), "tags": n.get("tags")} for n in partial.get("notes", [])}

    by_word: dict[str, dict] = {}
    for path in args.coach:
        data = json.loads(path.read_text(encoding="utf-8"))
        for n in data.get("notes", []):
            w = str(n.get("word") or "").strip()
            if w:
                by_word[w] = n

    out_notes: list[dict] = []
    for n in partial.get("notes", []):
        w = n["word"]
        c = by_word.get(w)
        if not c:
            print(f"missing coach for {w!r}", file=sys.stderr)
            return 1
        m = meta[w]
        pos = _note_pos(c)
        meaning = fuse_pos_into_meaning(_normalize_list(c.get("meaning", [])), pos)
        out_notes.append(
            {
                "word": w,
                "pronunciation": c.get("pronunciation", ""),
                "part_of_speech": pos,
                "meaning": meaning,
                "english_definition": c.get("english_definition", ""),
                "root": c.get("root", ""),
                "example": c.get("example", ""),
                "collocations": c.get("collocations", []),
                "audio_html": c.get("audio_html", ""),
                "source": m.get("source"),
                "tags": m.get("tags"),
            }
        )

    args.output.write_text(
        json.dumps({"notes": out_notes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(out_notes)} notes -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
