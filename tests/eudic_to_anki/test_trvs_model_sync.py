from __future__ import annotations

import contextlib
import fcntl
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import model_contract

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import_sync", SCRIPTS / "ankiconnect_import.py"
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)

sync_spec = importlib.util.spec_from_file_location(
    "sync_trvs_lab_model_cli", SCRIPTS / "sync_trvs_lab_model.py"
)
assert sync_spec is not None and sync_spec.loader is not None
sync_trvs_lab_model = importlib.util.module_from_spec(sync_spec)
sync_spec.loader.exec_module(sync_trvs_lab_model)


class MissingModelClient:
    def __init__(self, events: list[str] | None = None) -> None:
        self.actions: list[str] = []
        self.events = events if events is not None else self.actions
        self.model_exists = False
        self.fields: list[str] = []
        self.templates: dict[str, dict[str, str]] = {}
        self.css = ""
        self.fail_action: str | None = None
        self.ignore_actions: set[str] = set()

    def set_existing(
        self,
        *,
        fields: list[str],
        front: str,
        back: str,
        css: str,
    ) -> None:
        self.model_exists = True
        self.fields = list(fields)
        self.templates = {
            "Context Anchor": {"Front": front, "Back": back}
        }
        self.css = css

    def invoke(self, action: str, **params: object) -> object:
        self.actions.append(action)
        if self.events is not self.actions:
            self.events.append(action)
        if action == self.fail_action:
            raise RuntimeError(f"forced failure: {action}")
        if action in self.ignore_actions:
            return None
        if action == "version":
            return 6
        if action == "modelNames":
            return ["TRVS-Lab"] if self.model_exists else []
        if action == "createModel":
            self.model_exists = True
            self.fields = list(params["inOrderFields"])
            self.templates = {
                str(template["Name"]): {
                    "Front": str(template["Front"]),
                    "Back": str(template["Back"]),
                }
                for template in params["cardTemplates"]
            }
            self.css = str(params["css"])
            return 1
        if action == "modelTemplates":
            return self.templates
        if action == "modelFieldNames":
            return self.fields
        if action == "modelStyling":
            return {"css": self.css}
        if action == "modelFieldAdd":
            self.fields.append(str(params["fieldName"]))
            return None
        if action == "updateModelTemplates":
            model = params["model"]
            self.templates = dict(model["templates"])
            return None
        if action == "updateModelStyling":
            model = params["model"]
            self.css = str(model["css"])
            return None
        if action == "findNotes":
            return [1, 2]
        if action == "deckNames":
            return ["words::learn", "words::defer", "words::skip"]
        if action == "sync":
            return None
        raise AssertionError(action)


