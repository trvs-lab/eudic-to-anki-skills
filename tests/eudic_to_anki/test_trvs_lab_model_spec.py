from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "skills" / "eudic-to-anki" / "assets"


class TrvsLabModelSpecTests(unittest.TestCase):
    def test_model_spec_has_phrase_chunk_fields(self) -> None:
        spec = json.loads((ASSETS / "trvs_lab_model.json").read_text(encoding="utf-8"))
        self.assertIn("目标短语块", spec["fields"])
        self.assertIn("短语块锚点", spec["fields"])
        self.assertIn("短语块例句", spec["fields"])
        self.assertIn("短语块挖空", spec["fields"])

    def test_model_spec_has_anchor_and_recall_templates(self) -> None:
        spec = json.loads((ASSETS / "trvs_lab_model.json").read_text(encoding="utf-8"))
        names = [template["Name"] for template in spec["card_templates"]]
        self.assertEqual(names, ["Chunk Anchor", "Chunk Recall"])

    def test_template_files_exist_and_reference_new_fields(self) -> None:
        anchor_front = (ASSETS / "trvs_lab_chunk_anchor_front.html").read_text(encoding="utf-8")
        anchor_back = (ASSETS / "trvs_lab_chunk_anchor_back.html").read_text(encoding="utf-8")
        recall_front = (ASSETS / "trvs_lab_chunk_recall_front.html").read_text(encoding="utf-8")
        recall_back = (ASSETS / "trvs_lab_chunk_recall_back.html").read_text(encoding="utf-8")
        self.assertIn("{{目标短语块}}", anchor_front)
        self.assertIn("{{短语块例句}}", anchor_front)
        self.assertNotIn("{{例句}}", anchor_front)
        self.assertIn("{{FrontSide}}", anchor_back)
        self.assertIn("phrase-confirmation", anchor_back)
        self.assertIn("{{短语块锚点}}", anchor_back)
        self.assertIn("{{#例句}}", anchor_back)
        self.assertIn("{{/例句}}", anchor_back)
        self.assertIn("word-header", anchor_back)
        self.assertIn("{{单词}}", anchor_back)
        self.assertLess(anchor_back.index("{{单词}}"), anchor_back.index("{{音标}}"))
        self.assertLess(anchor_back.index("{{音标}}"), anchor_back.index("{{释义}}"))
        self.assertLess(anchor_back.index("{{短语块锚点}}"), anchor_back.index("{{例句}}"))
        self.assertLess(anchor_back.index("{{例句}}"), anchor_back.index("{{单词}}"))
        self.assertIn("{{#短语块挖空}}", recall_front)
        self.assertLess(recall_front.index("{{短语块挖空}}"), recall_front.index("{{短语块锚点}}"))
        self.assertIn("recall-hint", recall_front)
        self.assertIn("recall-blank", recall_front)
        self.assertIn("{{目标短语块}}", recall_back)
        self.assertNotIn("{{短语块例句}}", recall_back)
        self.assertIn("{{#例句}}", recall_back)
        self.assertNotIn("{{短语块锚点}}", recall_back)
        self.assertIn("recall-answer-head", recall_back)
        self.assertIn("word-header", recall_back)
        self.assertIn("{{单词}}", recall_back)
        self.assertLess(recall_back.index("{{单词}}"), recall_back.index("{{音标}}"))
        self.assertLess(recall_back.index("{{音标}}"), recall_back.index("{{释义}}"))

    def test_model_referenced_assets_exist(self) -> None:
        spec = json.loads((ASSETS / "trvs_lab_model.json").read_text(encoding="utf-8"))
        for template in spec["card_templates"]:
            self.assertTrue((ASSETS / template["FrontPath"]).is_file())
            self.assertTrue((ASSETS / template["BackPath"]).is_file())
        self.assertTrue((ASSETS / spec["css_path"]).is_file())

    def test_anchor_highlighter_wraps_text_nodes_without_rewriting_markup(self) -> None:
        anchor_front = (ASSETS / "trvs_lab_chunk_anchor_front.html").read_text(encoding="utf-8")
        self.assertNotIn("instance.innerHTML = instance.innerHTML.replace", anchor_front)
        self.assertIn("document.createTreeWalker", anchor_front)
        self.assertIn("NodeFilter.SHOW_TEXT", anchor_front)
        self.assertIn("createHighlightNode", anchor_front)
        self.assertNotIn("split(/\\s+/)", anchor_front)
        self.assertIn("var phrase = chunk.textContent.trim()", anchor_front)

    def test_recall_front_styles_keep_cloze_as_primary_prompt(self) -> None:
        styling = (ASSETS / "trvs_lab_styling.css").read_text(encoding="utf-8")
        self.assertIn("-webkit-font-smoothing: antialiased", styling)
        self.assertIn("overflow-x: hidden", styling)
        self.assertIn(".chunk-recall-card .items + .items", styling)
        self.assertIn(".chunk-recall-card {", styling)
        self.assertIn("padding-bottom: 10px", styling)
        self.assertIn(".chunk-recall-card .recall-cloze", styling)
        self.assertIn("font-size: 22px", styling)
        self.assertIn(".chunk-recall-card .recall-hint", styling)
        self.assertIn("font-size: 18px", styling)
        self.assertIn("background: transparent", styling)
        self.assertIn(".recall-blank", styling)
        self.assertIn("border-bottom: 0", styling)
        self.assertIn(".chunk-recall-answer .recall-answer-head", styling)
        self.assertIn(".chunk-answer .phrase-confirmation", styling)
        self.assertIn(".word-header", styling)
        self.assertIn("overflow-wrap: anywhere", styling)


if __name__ == "__main__":
    unittest.main()
