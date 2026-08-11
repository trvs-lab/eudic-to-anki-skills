from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import", SCRIPTS / "ankiconnect_import.py"
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


def source_note(**overrides: object) -> dict[str, object]:
    note: dict[str, object] = {
        "word": "Inflict",
        "pronunciation": "/ɪnˈflɪkt/",
        "meaning": ["vt. 使遭受；造成"],
        "english_definition": "to make someone suffer something unpleasant",
        "word_family": (
            "拆解：in-「在……上」+ flict「打击」→ inflict「v. 使遭受；造成」\n"
            "联想：conflict「n. 冲突」、afflict「v. 使痛苦」"
        ),
        "source_context": "The storm inflicted serious damage on the town.",
        "card_sentence": "The storm inflicted serious damage on the town.",
        "sentence_origin": "source",
        "source_chunk": "inflicted serious damage on",
        "source_chunk_meaning": "给……造成严重破坏",
        "learning_group": "learn",
        "category_id": "book-1",
        "add_time_utc": "2026-08-10T01:00:00Z",
    }
    note.update(overrides)
    return note


class ContextAnchorFieldTests(unittest.TestCase):
    def test_build_fields_maps_context_anchor_contract(self) -> None:
        fields = ankiconnect_import.build_trvs_lab_fields(
            source_note(), "[sound:inflict.mp3]"
        )
        self.assertEqual(fields["单词"], "Inflict")
        self.assertEqual(fields["规范词形"], "inflict")
        self.assertEqual(
            fields["卡片例句"], "The storm inflicted serious damage on the town."
        )
        self.assertEqual(fields["例句来源"], "source")
        self.assertEqual(fields["来源词块"], "inflicted serious damage on")
        self.assertEqual(
            fields["词族构词"],
            "拆解：in-「在……上」+ flict「打击」→ inflict「v. 使遭受；造成」\n"
            "联想：conflict「n. 冲突」、afflict「v. 使痛苦」",
        )
        self.assertEqual(fields["学习分组"], "learn")
        self.assertEqual(json.loads(fields["遇见记录"])[0]["origin"], "source")

    def test_generated_sentence_is_a_real_encounter_but_not_history(self) -> None:
        first = ankiconnect_import.build_trvs_lab_fields(
            source_note(), "[sound:inflict.mp3]"
        )
        second = ankiconnect_import.build_trvs_lab_fields(
            source_note(
                source_context="",
                card_sentence="Criticism can inflict lasting harm on a young child.",
                sentence_origin="generated",
                add_time_utc="2026-08-11T01:00:00Z",
            ),
            "[sound:inflict.mp3]",
            existing_fields=first,
        )
        self.assertEqual(second["遇见次数"], "2")
        self.assertIn("The storm inflicted serious damage", second["历史语境"])
        self.assertNotIn("Criticism can inflict", second["历史语境"])

    def test_idempotent_encounter_does_not_change_fields(self) -> None:
        first = ankiconnect_import.build_trvs_lab_fields(
            source_note(), "[sound:inflict.mp3]"
        )
        repeated = ankiconnect_import.build_trvs_lab_fields(
            source_note(), "[sound:other.mp3]", existing_fields=first
        )
        self.assertEqual(repeated, first)

    def test_older_backfill_counts_but_does_not_replace_latest_card(self) -> None:
        latest = ankiconnect_import.build_trvs_lab_fields(
            source_note(
                source_context="The flood inflicted more damage on local farms.",
                card_sentence="The flood inflicted more damage on local farms.",
                add_time_utc="2026-08-11T01:00:00Z",
            ),
            "[sound:inflict.mp3]",
        )
        backfilled = ankiconnect_import.build_trvs_lab_fields(
            source_note(add_time_utc="2026-08-09T01:00:00Z"),
            "[sound:inflict.mp3]",
            existing_fields=latest,
        )
        self.assertEqual(
            backfilled["卡片例句"],
            "The flood inflicted more damage on local farms.",
        )
        self.assertEqual(backfilled["最近遇见"], "2026-08-11T01:00:00Z")
        self.assertEqual(backfilled["遇见次数"], "2")
        self.assertIn("The storm inflicted serious damage", backfilled["历史语境"])

    def test_recent_encounter_uses_local_time_and_history_is_newest_first(self) -> None:
        first = ankiconnect_import.build_trvs_lab_fields(
            source_note(
                source_context="The first storm inflicted damage on the coast.",
                card_sentence="The first storm inflicted damage on the coast.",
                add_time_utc="2026-08-08T23:00:00Z",
                add_time_local="2026-08-09 07:00:00",
            ),
            "[sound:inflict.mp3]",
        )
        second = ankiconnect_import.build_trvs_lab_fields(
            source_note(
                source_context="The second storm inflicted damage on nearby farms.",
                card_sentence="The second storm inflicted damage on nearby farms.",
                add_time_utc="2026-08-09T23:00:00Z",
                add_time_local="2026-08-10 07:00:00",
            ),
            "[sound:inflict.mp3]",
            existing_fields=first,
        )
        third = ankiconnect_import.build_trvs_lab_fields(
            source_note(
                source_context="The latest storm inflicted damage on several homes.",
                card_sentence="The latest storm inflicted damage on several homes.",
                add_time_utc="2026-08-10T23:00:00Z",
                add_time_local="2026-08-11 07:00:00",
            ),
            "[sound:inflict.mp3]",
            existing_fields=second,
        )
        self.assertEqual(third["最近遇见"], "2026-08-11 07:00:00")
        self.assertLess(
            third["历史语境"].index("second storm"),
            third["历史语境"].index("first storm"),
        )

    def test_required_fields_do_not_require_optional_word_family_or_chunk(self) -> None:
        fields = ankiconnect_import.build_trvs_lab_fields(
            source_note(word_family="", source_chunk="", source_chunk_meaning=""), ""
        )
        self.assertEqual(
            ankiconnect_import._missing_required_field_names(
                fields, require_audio=False
            ),
            [],
        )
        self.assertEqual(
            ankiconnect_import._missing_required_field_names(
                fields, require_audio=True
            ),
            ["发音"],
        )

    def test_preview_counts_input_records_and_aggregated_terms(self) -> None:
        counts = ankiconnect_import.preview_counts(
            [
                source_note(),
                source_note(add_time_utc="2026-08-11T01:00:00Z"),
                source_note(
                    word="sphinx",
                    learning_group="skip",
                    add_time_utc="2026-08-11T02:00:00Z",
                ),
                {"word": "x", "learning_group": "reject"},
            ]
        )
        self.assertEqual(counts["input_records"], 4)
        self.assertEqual(counts["aggregated_terms"], 2)
        self.assertEqual(counts["learn"], 2)
        self.assertEqual(counts["skip"], 1)
        self.assertEqual(counts["reject"], 1)

    def test_malformed_existing_encounter_log_stops_instead_of_losing_history(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "遇见记录 is not valid JSON"):
            ankiconnect_import.build_trvs_lab_fields(
                source_note(add_time_utc="2026-08-12T01:00:00Z"),
                "[sound:inflict.mp3]",
                existing_fields={"遇见记录": "not-json", "遇见次数": "4"},
            )


if __name__ == "__main__":
    unittest.main()
