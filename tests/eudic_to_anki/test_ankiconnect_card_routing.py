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
    "ankiconnect_import",
    SCRIPTS / "ankiconnect_import.py",
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.cards = {
            101: {"cardId": 101, "note": 1, "ord": 0, "deckName": "words"},
            102: {"cardId": 102, "note": 1, "ord": 1, "deckName": "words"},
            201: {"cardId": 201, "note": 2, "ord": 0, "deckName": "words"},
        }

    def invoke(self, action: str, **params: Any) -> Any:
        self.calls.append((action, params))
        if action == "notesInfo":
            notes = params["notes"]
            result = []
            for note_id in notes:
                if note_id == 1:
                    result.append(
                        {
                            "noteId": 1,
                            "fields": {
                                "单词": {"value": "inflict"},
                                "学习标记": {"value": "★"},
                            },
                            "cards": [101, 102],
                        }
                    )
                if note_id == 2:
                    result.append(
                        {
                            "noteId": 2,
                            "fields": {
                                "单词": {"value": "sphinx"},
                                "学习标记": {"value": "◇"},
                            },
                            "cards": [201],
                        }
                    )
            return result
        if action == "cardsInfo":
            return [self.cards[card_id] for card_id in params["cards"]]
        if action == "changeDeck":
            return None
        return None


class CardRoutingTests(unittest.TestCase):
    def test_chunk_deck_names_are_action_first(self) -> None:
        self.assertEqual(
            ankiconnect_import.chunk_anchor_deck_name("words", "focus"),
            "words::chunk-anchor::focus",
        )
        self.assertEqual(
            ankiconnect_import.chunk_recall_deck_name("words"),
            "words::chunk-recall::focus",
        )

    def test_route_focus_note_cards_to_anchor_and_recall_decks(self) -> None:
        client = FakeClient()
        ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")
        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertIn(
            ("changeDeck", {"cards": [101], "deck": "words::chunk-anchor::focus"}),
            change_calls,
        )
        self.assertIn(
            ("changeDeck", {"cards": [102], "deck": "words::chunk-recall::focus"}),
            change_calls,
        )

    def test_route_passive_note_only_to_anchor_deck(self) -> None:
        client = FakeClient()
        ankiconnect_import.route_trvs_chunk_cards(client, [2], base_deck="words")
        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(
            change_calls,
            [("changeDeck", {"cards": [201], "deck": "words::chunk-anchor::passive"})],
        )


if __name__ == "__main__":
    unittest.main()
