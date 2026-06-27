from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import",
    SCRIPTS / "ankiconnect_import.py",
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class AnkiconnectPhraseFieldTests(unittest.TestCase):
    def test_build_trvs_lab_fields_maps_phrase_chunk_fields(self) -> None:
        fields = ankiconnect_import.build_trvs_lab_fields(
            {
                "word": "inflict",
                "pronunciation": "/ɪnˈflɪkt/",
                "part_of_speech": "vt.",
                "meaning": ["造成；使承受"],
                "english_definition": "to make someone suffer harm, pain, or damage",
                "root": "in-（进入）+ flict（打击）",
                "example": "The storm inflicted serious damage on the town.",
                "collocations": ["inflict pain on", "inflict punishment on"],
                "target_chunk": "inflict damage on",
                "target_chunk_meaning": "造成严重伤害",
                "target_chunk_sentence": "The storm can inflict damage on a town.",
                "target_chunk_cloze": "The storm can ____ a town.",
                "learning_priority": "focus",
            },
            "[sound:inflict.mp3]",
        )
        self.assertEqual(fields["目标短语块"], "inflict damage on")
        self.assertEqual(fields["短语块锚点"], "造成严重伤害")
        self.assertEqual(fields["短语块例句"], "The storm can inflict damage on a town.")
        self.assertEqual(fields["短语块挖空"], "The storm can ____ a town.")
        self.assertEqual(fields["发音"], "[sound:inflict.mp3]")

    def test_build_trvs_lab_fields_maps_chinese_phrase_chunk_aliases(self) -> None:
        fields = ankiconnect_import.build_trvs_lab_fields(
            {
                "单词": "inflict",
                "音标": "/ɪnˈflɪkt/",
                "词性": "vt.",
                "释义": ["造成；使承受"],
                "英英": "to make someone suffer harm, pain, or damage",
                "词根": "in-（进入）+ flict（打击）",
                "例句": "The storm inflicted serious damage on the town.",
                "常用搭配": ["inflict pain on", "inflict punishment on"],
                "目标短语块": "inflict damage on",
                "短语块锚点": "造成严重伤害",
                "短语块例句": "The storm can inflict damage on a town.",
                "短语块挖空": "The storm can ____ a town.",
                "learning_priority": "focus",
            },
            "",
        )
        self.assertEqual(fields["目标短语块"], "inflict damage on")
        self.assertEqual(fields["短语块锚点"], "造成严重伤害")
        self.assertEqual(fields["短语块例句"], "The storm can inflict damage on a town.")
        self.assertEqual(fields["短语块挖空"], "The storm can ____ a town.")

    def test_required_payload_fields_include_phrase_anchor_fields(self) -> None:
        fields = {
            "单词": "inflict",
            "音标": "/ɪnˈflɪkt/",
            "释义": "vt. 造成；使承受",
            "英英": "to make someone suffer harm, pain, or damage",
            "词根": "in-（进入）+ flict（打击）",
            "例句": "The storm inflicted serious damage on the town.",
            "常用搭配": "inflict pain on<br>inflict punishment on",
            "目标短语块": "",
            "短语块锚点": "造成严重伤害",
            "短语块例句": "",
            "短语块挖空": "The storm can ____ a town.",
            "学习标记": "★",
        }
        missing = ankiconnect_import._missing_required_field_names(
            fields,
            require_audio=False,
        )
        self.assertIn("目标短语块", missing)
        self.assertIn("短语块例句", missing)

    def test_required_payload_fields_allow_empty_source_example(self) -> None:
        fields = {
            "单词": "inflict",
            "音标": "/ɪnˈflɪkt/",
            "释义": "vt. 造成；使承受",
            "英英": "to make someone suffer harm, pain, or damage",
            "词根": "in-（进入）+ flict（打击）",
            "例句": "",
            "常用搭配": "inflict pain on<br>inflict punishment on",
            "目标短语块": "inflict damage on",
            "短语块锚点": "造成严重伤害",
            "短语块例句": "The storm can inflict damage on a town.",
            "短语块挖空": "The storm can ____ a town.",
            "学习标记": "★",
        }
        missing = ankiconnect_import._missing_required_field_names(
            fields,
            require_audio=False,
        )
        self.assertNotIn("例句", missing)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
