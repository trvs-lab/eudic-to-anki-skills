from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
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
        self.assertIn("-webkit-tap-highlight-color: transparent", word_button)
        self.assertIn("font-family: Georgia, serif !important", word_button)
        self.assertIn("font-size: 34px !important", word_button)
        self.assertIn("font-weight: 650 !important", word_button)
        self.assertIn("border-radius: 0 !important", word_button)
        self.assertIn("box-shadow: none !important", word_button)
        self.assertIn("min-width: 0", word_button)
        self.assertIn("min-height: 0", word_button)
        self.assertIn("outline: none", word_button)
        self.assertIn(".word-button:active,\n.word-button:focus", css)
        self.assertIn("background: transparent !important", css)
        self.assertIn("border-color: transparent !important", css)
        self.assertIn(
            "outline: 3px solid rgba(79, 111, 103, 0.18) !important",
            css,
        )
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
        self.assertIn('<span class="note-label">来源</span>', back)
        self.assertIn('<span class="note-label">释义</span>', back)
        self.assertIn('id="annotation-rail"', back)
        self.assertIn('id="word-family-source"', back)
        self.assertIn("appendMorphologyRows", back)
        self.assertNotIn("innerHTML", back)
        self.assertIn('id="latest-encounter"', back)
        self.assertIn("latest.textContent = match[0]", back)

    def test_context_notes_share_one_rail_and_preserve_word_family_labels(self) -> None:
        template = self.spec["card_templates"][0]
        back = (ASSETS / template["BackPath"]).read_text(encoding="utf-8")
        css = (ASSETS / self.spec["css_path"]).read_text(encoding="utf-8")
        self.assertIn(".annotation-rail", css)
        self.assertIn(".annotation-rail::before", css)
        self.assertIn(".note-row", css)
        self.assertIn(".note-label", css)
        self.assertIn(".morphology-start::before", css)
        self.assertIn('line.indexOf("拆解：") === 0', back)
        self.assertIn('line.indexOf("联想：") === 0', back)
        self.assertIn('node.nodeName === "BR"', back)

    def test_history_is_inside_the_annotation_card_with_a_display_only_label(self) -> None:
        back = (ASSETS / self.spec["card_templates"][0]["BackPath"]).read_text(
            encoding="utf-8"
        )

        class ParentIds(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.stack = []
                self.parents = {}

            def handle_starttag(self, tag, attrs) -> None:
                element_id = dict(attrs).get("id")
                if element_id:
                    self.parents[element_id] = self.stack[-1] if self.stack else None
                self.stack.append(element_id)

            def handle_endtag(self, tag) -> None:
                self.stack.pop()

        markup = ParentIds()
        markup.feed(back.split("<script>", 1)[0])
        self.assertEqual(markup.parents["history-row"], "annotation-rail")
        self.assertEqual(markup.parents["history-contexts"], "history-row")
        self.assertIn('<span class="note-label">温故</span>', back)
        self.assertIn("{{#历史语境}}", back)
        self.assertIn("{{历史语境}}", back)
        self.assertNotIn("{{温故}}", back)

    def test_front_and_history_share_the_same_highlighter(self) -> None:
        template = self.spec["card_templates"][0]
        front = (ASSETS / template["FrontPath"]).read_text(encoding="utf-8")
        back = (ASSETS / template["BackPath"]).read_text(encoding="utf-8")
        self.assertEqual(front.count("function highlightContextWord("), 1)
        self.assertIn(
            'highlightContextWord(document.getElementById("card-sentence"))', front
        )
        self.assertIn("highlightContextWord(history)", back)
        self.assertLess(
            back.index("history.appendChild(paragraph)"),
            back.index("highlightContextWord(history)"),
        )
        self.assertNotIn("function highlightContextWord(", back)

    def test_card_uses_restrained_emphasis_without_a_headword_underline(self) -> None:
        css = (ASSETS / self.spec["css_path"]).read_text(encoding="utf-8")
        word_button = css.split(".word-button {", 1)[1].split("}", 1)[0]
        mark = css.split("mark {", 1)[1].split("}", 1)[0]
        ipa = css.split(".answer-ipa {", 1)[1].split("}", 1)[0]
        rail = css.split(".annotation-rail::before {", 1)[1].split("}", 1)[0]
        self.assertIn("text-decoration: none", word_button)
        self.assertNotIn("border-bottom", word_button)
        self.assertIn("text-decoration-color: var(--mark)", mark)
        self.assertIn("color: var(--ipa)", ipa)
        self.assertIn("background: var(--rail)", rail)

    def test_card_compacts_notes_hides_scrollbars_and_keeps_answer_stationary(self) -> None:
        css = (ASSETS / self.spec["css_path"]).read_text(encoding="utf-8")
        self.assertIn("scrollbar-width: none", css)
        self.assertIn("html::-webkit-scrollbar", css)
        self.assertIn("body::-webkit-scrollbar", css)
        self.assertIn(
            "grid-template-columns: 60px minmax(0, 1fr); gap: 10px",
            css,
        )
        self.assertIn(
            "grid-template-columns: 54px minmax(0, 1fr); gap: 8px",
            css,
        )
        self.assertIn("left: 70px", css)
        self.assertIn("left: 62px", css)
        answer_panel = css.split(".answer-panel {", 1)[1].split("}", 1)[0]
        self.assertNotIn("animation", answer_panel)
        self.assertNotIn("@keyframes answer-reveal", css)
        self.assertNotIn("@keyframes answer-fade", css)
        self.assertNotIn("translateY(8px)", css)

    def test_card_promotes_the_sage_palette_in_light_and_dark_modes(self) -> None:
        css = (ASSETS / self.spec["css_path"]).read_text(encoding="utf-8")
        card = css.split(".card {", 1)[1].split("}", 1)[0]
        night = css.split(".nightMode .card {", 1)[1].split("}", 1)[0]
        for token in (
            "--ink: #1d2926",
            "--muted: #61716c",
            "--faint: #8b9995",
            "--line: #dfe7e3",
            "--ipa: #4f6f67",
            "--mark: rgba(75, 106, 98, 0.42)",
            "--rail: #8ba49d",
            "--note: #f1f6f4",
            "background: #fbfdfc",
        ):
            self.assertIn(token, card)
        for token in (
            "--ipa: #9bb7af",
            "--mark: rgba(155, 183, 175, 0.45)",
            "--rail: #708f87",
            "--note: rgba(155, 183, 175, 0.065)",
            "background: #17201e",
        ):
            self.assertIn(token, night)

    def test_model_referenced_assets_exist(self) -> None:
        for template in self.spec["card_templates"]:
            self.assertTrue((ASSETS / template["FrontPath"]).is_file())
            self.assertTrue((ASSETS / template["BackPath"]).is_file())
        self.assertTrue((ASSETS / self.spec["css_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
