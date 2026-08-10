from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "skills" / "eudic-to-anki" / "assets"


class TrvsLabModelSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = json.loads(
            (ASSETS / "trvs_lab_model.json").read_text(encoding="utf-8")
        )

    def test_model_has_context_anchor_fields_and_one_template(self) -> None:
        self.assertEqual(
            self.spec["fields"],
            [
                "单词",
                "规范词形",
                "音标",
                "语境释义",
                "英英",
                "原始来源",
                "卡片例句",
                "例句来源",
                "来源词块",
                "词块释义",
                "词族构词",
                "历史语境",
                "遇见次数",
                "最近遇见",
                "遇见记录",
                "学习分组",
                "发音",
            ],
        )
        self.assertEqual(
            [template["Name"] for template in self.spec["card_templates"]],
            ["Context Anchor"],
        )

    def test_front_only_renders_word_sentence_and_clickable_audio(self) -> None:
        template = self.spec["card_templates"][0]
        front = (ASSETS / template["FrontPath"]).read_text(encoding="utf-8")
        self.assertIn("{{单词}}", front)
        self.assertIn("{{卡片例句}}", front)
        self.assertIn("{{发音}}", front)
        self.assertIn("playAudio", front)
        for hidden_field in (
            "音标",
            "语境释义",
            "英英",
            "来源词块",
            "词族构词",
            "历史语境",
            "遇见次数",
            "最近遇见",
            "学习分组",
            "例句来源",
            "原始来源",
        ):
            self.assertNotIn("{{" + hidden_field + "}}", front)

    def test_back_is_unfolded_and_follows_information_order(self) -> None:
        template = self.spec["card_templates"][0]
        back = (ASSETS / template["BackPath"]).read_text(encoding="utf-8")
        ordered_fields = [
            "语境释义",
            "音标",
            "英英",
            "来源词块",
            "词块释义",
            "词族构词",
            "历史语境",
            "遇见次数",
            "最近遇见",
        ]
        positions = [back.index("{{" + name + "}}") for name in ordered_fields]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("<details", back)
        self.assertNotIn("{{学习分组}}", back)
        self.assertNotIn("priority-marker", back)
        self.assertNotIn("Chunk Recall", back)

    def test_model_referenced_assets_exist(self) -> None:
        for template in self.spec["card_templates"]:
            self.assertTrue((ASSETS / template["FrontPath"]).is_file())
            self.assertTrue((ASSETS / template["BackPath"]).is_file())
        self.assertTrue((ASSETS / self.spec["css_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
