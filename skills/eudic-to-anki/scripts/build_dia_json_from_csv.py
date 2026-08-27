#!/usr/bin/env python3
"""Build Context Anchor coaching placeholders from every Eudic CSV encounter."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path

IPA_FALLBACK: dict[str, str] = {
    "ratio": "/ˈɹeɪʃioʊ/",
    "jackpot": "/ˈdʒækpɑt/",
    "chevron": "/ˈʃɛvɹən/",
    "jovial": "/ˈdʒoʊviəl/",
    "shredded": "/ˈʃrɛdɪd/",
}


def wrap_ipa(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    return (
        text if text.startswith("/") and text.endswith("/") else f"/{text.strip('/')}/"
    )


def _looks_like_bad_phon(value: str) -> bool:
    return (
        not value
        or "`" in value
        or "·" in value
        or bool(re.search(r"\bRa\b|\bJack\b|\bChe\b|\bunz\.", value, re.I))
        or "ε" in value
        or bool(re.match(r"^[A-Za-z][A-Za-z·\s]+$", value))
    )


def clean_eudic_phon(raw: str, word: str = "") -> str:
    """Clean Eudic phon only for the explicit optional IPA-prefill mode."""
    text = re.sub(r"<[^>]+>", "", str(raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return IPA_FALLBACK.get(word, "")
    chunks = re.findall(r"/\s*[^/]+\s*/", text)
    inner = (chunks[0] if chunks else text).strip().strip("/")
    inner = inner.replace("'", "ˈ").replace("‘", "ˈ").replace("’", "ˈ")
    inner = re.sub(r"\[[^\]]*\]", "", inner)
    inner = re.sub(r"\s+", " ", inner.replace("·", "").replace("`", "")).strip()
    if _looks_like_bad_phon(inner):
        return IPA_FALLBACK.get(word, "")
    return wrap_ipa(inner)


def clean_context_line(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", str(raw or ""), flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def eudic_source_from_row(row: dict[str, str]) -> dict[str, str] | None:
    """Keep deletion identity separate from the normalized/coached Anki word."""
    if not row.get("language") or not row.get("category_id") or not row.get("word"):
        return None
    return {key: row[key] for key in ("language", "category_id", "word")}


def placeholder_from_row(
    row: dict[str, str], *, source: str, prefill_eudic_phon: bool
) -> dict[str, object] | None:
    word = str(row.get("word") or "").strip()
    if not word:
        return None
    pronunciation = ""
    if prefill_eudic_phon:
        pronunciation = clean_eudic_phon(str(row.get("phon") or ""), word=word)
    return {
        "word": word,
        "pronunciation": pronunciation,
        "part_of_speech": "",
        "meaning": [],
        "english_definition": "",
        "word_family": "",
        "source_context": clean_context_line(row.get("context_line") or ""),
        "card_sentence": "",
        "sentence_origin": "",
        "source_chunk": "",
        "source_chunk_meaning": "",
        "learning_group": "",
        "audio_html": "",
        "source": source,
        "eudic_source": eudic_source_from_row(row),
        "category_id": str(row.get("category_id") or ""),
        "category_name": str(row.get("category_name") or ""),
        "add_time_utc": str(row.get("add_time_utc") or ""),
        "add_time_local": str(row.get("add_time_local") or ""),
        "tags": [],
    }


def patch_pronunciations(csv_path: Path, json_path: Path) -> int:
    first: dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            word = str(row.get("word") or "").strip()
            if word and word not in first:
                first[word] = clean_eudic_phon(str(row.get("phon") or ""), word=word)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    changed = 0
    for note in data.get("notes", []):
        pronunciation = first.get(str(note.get("word") or "").strip(), "")
        if pronunciation:
            note["pronunciation"] = pronunciation
            changed += 1
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", default="eudic cloud")
    parser.add_argument("--batch-date", default="", help=argparse.SUPPRESS)
    parser.add_argument(
        "--eudic-words-only",
        action="store_true",
        help="Compatibility flag; every row is always an agent placeholder.",
    )
    parser.add_argument(
        "--eudic-phon-for-ipa",
        action="store_true",
        help="Optionally prefill IPA from Eudic phon instead of agent authoring.",
    )
    parser.add_argument("--patch-pronunciations-in-json", type=Path)
    args = parser.parse_args()

    if args.patch_pronunciations_in_json:
        changed = patch_pronunciations(args.csv, args.patch_pronunciations_in_json)
        print(
            f"Updated pronunciation for {changed} notes in "
            f"{args.patch_pronunciations_in_json}"
        )
        return 0
    if args.output is None:
        raise SystemExit("--output is required unless patching pronunciations")

    notes: list[dict[str, object]] = []
    with args.csv.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            note = placeholder_from_row(
                row,
                source=args.source,
                prefill_eudic_phon=args.eudic_phon_for_ipa,
            )
            if note is not None:
                notes.append(note)
    args.output.write_text(
        json.dumps({"notes": notes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(notes)} encounter placeholders to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
