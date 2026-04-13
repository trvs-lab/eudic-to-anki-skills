#!/usr/bin/env python3
"""Build TRVS-Lab-ready coach JSON from Eudic CSV: word list + metadata (tags, source).

All eight coach fields—including **`pronunciation`**—are written by the **executing agent** per
`word-coach-json-prompt.md` (`eudic-to-anki` skill default: **no** Eudic `phon` prefill
or pronunciation patch). This script emits placeholders only, plus optional `--eudic-phon-for-ipa`
/ `--patch-pronunciations-in-json` for **optional manual** use, and built-in COACH rows for a few
demo lemmas used in tests.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from coach_fields import fuse_pos_into_meaning


def wrap_ipa(phon: str) -> str:
    p = (phon or "").strip()
    if not p:
        return ""
    if p.startswith("/") and p.endswith("/"):
        return p
    return f"/{p.strip('/')}/"


_IPA_FALLBACK: dict[str, str] = {
    "ratio": "/\u02c8\u0279e\u026a\u0283io\u028a/",
    "jackpot": "/\u02c8d\u0292\u00e6kp\u0251t/",
    "chevron": "/\u02c8\u0283\u025bv\u0279\u0259n/",
    "jovial": "/\u02c8d\u0292o\u028avi\u0259l/",
    # Eudic often leaves `phon` empty; common learner errors from guessed IPA:
    "shredded": "/\u02c8\u0283r\u025bd\u026ad/",
}


def _ipa_fallback(word: str) -> str:
    w = (word or "").strip()
    return _IPA_FALLBACK.get(w, "")


def _looks_like_bad_phon(s: str) -> bool:
    if not s:
        return True
    if "`" in s or "\u00b7" in s:
        return True
    if re.search(r"\bRa\b|\bJack\b|\bChe\b|\bunz\.", s, re.I):
        return True
    if "\u03b5" in s:
        return True
    if re.match(r"^[A-Za-z][A-Za-z\u00b7\s]+$", s):
        return True
    return False


def clean_eudic_phon(raw: str, word: str = "") -> str:
    """Strip HTML from Eudic `phon` cell; normalize stress apostrophe to IPA ˈ; return IPA with slashes."""
    t = re.sub(r"<[^>]+>", "", str(raw or ""))
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return _ipa_fallback(word)

    slash_chunks = re.findall(r"/\s*[^/]+\s*/", t)
    if slash_chunks:
        inner = slash_chunks[0].strip().strip("/")
    else:
        inner = t.strip().strip("/")

    inner = inner.replace("'", "ˈ")
    inner = inner.replace("‘", "ˈ").replace("’", "ˈ")
    inner = re.sub(r"\[[^\]]*\]", "", inner)
    inner = inner.replace("·", "").replace("`", "").strip()
    inner = re.sub(r"\s+", " ", inner).strip()

    if not inner or _looks_like_bad_phon(inner):
        return _ipa_fallback(word)

    return wrap_ipa(inner)


def note_words_only(
    word: str,
    *,
    source: str,
    tags: list[str],
    pronunciation: str = "",
) -> dict[str, object]:
    """Placeholder note: only `word` is authoritative; coach/LLM fills the rest."""
    return {
        "word": word,
        "pronunciation": pronunciation,
        "meaning": [],
        "english_definition": "",
        "root": "",
        "example": "",
        "collocations": [],
        "audio_html": "",
        "source": source,
        "tags": tags,
    }


def note_from_csv_row_with_coach(
    row: dict[str, str],
    *,
    base: dict[str, object],
    source: str,
    tags: list[str],
) -> dict[str, object]:
    """Rare: built-in COACH lemmas for local tests; not used for normal Eudic exports."""
    w = (row.get("word") or "").strip()
    raw_meaning = base.get("meaning") or []
    if not isinstance(raw_meaning, list):
        meaning_list = [str(raw_meaning).strip()] if str(raw_meaning).strip() else []
    else:
        meaning_list = [str(x).strip() for x in raw_meaning if str(x).strip()]
    pos = str(base.get("part_of_speech") or "")
    meaning = fuse_pos_into_meaning(meaning_list, pos)
    endef = str(base["english_definition"])
    root = str(base["root"])
    example = str(base["example"])
    collocations = base["collocations"]
    if not isinstance(collocations, list):
        collocations = list(collocations) if collocations else []
    return {
        "word": w,
        "pronunciation": clean_eudic_phon(str(row.get("phon") or ""), word=w),
        "meaning": meaning,
        "english_definition": endef,
        "root": root,
        "example": example,
        "collocations": collocations,
        "audio_html": "",
        "source": source,
        "tags": tags,
    }


COACH: dict[str, dict[str, object]] = {
    "semantic": {
        "meaning": ["adj. 语义的", "adj. 与词义、含义相关的"],
        "english_definition": (
            "relating to meaning in language, especially the meaning of "
            "individual words and how they combine"
        ),
        "root": "希腊语 sēmantikos（有意义的）",
        "example": (
            'In that sentence, "bank" has a different semantic role than in '
            '"river bank."'
        ),
        "collocations": ["semantic field", "semantic ambiguity", "semantic shift"],
    },
    "clutter": {
        "meaning": ["n. 杂乱；一堆杂物", "vt. 使凌乱；乱堆乱放"],
        "english_definition": (
            "a messy collection of things; to fill a space in an untidy way"
        ),
        "root": "-",
        "example": "She cleared the clutter off the kitchen counter before guests arrived.",
        "collocations": ["clutter up", "mental clutter", "cluttered desk"],
    },
    "maturity": {
        "meaning": ["n. 成熟；发育完全", "n. （票据、贷款等）到期"],
        "english_definition": (
            "the state of being fully grown or developed; the time when a "
            "financial obligation becomes due"
        ),
        "root": "matur-（成熟）+ -ity（名词后缀）",
        "example": "He handled the crisis with a maturity beyond his years.",
        "collocations": ["reach maturity", "emotional maturity", "maturity date"],
    },
    "intentional": {
        "meaning": ["adj. 故意的", "adj. 有意的；蓄意的"],
        "english_definition": "done on purpose; planned rather than accidental",
        "root": "intention（意图）+ -al（形容词后缀）",
        "example": (
            "Leaving the form blank was an intentional choice, not an oversight."
        ),
        "collocations": ["intentional act", "intentional harm", "purely intentional"],
    },
    "aesthetics": {
        "meaning": ["n. 美学；审美学", "n. （产品、界面的）美感、视觉效果"],
        "english_definition": (
            "the branch of philosophy dealing with beauty and taste; the visual "
            "or stylistic qualities of something"
        ),
        "root": "希腊语 aisthētikos（与感知相关的）",
        "example": "The app's clean aesthetics made it pleasant to use every day.",
        "collocations": [
            "visual aesthetics",
            "minimalist aesthetics",
            "aesthetics of design",
        ],
    },
    "pinprick": {
        "meaning": ["n. 针扎的小孔；针眼大小的洞", "n. 小烦恼；微不足道的刺激"],
        "english_definition": (
            "a tiny hole made by a pin, or a small irritation or annoyance"
        ),
        "root": "pin（针）+ prick（刺、扎）",
        "example": (
            "Compared with the main outage, the five-minute delay felt like a pinprick."
        ),
        "collocations": [
            "a pinprick of light",
            "a pinprick of doubt",
            "pinprick holes",
        ],
    },
    "beady-eyed": {
        "meaning": ["adj. 目光锐利的；紧盯不放的", "adj. （常形容眼睛）小而亮、显得警觉"],
        "english_definition": (
            "having small, bright eyes and looking alert, watchful, or suspicious"
        ),
        "root": "beady（珠子般小而亮）+ -eyed（带…眼睛的）",
        "example": "The beady-eyed supervisor noticed every typo in the report.",
        "collocations": [
            "beady-eyed stare",
            "beady-eyed scrutiny",
            "beady-eyed look",
        ],
    },
    "beady": {
        "meaning": ["adj. （眼睛）小而圆亮的", "adj. 警觉的、紧盯的（常作 beady eyes）"],
        "english_definition": (
            "small, round, and shiny like beads—often used to describe eyes"
        ),
        "root": "bead（珠子）+ -y（形容词后缀）",
        "example": "The cat gave me a beady stare from the windowsill.",
        "collocations": ["beady eyes", "beady stare", "beady look"],
    },
    "flicker": {
        "meaning": ["v. 闪烁；忽明忽暗", "n. （情感、希望等）一闪而过"],
        "english_definition": "to shine unsteadily; a brief, weak light or feeling",
        "root": "-",
        "example": (
            "The lights flickered during the storm, then went out completely."
        ),
        "collocations": [
            "flicker on and off",
            "a flicker of hope",
            "screen flicker",
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination JSON (not required when using --patch-pronunciations-in-json only).",
    )
    parser.add_argument("--source", default="eudic cloud")
    parser.add_argument(
        "--batch-date",
        default="",
        help="If set, appended to tags (e.g. 2026-04-09).",
    )
    parser.add_argument(
        "--eudic-words-only",
        action="store_true",
        help=(
            "Ignore built-in COACH demo rows: every note is a placeholder for the agent. "
            "Default behavior already uses word-only placeholders for normal rows (IPA filled by "
            "the agent unless --eudic-phon-for-ipa is passed); this flag forces the same even if "
            "the word matches a COACH key."
        ),
    )
    parser.add_argument(
        "--eudic-phon-for-ipa",
        action="store_true",
        help=(
            "Optional (off skill default): prefill `pronunciation` from CSV `phon` only (HTML "
            "stripped; ' -> ˈ). The eudic-to-anki skill expects the agent to write IPA "
            "instead. Ignores `exp`."
        ),
    )
    parser.add_argument(
        "--patch-pronunciations-in-json",
        type=Path,
        default=None,
        help=(
            "Optional (off skill default): with --csv, load this notes JSON and overwrite each "
            "note's pronunciation when the CSV has non-empty `phon` (first row wins). Writes in "
            "place."
        ),
    )
    args = parser.parse_args()

    if args.patch_pronunciations_in_json:
        if not args.csv.exists():
            raise SystemExit(f"CSV not found: {args.csv}")
        if not args.patch_pronunciations_in_json.exists():
            raise SystemExit(f"JSON not found: {args.patch_pronunciations_in_json}")
        phon_first: dict[str, str] = {}
        with args.csv.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                w = (row.get("word") or "").strip()
                if not w or w in phon_first:
                    continue
                phon_first[w] = clean_eudic_phon(str(row.get("phon") or ""), word=w)
        data = json.loads(
            args.patch_pronunciations_in_json.read_text(encoding="utf-8")
        )
        changed = 0
        for note in data.get("notes", []):
            w = str(note.get("word") or "").strip()
            ipa = phon_first.get(w, "")
            if ipa:
                note["pronunciation"] = ipa
                changed += 1
        args.patch_pronunciations_in_json.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Updated pronunciation for {changed} notes in {args.patch_pronunciations_in_json}")
        return 0

    if not args.output:
        raise SystemExit("--output is required unless using --patch-pronunciations-in-json.")

    notes: list[dict[str, object]] = []
    seen: set[str] = set()
    with args.csv.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            w = (row.get("word") or "").strip()
            if not w or w in seen:
                continue
            seen.add(w)
            tags = ["english", "vocab", "eudic"]
            if args.batch_date:
                tags.append(args.batch_date)
            base = None if args.eudic_words_only else COACH.get(w)
            if base:
                notes.append(
                    note_from_csv_row_with_coach(
                        row, base=base, source=args.source, tags=tags
                    )
                )
            else:
                pron = ""
                if args.eudic_phon_for_ipa:
                    pron = clean_eudic_phon(str(row.get("phon") or ""), word=w)
                notes.append(
                    note_words_only(
                        w, source=args.source, tags=tags, pronunciation=pron
                    )
                )

    args.output.write_text(
        json.dumps({"notes": notes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(notes)} notes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
