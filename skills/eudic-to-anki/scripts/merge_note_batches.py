#!/usr/bin/env python3
"""Merge { \"notes\": [...] } JSON files into one import file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="+", type=Path, help="JSON files with top-level 'notes' array")
    p.add_argument("-o", "--output", type=Path, required=True)
    args = p.parse_args()
    all_notes: list[object] = []
    for path in args.inputs:
        data = json.loads(path.read_text(encoding="utf-8"))
        notes = data.get("notes")
        if not isinstance(notes, list):
            print(f"skip (no notes list): {path}", file=sys.stderr)
            continue
        all_notes.extend(notes)
    args.output.write_text(
        json.dumps({"notes": all_notes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_notes)} notes -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