def write_model_spec(root: Path) -> Path:
    (root / "front.html").write_text(
        "<div>{{单词}}</div>\n<div>{{卡片例句}}</div>\n", encoding="utf-8"
    )
    (root / "back.html").write_text(
        "<div>{{语境释义}}</div>\n<div>{{发音}}</div>\n", encoding="utf-8"
    )
    (root / "style.css").write_text(".card { color: black; }\n", encoding="utf-8")
    spec_path = root / "model.json"
    spec_path.write_text(
        json.dumps(
            {
                "model_name": "TRVS-Lab",
                "fields": ["单词", "语境释义", "卡片例句", "发音"],
                "css_path": "style.css",
                "card_templates": [
                    {
                        "Name": "Context Anchor",
                        "FrontPath": "front.html",
                        "BackPath": "back.html",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return spec_path


def run_import_cli(argv: list[str], client: object) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with (
        mock.patch.object(sys, "argv", ["ankiconnect_import.py", *argv]),
        mock.patch.object(ankiconnect_import, "AnkiConnectClient", return_value=client),
        mock.patch.object(
            ankiconnect_import,
            "upsert_context_anchor_notes",
            return_value={"added": 0, "updated": 0, "unchanged": 0},
        ),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        return ankiconnect_import.main(), stdout.getvalue(), stderr.getvalue()


def run_sync_cli(argv: list[str], client: object) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with (
        mock.patch.object(sys, "argv", ["sync_trvs_lab_model.py", *argv]),
        mock.patch.object(sync_trvs_lab_model, "AnkiConnectClient", return_value=client),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        try:
            code = sync_trvs_lab_model.main()
        except SystemExit as exc:
            code = int(exc.code)
    return code, stdout.getvalue(), stderr.getvalue()


class ImportModelDryRunCliTests(unittest.TestCase):
    def test_missing_model_dry_run_reports_create_without_writes_or_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            client = MissingModelClient()

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                        "--dry-run",
                    ],
                    client,
                )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Model preflight: action=create", stdout)
        self.assertIn(f"spec={model_spec.resolve()}", stdout)
        self.assertNotIn(
            "createModel", client.actions, "dry-run must not mutate the Anki model"
        )
        prepare_audio.assert_not_called()


class StandaloneModelSyncCliTests(unittest.TestCase):
    def test_check_reports_create_without_mutating_or_syncing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            client = MissingModelClient()

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec), "--check"], client
            )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Model preflight: action=create", stdout)
        self.assertNotIn("createModel", client.actions)
        self.assertNotIn("sync", client.actions)

    def test_default_run_creates_and_verifies_without_cloud_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            client = MissingModelClient()

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec)], client
            )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(client.actions.count("createModel"), 1)
        self.assertIn("Model verify: status=exact", stdout)
        self.assertNotIn("sync", client.actions)

    def test_default_run_performs_complete_compatible_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=[field for field in fields if field != "发音"],
                front="old front",
                back="old back",
                css="old css",
            )

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec)], client
            )

        self.assertEqual(code, 0, stderr)
        field_index = client.actions.index("modelFieldAdd")
        template_index = client.actions.index("updateModelTemplates")
        css_index = client.actions.index("updateModelStyling")
        self.assertLess(field_index, template_index)
        self.assertLess(template_index, css_index)
        self.assertIn("Model verify: status=exact", stdout)
        self.assertNotIn("sync", client.actions)

    def test_explicit_sync_runs_only_after_exact_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front=(root / "front.html").read_text(encoding="utf-8"),
                back=(root / "back.html").read_text(encoding="utf-8"),
                css=(root / "style.css").read_text(encoding="utf-8"),
            )

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec), "--sync"], client
            )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(client.actions[-1], "sync")
        self.assertIn("Model verify: status=exact", stdout)
        self.assertIn("Triggered Anki sync.", stdout)

    def test_check_of_update_plan_remains_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front="old front",
                back=(root / "back.html").read_text(encoding="utf-8"),
                css=(root / "style.css").read_text(encoding="utf-8"),
            )

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec), "--check", "--sync"], client
            )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Model preflight: action=update", stdout)
        self.assertFalse(
            {"modelFieldAdd", "updateModelTemplates", "updateModelStyling", "sync"}
            & set(client.actions)
        )

    def test_removed_partial_update_flags_are_rejected(self) -> None:
        for flag in ("--templates-only", "--css-only", "--create-if-missing"):
            with self.subTest(flag=flag):
                code, _stdout, stderr = run_sync_cli([flag], MissingModelClient())
                self.assertEqual(code, 2)
                self.assertIn(f"unrecognized arguments: {flag}", stderr)

    def test_explicit_sync_is_skipped_when_verification_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front="old front",
                back=(root / "back.html").read_text(encoding="utf-8"),
                css=(root / "style.css").read_text(encoding="utf-8"),
            )
            client.ignore_actions.add("updateModelTemplates")

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec), "--sync"], client
            )

        self.assertEqual(code, 1)
        self.assertIn("Model verify: status=mismatch", stdout)
        self.assertIn("model verification failed", stderr)
        self.assertNotIn("sync", client.actions)

    def test_check_returns_nonzero_for_blocked_legacy_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front="unused",
                back="unused",
                css=(root / "style.css").read_text(encoding="utf-8"),
            )
            client.templates = {"Chunk Anchor": {}, "Chunk Recall": {}}

            code, stdout, stderr = run_sync_cli(
                ["--model-spec", str(model_spec), "--check"], client
            )

        self.assertEqual(code, 1, stderr)
        self.assertIn("Model preflight: action=blocked", stdout)
        self.assertIn("Model migration: note_count=2", stdout)
        self.assertFalse(
            {"modelFieldAdd", "updateModelTemplates", "updateModelStyling", "sync"}
            & set(client.actions)
        )

    def test_sync_cli_uses_the_same_nonblocking_lock_as_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_spec = write_model_spec(root)
            client = MissingModelClient()
            model_contract.MODEL_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

            with model_contract.MODEL_LOCK_PATH.open("a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                code, stdout, stderr = run_sync_cli(
                    ["--model-spec", str(model_spec), "--check"], client
                )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("already running", stderr)
        self.assertEqual(client.actions, [])


