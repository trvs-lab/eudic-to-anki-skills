from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "ankiconnect_import_sync", SCRIPTS / "ankiconnect_import.py"
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class TrvsModelSyncTests(unittest.TestCase):
    def test_legacy_recall_model_requires_explicit_reimport_migration(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "modelNames":
                    return ["TRVS-Lab"]
                if action == "modelTemplates":
                    return {"Chunk Anchor": {}, "Chunk Recall": {}}
                raise AssertionError(action)

        with self.assertRaisesRegex(
            ankiconnect_import.AnkiImportError,
            "delete the legacy TRVS-Lab notes/note type",
        ):
            ankiconnect_import.assert_model_migration_safe(Client(), "TRVS-Lab")

    def test_current_context_anchor_template_does_not_need_update(self) -> None:
        front = "{{单词}}{{卡片例句}} playAudio"
        back = "".join(
            "{{" + field + "}}"
            for field in (
                "语境释义",
                "音标",
                "英英",
                "来源词块",
                "词块释义",
                "词族构词",
                "历史语境",
                "遇见次数",
                "最近遇见",
            )
        )
        self.assertFalse(
            ankiconnect_import._model_templates_need_update(
                {"Context Anchor": {"Front": front, "Back": back}}
            )
        )

    def test_extra_or_legacy_template_needs_update(self) -> None:
        self.assertTrue(
            ankiconnect_import._model_templates_need_update(
                {"Context Anchor": {}, "Chunk Recall": {}}
            )
        )

    def test_single_legacy_card_name_also_requires_reimport(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "modelNames":
                    return ["TRVS-Lab"]
                if action == "modelTemplates":
                    return {"Card 1": {}}
                raise AssertionError(action)

        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.assert_model_migration_safe(Client(), "TRVS-Lab")

    def test_context_anchor_template_with_legacy_fields_requires_reimport(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "modelNames":
                    return ["TRVS-Lab"]
                if action == "modelTemplates":
                    return {"Context Anchor": {}}
                if action == "modelFieldNames":
                    return ["单词", "学习标记", "卡片例句"]
                raise AssertionError(action)

        issues = ankiconnect_import.inspect_model_issues(Client(), "TRVS-Lab")
        self.assertEqual(issues, ["legacy fields remain: 学习标记"])
        with self.assertRaises(ankiconnect_import.AnkiImportError):
            ankiconnect_import.assert_model_migration_safe(Client(), "TRVS-Lab")

    def test_replaced_definition_root_and_example_fields_are_legacy(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "modelNames":
                    return ["TRVS-Lab"]
                if action == "modelTemplates":
                    return {"Context Anchor": {}}
                if action == "modelFieldNames":
                    return ["单词", "释义", "词根", "例句", "卡片例句"]
                raise AssertionError(action)

        issues = ankiconnect_import.inspect_model_issues(Client(), "TRVS-Lab")
        self.assertIn("例句", issues[0])
        self.assertIn("词根", issues[0])
        self.assertIn("释义", issues[0])

    def test_css_version_marks_current_style(self) -> None:
        self.assertTrue(ankiconnect_import._model_css_needs_update(".card{}"))
        self.assertFalse(
            ankiconnect_import._model_css_needs_update(
                "/* trvs-style-version: context-anchor-v1 */"
            )
        )


if __name__ == "__main__":
    unittest.main()
