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
        "meaning": ["vt. 造成；使承受"],
        "english_definition": "to make someone suffer harm, pain, or damage",
        "root": "in-（进入）+ flict（打击）",
        "example": "The storm inflicted serious damage on the town.",
        "collocations": ["inflict pain on", "inflict punishment on"],
        "audio_html": "",
        "learning_priority": "focus",
        "target_chunk": "inflict damage on",
        "target_chunk_meaning": "造成严重伤害",
        "target_chunk_cloze": "The storm ____ serious damage on the town.",
    }
    note.update(overrides)
    return note


class ValidatePhraseChunkTests(unittest.TestCase):
    def run_validator(self, note: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.json"
            path.write_text(json.dumps({"notes": [note]}, ensure_ascii=False), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                cwd=SKILL,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_valid_focus_phrase_chunk_note(self) -> None:
        result = self.run_validator(valid_note())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_accepts_valid_alias_only_phrase_chunk_note(self) -> None:
        note = valid_note(
            目标短语块="inflict damage on",
            短语块锚点="造成严重伤害",
            短语块挖空="The storm ____ serious damage on the town.",
        )
        del note["target_chunk"]
        del note["target_chunk_meaning"]
        del note["target_chunk_cloze"]

        result = self.run_validator(note)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_requires_target_chunk(self) -> None:
        result = self.run_validator(valid_note(target_chunk=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk must not be empty", result.stderr)

    def test_requires_target_chunk_meaning(self) -> None:
        result = self.run_validator(valid_note(target_chunk_meaning=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk_meaning must not be empty", result.stderr)

    def test_requires_focus_cloze(self) -> None:
        result = self.run_validator(valid_note(target_chunk_cloze=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("focus notes need target_chunk_cloze", result.stderr)

    def test_rejects_passive_cloze(self) -> None:
        result = self.run_validator(
            valid_note(learning_priority="passive", target_chunk_cloze="Fear can ____ judgment.")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("passive notes must leave target_chunk_cloze empty", result.stderr)

    def test_rejects_ignore_cloze(self) -> None:
        result = self.run_validator(
            valid_note(learning_priority="ignore", target_chunk_cloze="Fear can ____ judgment.")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("ignore notes must leave target_chunk_cloze empty", result.stderr)

    def test_rejects_cloze_without_blank(self) -> None:
        result = self.run_validator(valid_note(target_chunk_cloze="The storm inflicted damage."))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk_cloze must contain a blank", result.stderr)

    def test_rejects_short_bracket_blank_cloze(self) -> None:
        result = self.run_validator(valid_note(target_chunk_cloze="[blank] damage on town"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk_cloze must be a natural sentence", result.stderr)

    def test_rejects_word_level_chunk_meaning(self) -> None:
        result = self.run_validator(valid_note(target_chunk_meaning="vt. 造成；使承受"))
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "target_chunk_meaning should be a phrase-level Chinese anchor",
            result.stderr,
        )

    def test_rejects_long_chunk_meaning(self) -> None:
        result = self.run_validator(
            valid_note(target_chunk_meaning="这是一个明显超过二十四个汉字的中文短语块锚点内容用于测试")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "target_chunk_meaning should be a phrase-level Chinese anchor",
            result.stderr,
        )

    def test_rejects_non_string_phrase_chunk_fields(self) -> None:
        cases: list[tuple[str, object]] = [
            ("target_chunk", ["inflict damage on"]),
            ("target_chunk", {"chunk": "inflict damage on"}),
            ("target_chunk", 456),
            ("target_chunk_meaning", ["造成严重伤害"]),
            ("target_chunk_meaning", {"meaning": "造成严重伤害"}),
            ("target_chunk_meaning", 456),
            ("target_chunk_cloze", ["[blank] damage on town"]),
            ("target_chunk_cloze", {"cloze": "[blank] damage on town"}),
            ("target_chunk_cloze", 456),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=type(value).__name__):
                result = self.run_validator(valid_note(**{field: value}))
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"field {field!r} must be a string", result.stderr)

    def test_rejects_non_string_target_chunk_alias_even_with_valid_canonical(self) -> None:
        result = self.run_validator(valid_note(目标短语块=["inflict damage on"]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("field '目标短语块' must be a string", result.stderr)

    def test_rejects_non_string_target_chunk_meaning_alias_even_with_valid_canonical(self) -> None:
        result = self.run_validator(valid_note(短语块锚点={"meaning": "造成严重伤害"}))
        self.assertEqual(result.returncode, 1)
        self.assertIn("field '短语块锚点' must be a string", result.stderr)

    def test_rejects_non_string_target_chunk_cloze_alias_even_with_valid_canonical(self) -> None:
        result = self.run_validator(valid_note(短语块挖空=123))
        self.assertEqual(result.returncode, 1)
        self.assertIn("field '短语块挖空' must be a string", result.stderr)


if __name__ == "__main__":
    unittest.main()
