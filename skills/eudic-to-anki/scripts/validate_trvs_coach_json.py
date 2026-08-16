#!/usr/bin/env python3
"""Validate agent-authored Context Anchor JSON before Anki import."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from coach_fields import (
    LEARNING_GROUP_VALUES,
    SENTENCE_ORIGIN_VALUES,
    meaning_line_has_pos_prefix,
    normalize_word_key,
)

REPLACEMENT = "\ufffd"
MOJIBAKE_MARKERS = ("Ã", "Â", "Ð", "Ñ")
EN_WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
WORD_FAMILY_PLACEHOLDERS = {"-", "无", "不可拆分", "无构词线索", "无联想"}
WORD_FAMILY_POS_RE = re.compile(r"^(?:[A-Za-z]+\.)+\s+")
WORD_FAMILY_TARGET_RE = re.compile(r"^\s*[A-Za-z][A-Za-z' -]*「([^」]+)」")
WORD_FAMILY_TERM_RE = re.compile(r"([-A-Za-z/']+)「([^」]+)」")
SOURCE_CHUNK_DETERMINERS = {
    "a",
    "an",
    "the",
    "this",
    "that",
    "these",
    "those",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
}
IMPORTABLE_REQUIRED_KEYS = (
    "word",
    "pronunciation",
    "meaning",
    "english_definition",
    "card_sentence",
    "sentence_origin",
    "learning_group",
)
IRREGULAR_FORMS = {
    "be": {"am", "is", "are", "was", "were", "been", "being"},
    "go": {"goes", "went", "gone", "going"},
    "take": {"takes", "took", "taken", "taking"},
    "make": {"makes", "made", "making"},
    "come": {"comes", "came", "coming"},
    "see": {"sees", "saw", "seen", "seeing"},
    "get": {"gets", "got", "gotten", "getting"},
    "give": {"gives", "gave", "given", "giving"},
    "write": {"writes", "wrote", "written", "writing"},
    "read": {"reads", "reading"},
}


def _word_count(text: str) -> int:
    return len(EN_WORD_RE.findall(text))


def _target_pattern(word: str) -> re.Pattern[str] | None:
    normalized_word = normalize_word_key(word)
    if not normalized_word:
        return None
    if " " in normalized_word:
        return re.compile(
            rf"(?<![a-z]){re.escape(normalized_word)}(?![a-z])"
        )
    forms = {
        normalized_word,
        normalized_word + "s",
        normalized_word + "es",
        normalized_word + "ed",
        normalized_word + "ing",
        *IRREGULAR_FORMS.get(normalized_word, set()),
    }
    if normalized_word.endswith("e"):
        forms.update({normalized_word + "d", normalized_word[:-1] + "ing"})
    if normalized_word.endswith("y") and len(normalized_word) > 1:
        forms.update({normalized_word[:-1] + "ies", normalized_word[:-1] + "ied"})
    if (
        len(normalized_word) >= 3
        and normalized_word[-1] not in "aeiouwxy"
        and normalized_word[-2] in "aeiou"
        and normalized_word[-3] not in "aeiou"
    ):
        forms.update(
            {
                normalized_word + normalized_word[-1] + "ed",
                normalized_word + normalized_word[-1] + "ing",
            }
        )
    alternatives = "|".join(
        re.escape(form) for form in sorted(forms, key=len, reverse=True)
    )
    return re.compile(
        rf"(?<![a-z])(?:{alternatives})(?![a-z])"
    )


def _contains_target(sentence: str, word: str) -> bool:
    pattern = _target_pattern(word)
    return bool(pattern and pattern.search(normalize_word_key(sentence)))


def _source_chunk_adds_phrase_information(chunk: str, word: str) -> bool:
    pattern = _target_pattern(word)
    normalized_chunk = normalize_word_key(chunk)
    if not pattern or not pattern.search(normalized_chunk):
        return False
    remainder = pattern.sub(" ", normalized_chunk)
    extra_words = (token.casefold() for token in EN_WORD_RE.findall(remainder))
    return any(token not in SOURCE_CHUNK_DETERMINERS for token in extra_words)


def _text(note: dict[str, Any], key: str) -> str:
    value = note.get(key)
    return value.strip() if isinstance(value, str) else ""


def _split_word_family_associations(text: str) -> list[str]:
    associations: list[str] = []
    current: list[str] = []
    annotation_depth = 0
    for character in text:
        if character == "「":
            annotation_depth += 1
        elif character == "」" and annotation_depth:
            annotation_depth -= 1
        if character == "、" and annotation_depth == 0:
            associations.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    associations.append("".join(current).strip())
    return associations


def _annotation_has_pos_and_chinese_meaning(annotation: str) -> bool:
    has_pos = WORD_FAMILY_POS_RE.match(annotation) is not None
    return has_pos and CJK_RE.search(annotation) is not None


def _target_has_pos_and_chinese_meaning(text: str) -> bool:
    match = WORD_FAMILY_TARGET_RE.match(text)
    return bool(
        match and _annotation_has_pos_and_chinese_meaning(match.group(1).strip())
    )


def _association_has_pos_and_chinese_meaning(association: str) -> bool:
    word, opening, remainder = association.partition("「")
    if not word.strip() or not opening or not remainder.endswith("」"):
        return False
    return _annotation_has_pos_and_chinese_meaning(remainder[:-1].strip())


def _marked_root_or_affix_has_pos(text: str) -> bool:
    for term, annotation in WORD_FAMILY_TERM_RE.findall(text):
        is_marked_unit = term.startswith("-") or term.endswith("-") or "/" in term
        if is_marked_unit and WORD_FAMILY_POS_RE.match(annotation.strip()):
            return True
    return False


def _is_complete_importable_note(note: dict[str, Any]) -> bool:
    return all(note.get(key) not in (None, "", []) for key in IMPORTABLE_REQUIRED_KEYS)


def _validate_note(note: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    word = _text(note, "word")
    group_value = note.get("learning_group")
    if (
        not isinstance(group_value, str)
        or group_value.strip() not in LEARNING_GROUP_VALUES
    ):
        errors.append(
            f"note[{index}] word={word!r}: learning_group must be one of "
            f"{', '.join(LEARNING_GROUP_VALUES)}"
        )
        return errors
    group = group_value.strip()

    if group == "reject":
        if _is_complete_importable_note(note):
            errors.append(
                f"note[{index}] word={word!r}: reject is only for invalid fragments or garbage"
            )
        return errors

    for key in IMPORTABLE_REQUIRED_KEYS:
        if key not in note:
            errors.append(f"note[{index}] word={word!r}: missing key {key!r}")
    if not any(
        _text(note, key) for key in ("add_time_utc", "add_time_local", "encountered_at")
    ):
        errors.append(f"note[{index}] word={word!r}: encounter time is required")

    if not word:
        errors.append(f"note[{index}]: word must not be empty")
    elif len(word) == 1 and word.casefold() not in {"a", "i"}:
        errors.append(
            f"note[{index}] word={word!r}: invalid fragment should use learning_group reject"
        )

    for key in (
        "word",
        "pronunciation",
        "english_definition",
        "word_family",
        "source_context",
        "card_sentence",
        "sentence_origin",
        "source_chunk",
        "source_chunk_meaning",
        "audio_html",
    ):
        if key in note and not isinstance(note[key], str):
            errors.append(
                f"note[{index}] word={word!r}: field {key!r} must be a string"
            )
        value = note.get(key)
        if isinstance(value, str):
            if REPLACEMENT in value:
                errors.append(
                    f"note[{index}] word={word!r}: field {key!r} contains U+FFFD"
                )
            if any(marker in value for marker in MOJIBAKE_MARKERS):
                errors.append(
                    f"note[{index}] word={word!r}: field {key!r} contains mojibake"
                )

    pronunciation = _text(note, "pronunciation")
    if not pronunciation:
        errors.append(f"note[{index}] word={word!r}: pronunciation must not be empty")
    elif not (pronunciation.startswith("/") and pronunciation.endswith("/")):
        errors.append(
            f"note[{index}] word={word!r}: pronunciation must use /.../ IPA notation"
        )

    meanings = note.get("meaning")
    if not isinstance(meanings, list) or not meanings:
        errors.append(f"note[{index}] word={word!r}: meaning must be a non-empty array")
    elif any(not isinstance(item, str) or not item.strip() for item in meanings):
        errors.append(
            f"note[{index}] word={word!r}: meaning entries must be non-empty strings"
        )
    else:
        for item in meanings:
            if not meaning_line_has_pos_prefix(item):
                errors.append(
                    f"note[{index}] word={word!r}: meaning must start with a POS marker"
                )

    definition = _text(note, "english_definition")
    if not definition:
        errors.append(
            f"note[{index}] word={word!r}: english_definition must not be empty"
        )
    elif CJK_RE.search(definition):
        errors.append(
            f"note[{index}] word={word!r}: english_definition must be English"
        )
    elif not 6 <= _word_count(definition) <= 18:
        errors.append(
            f"note[{index}] word={word!r}: english_definition should contain 6-18 words"
        )

    word_family = _text(note, "word_family")
    if word_family in WORD_FAMILY_PLACEHOLDERS:
        errors.append(
            f"note[{index}] word={word!r}: "
            "omit word_family instead of using placeholder content"
        )
    elif word_family and HTML_TAG_RE.search(word_family):
        errors.append(
            f"note[{index}] word={word!r}: "
            "word_family must be plain text without HTML"
        )
    elif word_family:
        word_family_lines = [
            line.strip() for line in word_family.splitlines() if line.strip()
        ]
        if len(word_family_lines) != 2:
            errors.append(
                f"note[{index}] word={word!r}: "
                "word_family must contain exactly two non-empty lines"
            )
        elif not (
            word_family_lines[0].startswith("拆解：")
            and word_family_lines[1].startswith("联想：")
        ):
            errors.append(
                f"note[{index}] word={word!r}: "
                "word_family lines must start with 拆解： and 联想："
            )
        else:
            breakdown_text = word_family_lines[0].removeprefix("拆解：").strip()
            if not breakdown_text:
                errors.append(
                    f"note[{index}] word={word!r}: "
                    "word_family breakdown must not be empty"
                )
            association_text = word_family_lines[1].removeprefix("联想：").strip()
            if (
                breakdown_text in WORD_FAMILY_PLACEHOLDERS
                or association_text in WORD_FAMILY_PLACEHOLDERS
            ):
                errors.append(
                    f"note[{index}] word={word!r}: "
                    "omit word_family instead of using placeholder content"
                )
            else:
                _, arrow, target_text = breakdown_text.rpartition("→")
                if _marked_root_or_affix_has_pos(breakdown_text):
                    errors.append(
                        f"note[{index}] word={word!r}: word_family roots "
                        "and affixes must not include POS"
                    )
                if not arrow or not _target_has_pos_and_chinese_meaning(target_text):
                    errors.append(
                        f"note[{index}] word={word!r}: word_family target "
                        "must include POS and Chinese meaning"
                    )
                associations = _split_word_family_associations(association_text)
                if not 1 <= len(associations) <= 3 or not all(associations):
                    errors.append(
                        f"note[{index}] word={word!r}: "
                        "word_family must contain 1-3 associations separated by 、"
                    )
                elif not all(
                    _association_has_pos_and_chinese_meaning(item)
                    for item in associations
                ):
                    errors.append(
                        f"note[{index}] word={word!r}: each word_family "
                        "association must include POS and Chinese meaning"
                    )

    sentence = _text(note, "card_sentence")
    origin = _text(note, "sentence_origin")
    raw_source = _text(note, "source_context")
    if not sentence:
        errors.append(f"note[{index}] word={word!r}: card_sentence must not be empty")
    elif not _contains_target(sentence, word):
        errors.append(
            f"note[{index}] word={word!r}: card_sentence must contain the target word or a valid inflection"
        )
    if origin not in SENTENCE_ORIGIN_VALUES:
        errors.append(
            f"note[{index}] word={word!r}: sentence_origin must be one of "
            f"{', '.join(SENTENCE_ORIGIN_VALUES)}"
        )
    elif origin in {"source", "adapted"} and not raw_source:
        errors.append(
            f"note[{index}] word={word!r}: {origin} sentence needs source_context"
        )
    elif origin == "source" and normalize_word_key(sentence) != normalize_word_key(
        raw_source
    ):
        errors.append(
            f"note[{index}] word={word!r}: use adapted when card_sentence rewrites source_context"
        )
    elif origin == "generated":
        count = _word_count(sentence)
        if not 8 <= count <= 16:
            errors.append(
                f"note[{index}] word={word!r}: generated card_sentence should contain 8-16 words"
            )

    chunk = _text(note, "source_chunk")
    chunk_meaning = _text(note, "source_chunk_meaning")
    if bool(chunk) != bool(chunk_meaning):
        errors.append(
            f"note[{index}] word={word!r}: source_chunk and source_chunk_meaning must appear together"
        )
    if chunk and not _contains_target(chunk, word):
        errors.append(
            f"note[{index}] word={word!r}: source_chunk must contain the target word or a valid inflection"
        )
    elif chunk and not _source_chunk_adds_phrase_information(chunk, word):
        errors.append(
            f"note[{index}] word={word!r}: source_chunk must add phrase-level information beyond the target word"
        )
    if chunk and normalize_word_key(chunk) not in normalize_word_key(sentence):
        errors.append(
            f"note[{index}] word={word!r}: source_chunk must occur in card_sentence"
        )
    if (
        chunk
        and origin in {"source", "adapted"}
        and normalize_word_key(chunk) not in normalize_word_key(raw_source)
    ):
        errors.append(
            f"note[{index}] word={word!r}: source_chunk must be traceable to source_context"
        )
    if origin == "generated" and chunk:
        errors.append(
            f"note[{index}] word={word!r}: generated sentences cannot claim a source_chunk"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path)
    args = parser.parse_args()
    if not args.json_path.is_file():
        print(f"error: file not found: {args.json_path}", file=sys.stderr)
        return 2
    try:
        raw = args.json_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: invalid UTF-8 JSON: {exc}", file=sys.stderr)
        return 2
    if REPLACEMENT in raw:
        print("error: file contains U+FFFD", file=sys.stderr)
        return 2
    notes = data.get("notes") if isinstance(data, dict) else None
    if not isinstance(notes, list):
        print("error: top-level 'notes' must be an array", file=sys.stderr)
        return 2
    errors: list[str] = []
    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            errors.append(f"note[{index}] must be an object")
            continue
        errors.extend(_validate_note(note, index))
    if errors:
        print(f"validation failed ({len(errors)} issue(s)):", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"OK: {len(notes)} notes in {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
