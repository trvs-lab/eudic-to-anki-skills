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
        self.assertIn("{{FrontSide}}", anchor_back)
        self.assertIn("{{#短语块挖空}}", recall_front)
        self.assertIn("{{目标短语块}}", recall_back)
        self.assertNotIn("{{短语块锚点}}", recall_back)


if __name__ == "__main__":
    unittest.main()
