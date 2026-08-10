from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import_audio", SCRIPTS / "ankiconnect_import.py"
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class AudioFailurePolicyTests(unittest.TestCase):
    def test_existing_anki_sound_is_reused_without_generation(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "findNotes":
                    return [1]
                if action == "notesInfo":
                    return [{"fields": {"发音": {"value": "[sound:inflict.mp3]"}}}]
                raise AssertionError(action)

        note = {
            "word": "inflict",
            "learning_group": "learn",
            "audio_html": "",
        }
        ankiconnect_import.reuse_existing_anki_audio(Client(), [note], model="TRVS-Lab")
        self.assertEqual(note["audio_html"], "[sound:inflict.mp3]")

    def test_transient_failure_retries_once_with_same_command_and_voice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "inflict.mp3"
            calls: list[list[str]] = []

            def fake_run(command: list[str], **_: object) -> object:
                calls.append(command)
                if len(calls) == 1:
                    raise subprocess.CalledProcessError(1, command, stderr="temporary")
                output.write_bytes(b"ID3audio")
                return object()

            with mock.patch.object(ankiconnect_import.subprocess, "run", fake_run):
                result = ankiconnect_import.generate_audio_with_command(
                    command_template="edge-runner --text {text} --output {output} --voice {voice}",
                    word="inflict",
                    text="inflict",
                    output_path=output,
                    voice="en-US-GuyNeural",
                )

            self.assertEqual(result, output)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0], calls[1])
            self.assertIn("en-US-GuyNeural", calls[0])

    def test_second_failure_aborts_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "inflict.mp3"
            with mock.patch.object(
                ankiconnect_import.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(
                    1, ["edge-runner"], stderr="service unavailable"
                ),
            ) as run:
                with self.assertRaisesRegex(
                    ankiconnect_import.AnkiImportError,
                    r"service=edge-tts.*word='inflict'.*voice='en-US-GuyNeural'.*attempts=2",
                ):
                    ankiconnect_import.generate_audio_with_command(
                        command_template="edge-runner --output {output} --voice {voice}",
                        word="inflict",
                        text="inflict",
                        output_path=output,
                        voice="en-US-GuyNeural",
                    )
            self.assertEqual(run.call_count, 2)

    def test_invalid_mp3_is_retried_then_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "inflict.mp3"

            def fake_run(*_: object, **__: object) -> object:
                output.write_bytes(b"not an mp3")
                return object()

            with mock.patch.object(ankiconnect_import.subprocess, "run", fake_run):
                with self.assertRaisesRegex(
                    ankiconnect_import.AnkiImportError, "attempts=2"
                ):
                    ankiconnect_import.generate_audio_with_command(
                        command_template="edge-runner --output {output}",
                        word="inflict",
                        text="inflict",
                        output_path=output,
                        voice="en-US-GuyNeural",
                    )

    def test_configuration_error_does_not_invoke_any_service(self) -> None:
        with mock.patch.object(ankiconnect_import.subprocess, "run") as run:
            with self.assertRaisesRegex(
                ankiconnect_import.AnkiImportError,
                "Unsupported --audio-command placeholder",
            ):
                ankiconnect_import.generate_audio_with_command(
                    command_template="edge-runner {unknown}",
                    word="inflict",
                    text="inflict",
                    output_path=Path("unused.mp3"),
                    voice="en-US-GuyNeural",
                )
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
