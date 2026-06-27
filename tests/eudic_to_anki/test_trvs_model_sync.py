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


class TrvsModelSyncTests(unittest.TestCase):
    def test_model_templates_need_update_when_chunk_templates_missing(self) -> None:
        templates = {"Card 1": {"Front": "{{单词}}", "Back": "{{释义}}"}}
        self.assertTrue(ankiconnect_import._model_templates_need_update(templates))

    def test_model_templates_need_update_when_anchor_sentence_missing(self) -> None:
        templates = {
            "Chunk Anchor": {"Front": "{{目标短语块}}{{例句}}", "Back": "{{FrontSide}}"},
            "Chunk Recall": {
                "Front": "{{#短语块挖空}}{{短语块挖空}}{{/短语块挖空}}",
                "Back": "{{目标短语块}}{{短语块例句}}",
            },
        }
        self.assertTrue(ankiconnect_import._model_templates_need_update(templates))

    def test_model_templates_need_update_when_chunk_back_fields_missing(self) -> None:
        templates = {
            "Chunk Anchor": {
                "Front": "{{目标短语块}}{{短语块例句}}",
                "Back": "{{FrontSide}}{{音标}}",
            },
            "Chunk Recall": {
                "Front": "{{#短语块挖空}}{{短语块挖空}}{{/短语块挖空}}",
                "Back": "{{目标短语块}}",
            },
        }
        self.assertTrue(ankiconnect_import._model_templates_need_update(templates))

    def test_model_templates_do_not_need_update_when_chunk_templates_exist(self) -> None:
        templates = {
            "Chunk Anchor": {
                "Front": "{{目标短语块}}{{短语块例句}}",
                "Back": "{{FrontSide}}{{短语块锚点}}{{#例句}}{{例句}}{{/例句}}",
            },
            "Chunk Recall": {
                "Front": "{{#短语块挖空}}{{短语块挖空}}{{/短语块挖空}}",
                "Back": "{{目标短语块}}{{短语块例句}}",
            },
        }
        self.assertFalse(ankiconnect_import._model_templates_need_update(templates))


if __name__ == "__main__":
    unittest.main()
