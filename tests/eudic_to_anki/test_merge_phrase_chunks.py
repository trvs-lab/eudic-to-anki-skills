from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "eudic-to-anki"


def coach_note(word: str = "inflict", **overrides: object) -> dict[str, object]:
    note: dict[str, object] = {
        "word": word,
        "pronunciation": "/ɪnˈflɪkt/",
        "part_of_speech": "vt.",
        "meaning": ["vt. 使遭受；造成"],
        "english_definition": "to make someone suffer something unpleasant",
        "word_family": "in-（向内）+ flict（打击）",
        "card_sentence": "The storm inflicted serious damage on the town.",
        "sentence_origin": "source",
        "source_chunk": "inflicted serious damage on",
        "source_chunk_meaning": "给……造成严重破坏",
        "learning_group": "learn",
        "audio_html": "",
    }
    note.update(overrides)
    return note


class MergeContextAnchorTests(unittest.TestCase):
    def test_merge_preserves_each_eudic_encounter_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            partial = root / "partial.json"
            coach = root / "coach.json"
            output = root / "import.json"
            partial.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "word": "Inflict",
                                "source": "eudic cloud",
                                "source_context": "The storm inflicted serious damage on the town.",
                                "category_id": "book-a",
                                "category_name": "Novel A",
                                "add_time_utc": "2026-08-10T01:00:00Z",
                                "add_time_local": "2026-08-10 09:00:00",
                                "tags": ["reading"],
                            },
                            {
                                "word": "inflict",
                                "source": "eudic cloud",
                                "source_context": "The policy inflicted costs on small firms.",
                                "category_id": "book-b",
                                "category_name": "Book B",
                                "add_time_utc": "2026-08-11T01:00:00Z",
                                "add_time_local": "2026-08-11 09:00:00",
                                "tags": ["reading"],
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            coach.write_text(
                json.dumps({"notes": [coach_note()]}, ensure_ascii=False),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "merge_coach_with_partial.py"),
                    "--partial",
                    str(partial),
                    "--coach",
                    str(coach),
                    "-o",
                    str(output),
                ],
                cwd=SKILL,
                check=True,
            )
            notes = json.loads(output.read_text(encoding="utf-8"))["notes"]
            self.assertEqual(len(notes), 2)
            self.assertEqual(notes[0]["category_id"], "book-a")
            self.assertEqual(notes[1]["add_time_utc"], "2026-08-11T01:00:00Z")
            self.assertEqual(
                notes[1]["source_context"],
                "The policy inflicted costs on small firms.",
            )
            self.assertEqual(notes[0]["card_sentence"], coach_note()["card_sentence"])
            self.assertEqual(notes[0]["sentence_origin"], "source")
            self.assertNotIn("target_chunk_cloze", notes[0])

    def test_merge_keeps_generated_sentence_when_source_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            partial = root / "partial.json"
            coach = root / "coach.json"
            output = root / "import.json"
            partial.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "word": "inflict",
                                "source_context": "",
                                "category_id": "book-a",
                                "add_time_utc": "2026-08-10T01:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            coach.write_text(
                json.dumps(
                    {
                        "notes": [
                            coach_note(
                                card_sentence="Criticism can inflict lasting harm on a young child.",
                                sentence_origin="generated",
                                source_chunk="",
                                source_chunk_meaning="",
                            )
                        ]
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "merge_coach_with_partial.py"),
                    "--partial",
                    str(partial),
                    "--coach",
                    str(coach),
                    "-o",
                    str(output),
                ],
                cwd=SKILL,
                check=True,
            )
            note = json.loads(output.read_text(encoding="utf-8"))["notes"][0]
            self.assertEqual(note["source_context"], "")
            self.assertEqual(note["sentence_origin"], "generated")

    def test_minimal_week_merge_preserves_context_anchor_and_csv_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "export.csv"
            coach = root / "coach.json"
            output = root / "week.json"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "word",
                        "phon",
                        "context_line",
                        "category_id",
                        "category_name",
                        "add_time_utc",
                        "add_time_local",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "word": "distort",
                        "phon": "/dɪˈstɔrt/",
                        "context_line": "Fear can distort your judgment.",
                        "category_id": "book-a",
                        "category_name": "Novel A",
                        "add_time_utc": "2026-08-10T01:00:00Z",
                        "add_time_local": "2026-08-10 09:00:00",
                    }
                )
            coach.write_text(
                json.dumps(
                    {
                        "distort": {
                            "part_of_speech": "vt.",
                            "meaning": ["vt. 扭曲；曲解"],
                            "english_definition": "to change something so it is no longer accurate",
                            "word_family": "dis-（分开）+ tort（扭）",
                            "card_sentence": "Fear can distort your judgment.",
                            "sentence_origin": "source",
                            "source_chunk": "distort your judgment",
                            "source_chunk_meaning": "扭曲判断",
                            "learning_group": "learn",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "merge_minimal_week_import.py"),
                    "--csv",
                    str(csv_path),
                    "--coach-json",
                    str(coach),
                    "--output",
                    str(output),
                ],
                cwd=SKILL,
                check=True,
            )
            note = json.loads(output.read_text(encoding="utf-8"))["notes"][0]
            self.assertEqual(note["source_chunk"], "distort your judgment")
            self.assertEqual(note["category_name"], "Novel A")
            self.assertEqual(note["add_time_utc"], "2026-08-10T01:00:00Z")


if __name__ == "__main__":
    unittest.main()
