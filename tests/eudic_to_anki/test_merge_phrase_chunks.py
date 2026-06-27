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


class MergePhraseChunkTests(unittest.TestCase):
    def test_merge_coach_with_partial_preserves_phrase_chunk_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            partial = tmp_path / "partial.json"
            coach = tmp_path / "coach.json"
            output = tmp_path / "import.json"
            partial.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "word": "inflict",
                                "source": "eudic cloud",
                                "source_context": "The storm inflicted serious damage on the town.",
                                "tags": ["sample"],
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
                            {
                                "word": "inflict",
                                "pronunciation": "/ɪnˈflɪkt/",
                                "part_of_speech": "vt.",
                                "meaning": ["vt. 造成；使承受"],
                                "english_definition": "to make someone suffer harm or damage",
                                "root": "in-（进入）+ flict（打击）",
                                "example": "The storm inflicted serious damage on the town.",
                                "collocations": ["inflict pain on", "inflict punishment on"],
                                "audio_html": "",
                                "learning_priority": "focus",
                                "target_chunk": "inflict damage on",
                                "target_chunk_meaning": "造成严重伤害",
                                "target_chunk_sentence": "The storm can inflict damage on a town.",
                                "target_chunk_cloze": "The storm can ____ a town.",
                            }
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
            self.assertEqual(note["target_chunk"], "inflict damage on")
            self.assertEqual(note["target_chunk_meaning"], "造成严重伤害")
            self.assertEqual(
                note["target_chunk_sentence"],
                "The storm can inflict damage on a town.",
            )
            self.assertEqual(
                note["target_chunk_cloze"],
                "The storm can ____ a town.",
            )

    def test_merge_coach_with_partial_falls_back_to_alias_for_blank_chunk_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            partial = tmp_path / "partial.json"
            coach = tmp_path / "coach.json"
            output = tmp_path / "import.json"
            partial.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "word": "anchor",
                                "source": "eudic cloud",
                                "source_context": "The remark anchored the whole discussion.",
                                "tags": ["sample"],
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
                            {
                                "word": "anchor",
                                "pronunciation": "/ˈæŋkər/",
                                "part_of_speech": "vt.",
                                "meaning": ["vt. 固定；使有根据"],
                                "english_definition": "to make something firmly based on something else",
                                "root": "anchor（锚）",
                                "example": "The remark anchored the whole discussion.",
                                "collocations": ["anchor the discussion"],
                                "audio_html": "",
                                "learning_priority": "focus",
                                "target_chunk": "   ",
                                "目标短语块": "anchor the discussion",
                                "target_chunk_meaning": "   ",
                                "短语块锚点": "固定讨论重点",
                                "target_chunk_sentence": "   ",
                                "短语块例句": "The remark helped anchor the discussion.",
                                "target_chunk_cloze": "   ",
                                "短语块挖空": "The remark helped ____.",
                            }
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
            self.assertEqual(note["target_chunk"], "anchor the discussion")
            self.assertEqual(note["target_chunk_meaning"], "固定讨论重点")
            self.assertEqual(
                note["target_chunk_sentence"],
                "The remark helped anchor the discussion.",
            )
            self.assertEqual(
                note["target_chunk_cloze"],
                "The remark helped ____.",
            )

    def test_merge_minimal_week_import_preserves_phrase_chunk_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "export.csv"
            coach = tmp_path / "minimal.json"
            output = tmp_path / "week.json"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["word", "phon", "context_line"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "word": "distort",
                        "phon": "/dɪˈstɔrt/",
                        "context_line": "Fear can distort your judgment.",
                    }
                )
            coach.write_text(
                json.dumps(
                    {
                        "distort": {
                            "part_of_speech": "vt.",
                            "meaning": ["vt. 扭曲；曲解"],
                            "english_definition": "to change something so it is no longer accurate",
                            "root": "dis-（分开）+ tort（扭）",
                            "example": "Fear can distort your judgment.",
                            "collocations": ["distort the truth", "distort your judgment"],
                            "learning_priority": "focus",
                            "target_chunk": "distort your judgment",
                            "target_chunk_meaning": "扭曲判断",
                            "target_chunk_sentence": "Fear can distort your judgment.",
                            "target_chunk_cloze": "Fear can ____ your judgment.",
                        }
                    }
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
            self.assertEqual(note["target_chunk"], "distort your judgment")
            self.assertEqual(note["target_chunk_meaning"], "扭曲判断")
            self.assertEqual(note["target_chunk_sentence"], "Fear can distort your judgment.")
            self.assertEqual(note["target_chunk_cloze"], "Fear can ____ your judgment.")


if __name__ == "__main__":
    unittest.main()
