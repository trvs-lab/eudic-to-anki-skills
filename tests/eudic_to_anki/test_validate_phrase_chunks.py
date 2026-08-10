from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "eudic-to-anki"
VALIDATOR = SKILL / "scripts" / "validate_trvs_coach_json.py"


def valid_note(**overrides: object) -> dict[str, object]:
    note: dict[str, object] = {
        "word": "inflict",
        "pronunciation": "/ɪnˈflɪkt/",
        "part_of_speech": "vt.",
        "meaning": ["vt. 使遭受；造成"],
        "english_definition": "to make someone suffer something unpleasant",
        "word_family": "in-（向内）+ flict（打击）",
        "source_context": "The storm inflicted serious damage on the town.",
        "card_sentence": "The storm inflicted serious damage on the town.",
        "sentence_origin": "source",
        "source_chunk": "inflicted serious damage on",
        "source_chunk_meaning": "给……造成严重破坏",
        "learning_group": "learn",
        "category_id": "book-1",
        "add_time_utc": "2026-08-10T01:00:00Z",
        "audio_html": "",
    }
    note.update(overrides)
    return note


class ValidateContextAnchorTests(unittest.TestCase):
    def run_validator(
        self, note: dict[str, object]
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.json"
            path.write_text(
                json.dumps({"notes": [note]}, ensure_ascii=False), encoding="utf-8"
            )
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                cwd=SKILL,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_source_adapted_and_generated_sentences(self) -> None:
        cases = [
            valid_note(),
            valid_note(
                card_sentence="The storm inflicted serious damage.",
                sentence_origin="adapted",
                source_chunk="inflicted serious damage",
            ),
            valid_note(
                source_context="",
                card_sentence="Criticism can inflict lasting harm on a young child.",
                sentence_origin="generated",
                source_chunk="",
                source_chunk_meaning="",
            ),
        ]
        for case in cases:
            with self.subTest(origin=case["sentence_origin"]):
                result = self.run_validator(case)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_requires_generated_sentence_when_source_is_missing(self) -> None:
        result = self.run_validator(
            valid_note(source_context="", card_sentence="", sentence_origin="generated")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("card_sentence must not be empty", result.stderr)

    def test_generated_sentence_must_contain_target_word(self) -> None:
        result = self.run_validator(
            valid_note(
                source_context="",
                card_sentence="Criticism can cause lasting harm to a child.",
                sentence_origin="generated",
                source_chunk="",
                source_chunk_meaning="",
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("card_sentence must contain the target word", result.stderr)

    def test_generated_sentence_has_practical_default_length(self) -> None:
        too_short = self.run_validator(
            valid_note(
                source_context="",
                card_sentence="They inflict harm.",
                sentence_origin="generated",
                source_chunk="",
                source_chunk_meaning="",
            )
        )
        self.assertEqual(too_short.returncode, 1)
        self.assertIn(
            "generated card_sentence should contain 8-16 words", too_short.stderr
        )

    def test_english_definition_uses_compact_six_to_eighteen_word_range(self) -> None:
        too_short = self.run_validator(
            valid_note(english_definition="to cause serious lasting harm")
        )
        self.assertEqual(too_short.returncode, 1)
        self.assertIn("should contain 6-18 words", too_short.stderr)

    def test_source_chunk_is_optional_but_must_be_traceable(self) -> None:
        omitted = self.run_validator(
            valid_note(source_chunk="", source_chunk_meaning="")
        )
        self.assertEqual(omitted.returncode, 0, omitted.stderr)

        invalid = self.run_validator(valid_note(source_chunk="inflict pain on"))
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("source_chunk must occur in card_sentence", invalid.stderr)

    def test_rewritten_source_must_be_marked_adapted(self) -> None:
        result = self.run_validator(
            valid_note(
                card_sentence="The storm inflicted serious damage.",
                sentence_origin="source",
                source_chunk="inflicted serious damage",
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "use adapted when card_sentence rewrites source_context", result.stderr
        )

    def test_requires_stable_encounter_identity(self) -> None:
        result = self.run_validator(valid_note(add_time_utc=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("encounter time is required", result.stderr)

    def test_reject_group_is_reserved_for_invalid_fragments(self) -> None:
        complete = self.run_validator(valid_note(learning_group="reject"))
        self.assertEqual(complete.returncode, 1)
        self.assertIn("reject is only for invalid fragments", complete.stderr)

        fragment = self.run_validator(
            valid_note(
                word="x",
                pronunciation="",
                meaning=[],
                english_definition="",
                word_family="",
                source_context="",
                card_sentence="",
                sentence_origin="",
                source_chunk="",
                source_chunk_meaning="",
                learning_group="reject",
            )
        )
        self.assertEqual(fragment.returncode, 0, fragment.stderr)

    def test_skip_accepts_complete_words_and_phrases(self) -> None:
        cases = (
            ("sphinx", "The stone sphinx guarded the entrance to the old temple."),
            ("by and large", "By and large, the new process works as expected."),
        )
        for word, sentence in cases:
            result = self.run_validator(
                valid_note(
                    word=word,
                    learning_group="skip",
                    source_context=sentence,
                    card_sentence=sentence,
                    source_chunk="",
                    source_chunk_meaning="",
                )
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
