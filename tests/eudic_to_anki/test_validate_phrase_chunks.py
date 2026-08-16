from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .fixtures import INFLICT_WORD_FAMILY


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
        "word_family": INFLICT_WORD_FAMILY,
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

    def test_word_family_requires_two_labeled_lines(self) -> None:
        result = self.run_validator(
            valid_note(word_family="ascend v. 上升；晋升")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "word_family must contain exactly two non-empty lines",
            result.stderr,
        )

    def test_word_family_requires_breakdown_and_association_labels(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "构成：ascend「v. 上升」→ ascension「n. 上升」\n"
                    "相关：ascent「n. 上升」"
                )
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "word_family lines must start with 拆解： and 联想：",
            result.stderr,
        )

    def test_word_family_rejects_authored_html(self) -> None:
        cases = (
            (
                "<strong>拆解：</strong>ascend「v. 上升」→ "
                "ascension「n. 上升」\n联想：ascent「n. 上升」"
            ),
            (
                "拆解：ascend「v. 上升」→ ascension「n. 上升」\n"
                "联想：ascent「n. 上升」<!-- hidden note -->"
            ),
        )
        for word_family in cases:
            with self.subTest(word_family=word_family):
                result = self.run_validator(
                    valid_note(word_family=word_family)
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "word_family must be plain text without HTML",
                    result.stderr,
                )

    def test_word_family_requires_one_to_three_associations(self) -> None:
        cases = (
            "联想：",
            (
                "联想：ascent「n. 上升」、descend「v. 下降」、"
                "transcend「v. 超越」、condescend「v. 屈尊」"
            ),
        )
        for association_line in cases:
            with self.subTest(association_line=association_line):
                result = self.run_validator(
                    valid_note(
                        word_family=(
                            "拆解：ascend「v. 上升」→ ascension「n. 上升」\n"
                            f"{association_line}"
                        )
                    )
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "word_family must contain 1-3 associations separated by 、",
                    result.stderr,
                )

    def test_word_family_rejects_labeled_placeholders(self) -> None:
        result = self.run_validator(
            valid_note(word_family="拆解：不可拆分\n联想：无")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "omit word_family instead of using placeholder content",
            result.stderr,
        )

    def test_word_family_ignores_separators_inside_chinese_meanings(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "拆解：circum-「环绕、四周」+ spect「看」→ "
                    "circumspect「adj. 谨慎的、考虑周全的」\n"
                    "联想：inspect「v. 检查、审视」、"
                    "prospect「n. 前景、可能性」、"
                    "retrospect「n. 回顾、追溯」"
                )
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_each_word_family_association_needs_pos_and_chinese_meaning(self) -> None:
        association_lines = (
            "联想：ascent、descend",
            "联想：ascent「上升」",
            "联想：ascent「n. rise」",
        )
        for association_line in association_lines:
            with self.subTest(association_line=association_line):
                result = self.run_validator(
                    valid_note(
                        word_family=(
                            "拆解：ascend「v. 上升」→ ascension「n. 上升」\n"
                            f"{association_line}"
                        )
                    )
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "each word_family association must include POS and Chinese meaning",
                    result.stderr,
                )

    def test_word_family_target_needs_pos_and_chinese_meaning(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "拆解：ascend「v. 上升」→ ascension\n"
                    "联想：ascent「n. 上升」"
                )
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "word_family target must include POS and Chinese meaning",
            result.stderr,
        )

    def test_word_family_target_annotation_must_follow_the_arrow(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "拆解：ascend「v. 上升」→ -ion「n. 名词后缀」+ ascension\n"
                    "联想：ascent「n. 上升」"
                )
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "word_family target must include POS and Chinese meaning",
            result.stderr,
        )

    def test_word_family_affixes_do_not_accept_pos_markers(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "拆解：ascend「v. 上升」+ -ion「n. 名词后缀」→ "
                    "ascension「n. 上升」\n联想：ascent「n. 上升」"
                )
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "word_family roots and affixes must not include POS",
            result.stderr,
        )

    def test_word_family_target_suffix_note_does_not_accept_pos_marker(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "拆解：ascend「v. 上升」→ ascension「n. 上升」"
                    "（-ion「n. 名词后缀」）\n联想：ascent「n. 上升」"
                )
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "word_family roots and affixes must not include POS",
            result.stderr,
        )

    def test_word_family_accepts_other_standard_pos_abbreviations(self) -> None:
        result = self.run_validator(
            valid_note(
                word_family=(
                    "拆解：what「pron. 什么」+ ever「adv. 曾经」→ "
                    "whatever「pron. 无论什么」\n"
                    "联想：whatsoever「pron. 无论什么」"
                )
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_word_family_requires_breakdown_content(self) -> None:
        result = self.run_validator(
            valid_note(word_family="拆解：\n联想：ascent「n. 上升」")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("word_family breakdown must not be empty", result.stderr)

    def test_accepts_recommended_word_family_examples(self) -> None:
        examples = (
            (
                "拆解：ascend「v. 上升；晋升」→ ascension「n. 上升；晋升」"
                "（-ion「名词后缀」，词干变体为 ascens-；"
                "scend/scand「攀登、上升」）\n"
                "联想：ascent「n. 上升；攀登」、descend「v. 下降；下去」"
            ),
            (
                "拆解：ir-「不」+ reverse「v. 逆转；颠倒」+ "
                "-ible「能够……的」→ irreversible「adj. 不可逆转的」\n"
                "联想：reversible「adj. 可逆的」、"
                "reversibility「n. 可逆性」"
            ),
            (
                "拆解：circum-「环绕、四周」+ spect「看」→ "
                "circumspect「adj. 谨慎的；考虑周全的」，字面是「向四周看」\n"
                "联想：inspect「v. 检查」、prospect「n. 前景」、"
                "retrospect「n. 回顾」"
            ),
            (
                "拆解：bene-「好、善」+ vol/volent「意愿、希望」→ "
                "benevolent「adj. 仁慈的；乐善好施的」\n"
                "联想：benevolence「n. 仁慈；善意」、"
                "malevolent「adj. 恶意的」"
            ),
        )
        for word_family in examples:
            with self.subTest(word_family=word_family):
                result = self.run_validator(valid_note(word_family=word_family))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_chunk_is_optional_but_must_be_traceable(self) -> None:
        omitted = self.run_validator(
            valid_note(source_chunk="", source_chunk_meaning="")
        )
        self.assertEqual(omitted.returncode, 0, omitted.stderr)

        invalid = self.run_validator(valid_note(source_chunk="inflict pain on"))
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("source_chunk must occur in card_sentence", invalid.stderr)

    def test_source_chunk_must_contain_the_target_word(self) -> None:
        result = self.run_validator(
            valid_note(
                source_chunk="serious damage",
                source_chunk_meaning="严重破坏",
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "source_chunk must contain the target word or a valid inflection",
            result.stderr,
        )

    def test_source_chunk_rejects_target_only_and_determiner_only_content(
        self,
    ) -> None:
        cases = (
            valid_note(
                source_chunk="inflicted",
                source_chunk_meaning="造成",
            ),
            valid_note(
                word="medieval",
                pronunciation="/ˌmediˈiːvəl/",
                meaning=["adj. 中世纪的"],
                english_definition="relating to the Middle Ages in European history",
                word_family="",
                source_context="A medieval anatomist studied the human body.",
                card_sentence="A medieval anatomist studied the human body.",
                source_chunk="medieval",
                source_chunk_meaning="中世纪的",
            ),
            valid_note(
                word="cleft",
                pronunciation="/kleft/",
                meaning=["n. 裂缝；裂口"],
                english_definition="a narrow opening or split in a surface",
                word_family="",
                source_context="Start at the cleft where the rock divides.",
                card_sentence="Start at the cleft where the rock divides.",
                source_chunk="the cleft",
                source_chunk_meaning="裂口处",
            ),
            valid_note(
                word="lead",
                pronunciation="/liːd/",
                meaning=["n. 提前量"],
                english_definition="time available before something needs to begin",
                word_family="",
                source_context="We want to reduce our lead time.",
                card_sentence="We want to reduce our lead time.",
                source_chunk="lead",
                source_chunk_meaning="lead time 中的交付周期",
            ),
        )
        for case in cases:
            with self.subTest(word=case["word"], chunk=case["source_chunk"]):
                result = self.run_validator(case)
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "source_chunk must add phrase-level information beyond the target word",
                    result.stderr,
                )

    def test_source_chunk_accepts_terms_and_required_prepositions(self) -> None:
        cases = (
            valid_note(
                word="lead",
                pronunciation="/liːd/",
                meaning=["n. 提前量"],
                english_definition="time available before something needs to begin",
                word_family="",
                source_context="We want to reduce our lead time.",
                card_sentence="We want to reduce our lead time.",
                source_chunk="lead time",
                source_chunk_meaning="交付周期；前置时间",
            ),
            valid_note(
                word="rely",
                pronunciation="/rɪˈlaɪ/",
                meaning=["vi. 依靠；信赖"],
                english_definition="to need or trust someone or something",
                word_family="",
                source_context="You can rely on this backup system.",
                card_sentence="You can rely on this backup system.",
                source_chunk="rely on",
                source_chunk_meaning="依靠；信赖",
            ),
        )
        for case in cases:
            with self.subTest(word=case["word"], chunk=case["source_chunk"]):
                result = self.run_validator(case)
                self.assertEqual(result.returncode, 0, result.stderr)

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


class WordCoachPromptContractTests(unittest.TestCase):
    def test_prompt_covers_semantic_morphology_failures(self) -> None:
        prompt = (SKILL / "references" / "word-coach-json-prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("只列 `ascent, descend`", prompt)
        self.assertIn("`take a toll on` 等固定短语虚构词根词缀", prompt)
        self.assertIn("低置信度词源", prompt)
        self.assertIn("基础词、目标词和联想词统一写成", prompt)
        self.assertIn("前缀、后缀和词根写成", prompt)

    def test_prompt_defines_the_source_chunk_quality_gate(self) -> None:
        prompt = (SKILL / "references" / "word-coach-json-prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("稀疏的短语级学习线索", prompt)
        self.assertIn("目标词本身、目标词的单个词形", prompt)
        self.assertIn("只增加冠词，留空", prompt)
        self.assertIn("词块和释义范围不一致", prompt)


if __name__ == "__main__":
    unittest.main()
