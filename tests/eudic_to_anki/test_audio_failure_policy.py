from __future__ import annotations

import base64
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .fixtures import VALID_MP3_BYTES

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
    def test_mp3_validation_requires_complete_audio_frames(self) -> None:
        id3_header = b"ID3\x04\x00\x00\x00\x00\x00\x00"
        for data in (b"ID3x", id3_header, VALID_MP3_BYTES[:-1], b"\xff\xfb\x00\x00"):
            with self.subTest(data=data[:10]):
                with self.assertRaises(ankiconnect_import.AnkiImportError):
                    ankiconnect_import._validate_mp3_bytes(data, word="anchor", source="test")
        for data in (VALID_MP3_BYTES, id3_header + VALID_MP3_BYTES, VALID_MP3_BYTES + b"TAG" + bytes(125)):
            ankiconnect_import._validate_mp3_bytes(data, word="anchor", source="test")

    def test_existing_anki_sound_is_reused_without_generation(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "findNotes":
                    return [1]
                if action == "notesInfo":
                    return [{"fields": {"发音": {"value": "[sound:inflict.mp3]"}}}]
                if action == "retrieveMediaFile":
                    return base64.b64encode(VALID_MP3_BYTES).decode("ascii")
                raise AssertionError(action)

        note = {
            "word": "inflict",
            "learning_group": "learn",
            "audio_html": "",
        }
        ankiconnect_import.reuse_existing_anki_audio(Client(), [note], model="TRVS-Lab")
        self.assertEqual(note["audio_html"], "[sound:inflict.mp3]")

        with mock.patch.object(
            ankiconnect_import, "generate_audio_with_command"
        ) as generate:
            prepared = ankiconnect_import.prepare_all_audio(
                [note],
                provider="command",
                command_template=(
                    "python3 scripts/edge_tts_runner.py --text {text} "
                    "--output {output} --voice {voice}"
                ),
                audio_dir=Path("unused"),
                audio_format="mp3",
                voice="en-US-GuyNeural",
            )
        self.assertEqual(prepared, {})
        generate.assert_not_called()

    def test_transient_failure_retries_once_with_same_command_and_voice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "inflict.mp3"
            calls: list[list[str]] = []

            def fake_run(command: list[str], **_: object) -> object:
                calls.append(command)
                if len(calls) == 1:
                    raise subprocess.CalledProcessError(1, command, stderr="temporary")
                output.write_bytes(VALID_MP3_BYTES)
                return object()

            with mock.patch.object(ankiconnect_import.subprocess, "run", fake_run):
                result = ankiconnect_import.generate_audio_with_command(
                    command_template=(
                        "python3 scripts/edge_tts_runner.py --text {text} "
                        "--output {output} --voice {voice}"
                    ),
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
                        command_template=(
                            "python3 scripts/edge_tts_runner.py --output {output} "
                            "--voice {voice}"
                        ),
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
                        command_template=(
                            "python3 scripts/edge_tts_runner.py --output {output} "
                            "--voice {voice}"
                        ),
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
                    command_template=(
                        "python3 scripts/edge_tts_runner.py {unknown} --voice {voice}"
                    ),
                    word="inflict",
                    text="inflict",
                    output_path=Path("unused.mp3"),
                    voice="en-US-GuyNeural",
                )
        run.assert_not_called()

    def test_alternate_tts_provider_is_rejected_before_execution(self) -> None:
        with mock.patch.object(ankiconnect_import.subprocess, "run") as run:
            with self.assertRaisesRegex(
                ankiconnect_import.AnkiImportError,
                "alternate TTS providers",
            ):
                ankiconnect_import.generate_audio_with_command(
                    command_template="say {text} --voice {voice}",
                    word="inflict",
                    text="inflict",
                    output_path=Path("unused.mp3"),
                    voice="en-US-GuyNeural",
                )
        run.assert_not_called()

    def test_invalid_existing_media_is_not_treated_as_reusable_audio(self) -> None:
        class Client:
            def invoke(self, action: str, **_: object) -> object:
                if action == "findNotes":
                    return [1]
                if action == "notesInfo":
                    return [
                        {
                            "fields": {
                                "发音": {"value": "[sound:broken.mp3]"},
                                "遇见记录": {
                                    "value": '[{"id":"same","at":"2026-08-10"}]'
                                },
                            }
                        }
                    ]
                if action == "retrieveMediaFile":
                    return base64.b64encode(b"broken").decode("ascii")
                raise AssertionError(action)

        note = {
            "word": "inflict",
            "learning_group": "learn",
            "audio_html": "",
            "encounter_id": "same",
        }
        ankiconnect_import.reuse_existing_anki_audio(Client(), [note], model="TRVS-Lab")
        self.assertEqual(note["audio_html"], "")
        self.assertTrue(note["_repair_audio"])
        self.assertNotIn("_idempotent_encounter", note)
        with self.assertRaisesRegex(
            ankiconnect_import.AnkiImportError, "No valid audio"
        ):
            ankiconnect_import.prepare_all_audio(
                [note],
                provider="none",
                command_template=None,
                audio_dir=Path("unused"),
                audio_format="mp3",
                voice="en-US-GuyNeural",
            )


if __name__ == "__main__":
    unittest.main()
