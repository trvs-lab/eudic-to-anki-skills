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
        self.assertIn("document.createTreeWalker", front)
        self.assertIn('"take": "took taken taking takes"', front)
        self.assertIn('base.slice(0, -1) + "ing"', front)
        self.assertNotIn("innerHTML =", front)
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

    def test_front_typography_is_stable_across_anki_platforms(self) -> None:
        css = (ASSETS / self.spec["css_path"]).read_text(encoding="utf-8")
        word_button = css.split(".word-button {", 1)[1].split("}", 1)[0]
        sentence = css.split(".card-sentence {", 1)[1].split("}", 1)[0]
        self.assertIn("\n  appearance: none", word_button)
        self.assertIn("-webkit-appearance: none", word_button)
        self.assertIn("font-family: Georgia, serif !important", word_button)
        self.assertIn("font-size: 34px !important", word_button)
        self.assertIn("font-weight: 650 !important", word_button)
        self.assertIn("width: fit-content", sentence)
        self.assertIn("max-width: 100%", sentence)
        self.assertIn("text-align: left", sentence)

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
        self.assertNotIn(
            '<span class="answer-label">词族构词</span>',
            back,
        )
        self.assertIn('<div class="word-family">{{词族构词}}</div>', back)
        self.assertIn('id="latest-encounter"', back)
        self.assertIn("latest.textContent = match[0]", back)

    def test_word_family_uses_full_width_and_preserves_authored_lines(self) -> None:
        css = (ASSETS / self.spec["css_path"]).read_text(encoding="utf-8")
        self.assertIn(".word-family", css)
        self.assertIn("white-space: pre-line", css)
        self.assertNotIn(".answer-row.word-family", css)

    def test_model_referenced_assets_exist(self) -> None:
        for template in self.spec["card_templates"]:
            self.assertTrue((ASSETS / template["FrontPath"]).is_file())
            self.assertTrue((ASSETS / template["BackPath"]).is_file())
        self.assertTrue((ASSETS / self.spec["css_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
