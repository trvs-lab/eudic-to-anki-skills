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
        self.notes_info_override: list[dict[str, Any]] | None = None
        self.cards_info_override: list[dict[str, Any]] | None = None
        self.cards_info_by_request: dict[tuple[int, ...], list[dict[str, Any]]] = {}
        self.cards = {
            101: {"cardId": 101, "note": 1, "ord": 0, "deckName": "words"},
            102: {"cardId": 102, "note": 1, "ord": 1, "deckName": "words"},
            201: {"cardId": 201, "note": 2, "ord": 0, "deckName": "words"},
        }

    def invoke(self, action: str, **params: Any) -> Any:
        self.calls.append((action, params))
        if action == "notesInfo":
            if self.notes_info_override is not None:
                return self.notes_info_override
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
            request_key = tuple(params["cards"])
            if request_key in self.cards_info_by_request:
                return self.cards_info_by_request[request_key]
            if self.cards_info_override is not None:
                return self.cards_info_override
            return [self.cards[card_id] for card_id in params["cards"]]
        if action == "changeDeck":
            return None
        return None


class CardRoutingTests(unittest.TestCase):
    def test_planned_chunk_deck_counts_are_card_counts(self) -> None:
        payloads = [
            {"fields": {"学习标记": "★"}},
            {"fields": {"学习标记": "◇"}},
            {"fields": {"学习标记": "×"}},
        ]

        self.assertEqual(
            ankiconnect_import.planned_chunk_deck_counts_text(payloads, "words"),
            (
                "words::chunk-anchor::focus: 1, "
                "words::chunk-anchor::ignore: 1, "
                "words::chunk-anchor::passive: 1, "
                "words::chunk-recall::focus: 1"
            ),
        )

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

    def test_route_raises_without_changing_decks_when_notes_info_omits_note(self) -> None:
        client = FakeClient()
        client.notes_info_override = []

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])

    def test_route_raises_without_changing_decks_when_notes_info_has_unexpected_note(
        self,
    ) -> None:
        client = FakeClient()
        client.notes_info_override = [
            {
                "noteId": 1,
                "fields": {
                    "单词": {"value": "inflict"},
                    "学习标记": {"value": "★"},
                },
                "cards": [101, 102],
            },
            {
                "noteId": 3,
                "fields": {
                    "单词": {"value": "stray"},
                    "学习标记": {"value": "◇"},
                },
                "cards": [301],
            },
        ]

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])

    def test_route_raises_without_changing_decks_when_cards_info_omits_card(self) -> None:
        client = FakeClient()
        client.cards_info_override = [client.cards[101]]

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])

    def test_route_raises_without_changing_decks_when_cards_info_has_unexpected_card(
        self,
    ) -> None:
        client = FakeClient()
        client.cards_info_override = [
            client.cards[101],
            client.cards[102],
            {"cardId": 999, "note": 1, "ord": 0, "deckName": "words"},
        ]

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])

    def test_route_raises_without_changing_decks_when_cards_info_duplicates_card(
        self,
    ) -> None:
        client = FakeClient()
        client.cards_info_override = [
            client.cards[101],
            client.cards[101],
            client.cards[102],
        ]

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])

    def test_route_does_not_change_any_decks_when_later_note_has_bad_cards_info(
        self,
    ) -> None:
        client = FakeClient()
        client.cards_info_by_request[(101, 102)] = [
            client.cards[101],
            client.cards[102],
        ]
        client.cards_info_by_request[(201,)] = []

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [1, 2], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])

    def test_route_raises_for_non_focus_recall_card(self) -> None:
        client = FakeClient()
        client.cards[201] = {"cardId": 201, "note": 2, "ord": 1, "deckName": "words"}

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.route_trvs_chunk_cards(client, [2], base_deck="words")

        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(change_calls, [])


if __name__ == "__main__":
    unittest.main()
