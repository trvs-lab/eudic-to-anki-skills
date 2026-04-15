#!/usr/bin/env python3
"""Validate TRVS-Lab coach JSON before AnkiConnect import.

Catches common agent pipeline failures: UTF-8 replacement char (U+FFFD) in IPA,
malformed pronunciation slashes, invalid JSON. Run after writing <notes-json>, before
`ankiconnect_import.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from coach_fields import meaning_line_has_pos_prefix

REPLACEMENT = "\ufffd"
# CJK + common extension blocks; root with morphological "+" must include a Chinese gloss (skill rule).
_CJK_RE = re.compile(r"[\u3007\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002ceaf\U00030000-\U000323af]")
_MOJIBAKE_MARKERS = ("Ã", "Â", "Ð", "Ñ")
_ROOT_SEGMENT_RE = re.compile(r"^[^+（）()]{1,40}（[^（）]{1,20}）$")
_ROOT_BANNED_EN_RE = re.compile(
    r"\b(past\s*participle|participle|suffix|prefix|form|tense|with\s*-?ed)\b",
    re.I,
)
REQUIRED_KEYS = (
    "word",
    "pronunciation",
    "part_of_speech",
    "meaning",
    "english_definition",
    "root",
    "example",
    "collocations",
    "audio_html",
)


def _has_replacement(s: str) -> bool:
    return REPLACEMENT in s


def _note_pos(note: dict[str, Any]) -> str:
    for key in ("part_of_speech", "pos", "词性"):
        value = note.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _validate_root_value(root_val: str, word: str, index: int) -> list[str]:
    errs: list[str] = []
    rs = root_val.strip()
    if not rs:
        errs.append(
            f"note[{index}] word={word!r}: root must not be empty (use '-' if unsplittable)"
        )
        return errs
    if rs == "-":
        return errs

    if "(" in rs or ")" in rs:
        errs.append(
            f"note[{index}] word={word!r}: root must use full-width Chinese parentheses （）, not ()"
        )
    if _ROOT_BANNED_EN_RE.search(rs):
        errs.append(
            f"note[{index}] word={word!r}: root looks like English grammar explanation; "
            f"use 形式（中文义） segments (got {root_val!r})"
        )
    if _CJK_RE.search(rs) is None:
        errs.append(
            f"note[{index}] word={word!r}: root must contain Chinese glosses (got {root_val!r})"
        )

    parts = [p.strip() for p in rs.split("+")]
    if any(not p for p in parts):
        errs.append(
            f"note[{index}] word={word!r}: root has empty segment around '+' (got {root_val!r})"
        )
        return errs

    for p in parts:
        if not _ROOT_SEGMENT_RE.match(p):
            errs.append(
                f"note[{index}] word={word!r}: invalid root segment {p!r}; expected 形式（中文义）"
            )
    return errs


def _check_note(note: dict[str, Any], index: int, require_ipa_slashes: bool) -> list[str]:
    errs: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in note:
            errs.append(f"note[{index}] missing key {key!r} (word={note.get('word')!r})")

    w = str(note.get("word") or "").strip()
    pron = note.get("pronunciation")
    if pron is None:
        errs.append(f"note[{index}] word={w!r}: pronunciation must be present (use \"\" if empty)")
        return errs
    if not isinstance(pron, str):
        errs.append(f"note[{index}] word={w!r}: pronunciation must be a string")
        return errs

    if _has_replacement(pron):
        errs.append(
            f"note[{index}] word={w!r}: pronunciation contains U+FFFD (replacement character)—"
            f"encoding was corrupted; rewrite IPA via UTF-8 file write or \\u escapes, "
            f"not shell heredocs."
        )

    if pron.strip():
        if require_ipa_slashes and not (pron.startswith("/") and pron.endswith("/")):
            errs.append(
                f"note[{index}] word={w!r}: non-empty pronunciation should be one AmE IPA "
                f"wrapped in /.../ (got {pron!r})"
            )
        if any(m in pron for m in _MOJIBAKE_MARKERS):
            errs.append(
                f"note[{index}] word={w!r}: pronunciation contains mojibake markers "
                f"(e.g. Ã/Â/Ð/Ñ), likely encoding corruption: {pron!r}"
            )

    for key in ("word", "english_definition", "root", "example"):
        val = note.get(key, "")
        if val is not None and not isinstance(val, str):
            errs.append(
                f"note[{index}] word={w!r}: field {key!r} must be a string "
                f"(got {type(val).__name__})"
            )
        if isinstance(val, str) and _has_replacement(val):
            errs.append(f"note[{index}] word={w!r}: field {key!r} contains U+FFFD")
        if isinstance(val, str) and key in ("word", "english_definition", "root", "example"):
            if any(m in val for m in _MOJIBAKE_MARKERS):
                errs.append(
                    f"note[{index}] word={w!r}: field {key!r} contains mojibake markers "
                    f"(e.g. Ã/Â/Ð/Ñ): {val!r}"
                )

    meanings = note.get("meaning")
    if meanings is not None:
        if not isinstance(meanings, list):
            errs.append(
                f"note[{index}] word={w!r}: meaning must be an array of strings "
                f"(got {type(meanings).__name__})"
            )
        else:
            if not any(isinstance(m, str) and m.strip() for m in meanings):
                errs.append(f"note[{index}] word={w!r}: meaning must not be empty")
            for j, m in enumerate(meanings):
                if not isinstance(m, str):
                    errs.append(
                        f"note[{index}] word={w!r}: meaning[{j}] must be string "
                        f"(got {type(m).__name__})"
                    )
                    continue
                if _has_replacement(m):
                    errs.append(f"note[{index}] word={w!r}: meaning[{j}] contains U+FFFD")
                if any(mark in m for mark in _MOJIBAKE_MARKERS):
                    errs.append(
                        f"note[{index}] word={w!r}: meaning[{j}] contains mojibake markers: {m!r}"
                    )
                if m.strip() and not meaning_line_has_pos_prefix(m):
                    errs.append(
                        f"note[{index}] word={w!r}: meaning[{j}] must start with a POS marker "
                        f"like 'n.', 'vt.', 'vi.', 'adj.' or 'adv.' (got {m!r})"
                    )

    pos = _note_pos(note)
    if not pos:
        errs.append(
            f"note[{index}] word={w!r}: missing non-empty 'part_of_speech' "
            "(use values like 'n.', 'vt.', 'vi.', 'adj.', 'adv.')"
        )
    elif not meaning_line_has_pos_prefix(pos):
        errs.append(
            f"note[{index}] word={w!r}: part_of_speech must look like a POS marker "
            f"(got {pos!r})"
        )

    colls = note.get("collocations")
    if colls is not None:
        if not isinstance(colls, list):
            errs.append(
                f"note[{index}] word={w!r}: collocations must be an array of strings "
                f"(got {type(colls).__name__})"
            )
        else:
            for j, c in enumerate(colls):
                if not isinstance(c, str):
                    errs.append(
                        f"note[{index}] word={w!r}: collocations[{j}] must be string "
                        f"(got {type(c).__name__})"
                    )
                    continue
                if _has_replacement(c):
                    errs.append(f"note[{index}] word={w!r}: collocations[{j}] contains U+FFFD")
                if any(mark in c for mark in _MOJIBAKE_MARKERS):
                    errs.append(
                        f"note[{index}] word={w!r}: collocations[{j}] contains mojibake markers: {c!r}"
                    )

    root_val = note.get("root", "")
    if isinstance(root_val, str):
        errs.extend(_validate_root_value(root_val, w, index))

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("json_path", type=Path, help="Import JSON with top-level 'notes' array")
    parser.add_argument(
        "--no-require-ipa-slashes",
        action="store_true",
        help="Do not require /.../ around non-empty pronunciation (not recommended).",
    )
    args = parser.parse_args()

    path = args.json_path
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"error: {path} is not valid UTF-8: {exc}", file=sys.stderr)
        return 2

    if _has_replacement(raw):
        print(
            f"error: {path} contains U+FFFD at file level—re-save as UTF-8 without corrupting IPA.",
            file=sys.stderr,
        )
        return 2

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 2

    notes = data.get("notes")
    if not isinstance(notes, list):
        print("error: top-level 'notes' must be an array", file=sys.stderr)
        return 2

    require_slashes = not args.no_require_ipa_slashes
    all_errs: list[str] = []
    for i, note in enumerate(notes):
        if not isinstance(note, dict):
            all_errs.append(f"note[{i}] must be an object, got {type(note).__name__}")
            continue
        all_errs.extend(_check_note(note, i, require_slashes))

    if all_errs:
        print(f"validation failed ({len(all_errs)} issue(s)):", file=sys.stderr)
        for line in all_errs:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"OK: {len(notes)} notes in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