class ImportModelContractCliTests(unittest.TestCase):
    def test_missing_model_is_created_and_verified_before_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            events: list[str] = []
            client = MissingModelClient(events)

            def prepare_audio(*_: object, **__: object) -> dict[str, Path]:
                events.append("prepare_audio")
                return {}

            with (
                mock.patch.object(
                    ankiconnect_import, "reuse_existing_anki_audio"
                ),
                mock.patch.object(
                    ankiconnect_import,
                    "prepare_all_audio",
                    side_effect=prepare_audio,
                ),
            ):
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                        "--no-sync",
                    ],
                    client,
                )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(client.actions.count("createModel"), 1)
        self.assertLess(events.index("createModel"), events.index("prepare_audio"))
        self.assertIn("Model verify: status=exact", stdout)

    def test_crlf_and_terminal_newlines_are_strictly_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front=(root / "front.html")
                .read_text(encoding="utf-8")
                .replace("\n", "\r\n")
                + "\r\n",
                back=(root / "back.html").read_text(encoding="utf-8").rstrip("\n"),
                css=(root / "style.css").read_text(encoding="utf-8") + "\n\n",
            )

            code, stdout, stderr = run_import_cli(
                [
                    "--input",
                    str(input_path),
                    "--model-spec",
                    str(model_spec),
                    "--dry-run",
                ],
                client,
            )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Model preflight: action=none", stdout)
        self.assertNotIn(
            "updateModelTemplates", client.actions
        )
        self.assertNotIn("updateModelStyling", client.actions)

    def test_compatible_update_adds_fields_then_updates_only_changed_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            target_front = (root / "front.html").read_text(encoding="utf-8")
            client = MissingModelClient()
            client.set_existing(
                fields=[field for field in fields if field != "发音"] + ["自定义"],
                front=target_front.replace("{{单词}}", "{{单词}} "),
                back=(root / "back.html").read_text(encoding="utf-8"),
                css=(root / "style.css").read_text(encoding="utf-8"),
            )
            events = client.events

            def prepare_audio(*_: object, **__: object) -> dict[str, Path]:
                events.append("prepare_audio")
                return {}

            with (
                mock.patch.object(
                    ankiconnect_import, "reuse_existing_anki_audio"
                ),
                mock.patch.object(
                    ankiconnect_import,
                    "prepare_all_audio",
                    side_effect=prepare_audio,
                ),
            ):
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                        "--no-sync",
                    ],
                    client,
                )

        self.assertEqual(code, 0, stderr)
        self.assertLess(
            events.index("modelFieldAdd"), events.index("updateModelTemplates")
        )
        self.assertLess(
            events.index("updateModelTemplates"), events.index("prepare_audio")
        )
        self.assertNotIn("updateModelStyling", client.actions)
        self.assertIn("自定义", client.fields)
        self.assertIn("Model warning: extra_fields=自定义", stdout)
        self.assertIn("Model verify: status=exact", stdout)

    def test_each_component_difference_is_reported_by_strict_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            targets = {
                "front": (root / "front.html").read_text(encoding="utf-8"),
                "back": (root / "back.html").read_text(encoding="utf-8"),
                "css": (root / "style.css").read_text(encoding="utf-8"),
            }

            for changed in ("front", "back", "css"):
                with self.subTest(changed=changed):
                    current = dict(targets)
                    current[changed] += " /* strict difference */"
                    client = MissingModelClient()
                    client.set_existing(fields=fields, **current)

                    code, stdout, stderr = run_import_cli(
                        [
                            "--input",
                            str(input_path),
                            "--model-spec",
                            str(model_spec),
                            "--dry-run",
                        ],
                        client,
                    )

                    self.assertEqual(code, 0, stderr)
                    self.assertIn("Model preflight: action=update", stdout)
                    self.assertIn(f"{changed}=change", stdout)
                    for unchanged in {"front", "back", "css"} - {changed}:
                        self.assertIn(f"{unchanged}=exact", stdout)

    def test_incompatible_model_is_blocked_with_count_and_migration_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front="unused",
                back="unused",
                css=(root / "style.css").read_text(encoding="utf-8"),
            )
            client.templates = {"Chunk Anchor": {}, "Chunk Recall": {}}

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertIn("Model preflight: action=blocked", stdout)
        self.assertIn("Model migration: note_count=2", stdout)
        self.assertIn("back up the complete Anki collection", stdout)
        self.assertIn("delete old TRVS-Lab notes", stdout)
        self.assertIn("delete the old TRVS-Lab note type", stdout)
        self.assertIn("requires the reported manual migration", stderr)
        self.assertFalse(
            {"modelFieldAdd", "updateModelTemplates", "updateModelStyling"}
            & set(client.actions)
        )
        prepare_audio.assert_not_called()

    def test_shared_lock_conflict_stops_before_model_or_audio_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            client = MissingModelClient()
            model_contract.MODEL_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

            with model_contract.MODEL_LOCK_PATH.open("a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.object(
                    ankiconnect_import, "prepare_all_audio"
                ) as prepare_audio:
                    code, stdout, stderr = run_import_cli(
                        [
                            "--input",
                            str(input_path),
                            "--model-spec",
                            str(model_spec),
                            "--no-sync",
                        ],
                        client,
                    )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("already running", stderr)
        self.assertNotIn("modelNames", client.actions)
        self.assertNotIn("createModel", client.actions)
        prepare_audio.assert_not_called()

    def test_no_ensure_model_flag_is_rejected_before_connecting_or_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            client = MissingModelClient()

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                        "--no-ensure-model",
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("--no-ensure-model is no longer supported", stderr)
        self.assertEqual(client.actions, [])
        prepare_audio.assert_not_called()

    def test_invalid_model_spec_stops_before_connecting_or_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            invalid_spec = root / "invalid.json"
            invalid_spec.write_text("{}", encoding="utf-8")
            client = MissingModelClient()

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(invalid_spec),
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("model spec name must be", stderr)
        self.assertNotIn("{", stderr)
        self.assertEqual(client.actions, [])
        prepare_audio.assert_not_called()

    def test_unreadable_template_file_stops_before_connecting_or_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            (root / "front.html").write_bytes(b"\xff")
            client = MissingModelClient()

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("model spec FrontPath cannot be read", stderr)
        self.assertEqual(client.actions, [])
        prepare_audio.assert_not_called()

    def test_partial_model_update_failure_is_reported_without_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            target_front = (root / "front.html").read_text(encoding="utf-8")
            target_back = (root / "back.html").read_text(encoding="utf-8")
            target_css = (root / "style.css").read_text(encoding="utf-8")
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front=target_front + "changed",
                back=target_back,
                css=target_css + "changed",
            )
            client.fail_action = "updateModelStyling"

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                        "--no-sync",
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertIn("Model update: completed=templates failed=css", stdout)
        self.assertIn("model update failed at css", stderr)
        self.assertEqual(
            client.templates["Context Anchor"]["Front"], target_front
        )
        self.assertNotEqual(client.css, target_css)
        self.assertNotIn("sync", client.actions)
        prepare_audio.assert_not_called()

    def test_post_update_verification_failure_stops_before_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front=(root / "front.html").read_text(encoding="utf-8") + "changed",
                back=(root / "back.html").read_text(encoding="utf-8"),
                css=(root / "style.css").read_text(encoding="utf-8"),
            )
            client.ignore_actions.add("updateModelTemplates")

            with mock.patch.object(
                ankiconnect_import, "prepare_all_audio"
            ) as prepare_audio:
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                        "--no-sync",
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertIn("Model verify: status=mismatch components=front", stdout)
        self.assertIn("model verification failed", stderr)
        self.assertNotIn("sync", client.actions)
        prepare_audio.assert_not_called()

    def test_verified_model_update_remains_when_audio_later_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            fields = json.loads(model_spec.read_text(encoding="utf-8"))["fields"]
            target_front = (root / "front.html").read_text(encoding="utf-8")
            client = MissingModelClient()
            client.set_existing(
                fields=fields,
                front="old front",
                back=(root / "back.html").read_text(encoding="utf-8"),
                css=(root / "style.css").read_text(encoding="utf-8"),
            )

            with (
                mock.patch.object(
                    ankiconnect_import, "reuse_existing_anki_audio"
                ),
                mock.patch.object(
                    ankiconnect_import,
                    "prepare_all_audio",
                    side_effect=ankiconnect_import.AnkiImportError(
                        "forced audio failure"
                    ),
                ),
            ):
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                    ],
                    client,
                )

        self.assertEqual(code, 1)
        self.assertIn("Model verify: status=exact", stdout)
        self.assertIn("forced audio failure", stderr)
        self.assertEqual(
            client.templates["Context Anchor"]["Front"], target_front
        )
        self.assertNotIn("sync", client.actions)

    def test_successful_import_syncs_only_after_model_and_audio_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            events: list[str] = []
            client = MissingModelClient(events)

            def prepare_audio(*_: object, **__: object) -> dict[str, Path]:
                events.append("prepare_audio")
                return {}

            with (
                mock.patch.object(
                    ankiconnect_import, "reuse_existing_anki_audio"
                ),
                mock.patch.object(
                    ankiconnect_import,
                    "prepare_all_audio",
                    side_effect=prepare_audio,
                ),
            ):
                code, stdout, stderr = run_import_cli(
                    [
                        "--input",
                        str(input_path),
                        "--model-spec",
                        str(model_spec),
                    ],
                    client,
                )

        self.assertEqual(code, 0, stderr)
        self.assertLess(events.index("createModel"), events.index("prepare_audio"))
        self.assertEqual(events[-1], "sync")
        self.assertIn("Triggered Anki sync.", stdout)

    def test_wrong_template_name_and_legacy_fields_are_both_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "notes.json"
            input_path.write_text(
                json.dumps([{"word": "anchor", "learning_group": "learn"}]),
                encoding="utf-8",
            )
            model_spec = write_model_spec(root)
            expected_fields = json.loads(model_spec.read_text(encoding="utf-8"))[
                "fields"
            ]

            cases = (
                ({"Card 1": {}}, expected_fields, "card templates are Card 1"),
                (
                    {
                        "Context Anchor": {
                            "Front": (root / "front.html").read_text(encoding="utf-8"),
                            "Back": (root / "back.html").read_text(encoding="utf-8"),
                        }
                    },
                    [*expected_fields, "学习标记", "释义", "词根", "例句"],
                    "legacy fields remain: 例句, 学习标记, 词根, 释义",
                ),
            )
            for templates, fields, expected_issue in cases:
                with self.subTest(expected_issue=expected_issue):
                    client = MissingModelClient()
                    client.set_existing(
                        fields=fields,
                        front="unused",
                        back="unused",
                        css=(root / "style.css").read_text(encoding="utf-8"),
                    )
                    client.templates = templates

                    code, stdout, stderr = run_import_cli(
                        [
                            "--input",
                            str(input_path),
                            "--model-spec",
                            str(model_spec),
                            "--dry-run",
                        ],
                        client,
                    )

                    self.assertEqual(code, 1, stderr)
                    self.assertIn("Model preflight: action=blocked", stdout)
                    self.assertIn(expected_issue, stdout)
                    self.assertFalse(
                        {
                            "modelFieldAdd",
                            "updateModelTemplates",
                            "updateModelStyling",
                        }
                        & set(client.actions)
                    )


if __name__ == "__main__":
    unittest.main()
