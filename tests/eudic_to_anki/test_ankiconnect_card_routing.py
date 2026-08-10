from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import", SCRIPTS / "ankiconnect_import.py"
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class FakeClient:
    def __init__(self, *, group: str = "defer") -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.group = group

    def invoke(self, action: str, **params: Any) -> Any:
        self.calls.append((action, params))
        if action == "findNotes":
            return [1]
        if action == "notesInfo":
            return [
                {
                    "noteId": 1,
                    "fields": {
                        "单词": {"value": "inflict"},
                        "规范词形": {"value": "inflict"},
                        "卡片例句": {"value": "The storm inflicted damage."},
                        "例句来源": {"value": "source"},
                        "原始来源": {"value": "The storm inflicted damage."},
                        "遇见次数": {"value": "1"},
                        "最近遇见": {"value": "2026-08-09T01:00:00Z"},
                        "遇见记录": {
                            "value": (
                                '[{"id":"old","at":"2026-08-09T01:00:00Z",'
                                '"raw_source":"The storm inflicted damage.",'
                                '"card_sentence":"The storm inflicted damage.",'
                                '"origin":"source"}]'
                            )
                        },
                        "学习分组": {"value": self.group},
                        "发音": {"value": "[sound:inflict.mp3]"},
                    },
                    "tags": [],
                    "cards": [101],
                }
            ]
        if action == "cardsInfo":
            return [
                {
                    "cardId": 101,
                    "note": 1,
                    "ord": 0,
                    "deckName": f"words::{self.group}",
                }
            ]
        if action in {"updateNote", "forgetCards", "changeDeck"}:
            return None
        raise AssertionError(f"unexpected action {action}")


def note(
    *, timestamp: str, raw: str = "The flood inflicted more damage."
) -> dict[str, Any]:
    return {
        "word": "Inflict",
        "pronunciation": "/ɪnˈflɪkt/",
        "meaning": ["vt. 使遭受；造成"],
        "english_definition": "to make someone suffer something unpleasant",
        "word_family": "in-（向内）+ flict（打击）",
        "source_context": raw,
        "card_sentence": raw or "Criticism can inflict lasting harm on a child.",
        "sentence_origin": "source" if raw else "generated",
        "learning_group": "defer",
        "category_id": "book-1",
        "add_time_utc": timestamp,
        "audio_html": "[sound:inflict.mp3]",
    }


class ContextAnchorImportTests(unittest.TestCase):
    def test_managed_deck_names_are_learn_defer_skip(self) -> None:
        self.assertEqual(
            ankiconnect_import.managed_decks("words"),
            ["words::learn", "words::defer", "words::skip"],
        )

    def test_new_encounter_promotes_defer_and_resets_one_card(self) -> None:
        client = FakeClient(group="defer")
        summary = ankiconnect_import.upsert_context_anchor_notes(
            client,
            [note(timestamp="2026-08-10T01:00:00Z")],
            base_deck="words",
            model="TRVS-Lab",
        )
        actions = [action for action, _ in client.calls]
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["defer_to_learn"], 1)
        self.assertIn("updateNote", actions)
        self.assertIn(("forgetCards", {"cards": [101]}), client.calls)
        self.assertIn(
            ("changeDeck", {"cards": [101], "deck": "words::learn"}),
            client.calls,
        )

    def test_skip_deck_is_authoritative_on_new_encounter(self) -> None:
        client = FakeClient(group="skip")
        ankiconnect_import.upsert_context_anchor_notes(
            client,
            [note(timestamp="2026-08-10T01:00:00Z")],
            base_deck="words",
            model="TRVS-Lab",
        )
        change_calls = [
            params for action, params in client.calls if action == "changeDeck"
        ]
        self.assertEqual(change_calls, [])
        update = next(
            params for action, params in client.calls if action == "updateNote"
        )
        self.assertEqual(update["note"]["fields"]["学习分组"], "skip")

    def test_exact_reimport_is_idempotent_and_does_not_reset(self) -> None:
        client = FakeClient(group="defer")
        repeated = note(
            timestamp="2026-08-09T01:00:00Z",
            raw="The storm inflicted damage.",
        )
        repeated["encounter_id"] = "old"
        summary = ankiconnect_import.upsert_context_anchor_notes(
            client, [repeated], base_deck="words", model="TRVS-Lab"
        )
        mutations = {
            "updateNote",
            "forgetCards",
            "changeDeck",
            "addNote",
            "addNotes",
        }
        self.assertEqual(summary["idempotent"], 1)
        self.assertFalse(any(action in mutations for action, _ in client.calls))


if __name__ == "__main__":
    unittest.main()
