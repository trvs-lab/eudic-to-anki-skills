from __future__ import annotations

import contextlib
import base64
import copy
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

from .fixtures import VALID_MP3_BYTES
from .test_eudic_export_safety import FakeClock, FakeResponse, http_error
from .test_trvs_model_sync import (
    MissingModelClient,
    SCRIPTS,
    ankiconnect_import as anki,
    model_contract,
    run_import_cli,
    write_import_input,
    write_model_spec,
)

import eudic_export

cleanup = anki.eudic_cleanup


class EudicCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.model_spec = write_model_spec(self.root)
        self.input_path = write_import_input(self.root)
        self.template = json.loads(self.input_path.read_text())[0]
        self.client = MissingModelClient()
        self.requests = []
        self.verification_words = []
        self.clock = FakeClock()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            mock.patch.dict(
                os.environ,
                {
                    "EUDIC_TOKEN": "test-only-token",
                    "EUDIC_TO_ANKI_TEMP_DIR": str(self.artifacts),
                },
            )
        )
        self.stack.enter_context(
            mock.patch.object(
                model_contract, "MODEL_LOCK_PATH", self.root / "anki.lock"
            )
        )
        self.stack.enter_context(
            mock.patch.object(
                eudic_export, "EXPORT_LOCK_PATH", self.root / "eudic.lock"
            )
        )
        self.stack.enter_context(
            mock.patch.object(
                cleanup,
                "REQUEST_TIME_SOURCE",
                eudic_export.RequestTimeSource(
                    monotonic=self.clock.monotonic,
                    sleep=self.clock.sleep,
                    utc_now=self.clock.utc_now,
                ),
            )
        )
        self.transport = self.stack.enter_context(
            mock.patch.object(
                eudic_export.urllib.request,
                "urlopen",
                side_effect=self.accept_delete,
            )
        )

    def entry(
        self,
        word: str = "anchor",
        *,
        category: str = "book-1",
        group: str = "learn",
        **overrides: object,
    ) -> dict:
        note = copy.deepcopy(self.template)
        note.update(
            {
                "word": word,
                "category_id": category,
                "learning_group": group,
                "encounter_id": f"{category}-{word}",
                "eudic_source": {
                    "language": "en",
                    "category_id": category,
                    "word": word,
                },
            }
        )
        note.update(overrides)
        return note

    def pending_files(self) -> list[Path]:
        return list(cleanup.pending_directory().glob("*.json"))

    def accept_delete(self, request: object, **kwargs: object) -> FakeResponse:
        if request.get_method() == "GET":
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
            self.assertEqual(
                urllib.parse.urlsplit(request.full_url).path,
                "/api/open/v1/studylist/word",
            )
            self.verification_words.append(query["word"][0])
            raise http_error(404, {"message": "word does not exist"})
        self.assertEqual(request.get_method(), "DELETE")
        self.assertEqual(kwargs["timeout"], 30)
        self.assertEqual(
            request.full_url, "https://api.frdic.com/api/open/v1/studylist/words"
        )
        self.requests.append(json.loads(request.data))
        files = self.pending_files()
        self.assertEqual(
            len(files), 1, "persist the pending work before sending DELETE"
        )
        self.assertNotIn("test-only-token", files[0].read_text())
        return FakeResponse({}, 204)

    def run_import(
        self,
        notes: list[dict],
        *,
        enabled: bool = True,
        sync: bool = False,
        extra: tuple[str, ...] = (),
    ) -> tuple[int, str, str]:
        self.input_path.write_text(json.dumps(notes), encoding="utf-8")
        argv = ["--input", str(self.input_path), "--model-spec", str(self.model_spec)]
        if enabled:
            argv.append("--cleanup-eudic")
        if not sync:
            argv.append("--no-sync")
        return run_import_cli([*argv, *extra], self.client)

    def resume(self) -> tuple[int, str, str]:
        return run_import_cli(["--resume-eudic-cleanup"], self.client)

    def test_complete_batch_deletes_only_exact_source_targets_without_sync_or_freshness_reads(
        self,
    ) -> None:
        first = self.entry("Anchor")
        second = self.entry("anchor", category="book-2")
        notes = [
            first,
            second,
            self.entry("later", group="defer"),
            self.entry("low", group="skip"),
            self.entry("garbage", group="reject"),
            self.entry("manual", eudic_source=None),
        ]
        code, stdout, stderr = self.run_import(notes)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            self.requests,
            [
                {
                    "language": "en",
                    "category_id": "book-1",
                    "words": ["Anchor", "later", "low"],
                },
                {
                    "language": "en",
                    "category_id": "book-1",
                    "words": ["Anchor", "later", "low"],
                },
                {"language": "en", "category_id": "book-2", "words": ["anchor"]},
                {"language": "en", "category_id": "book-2", "words": ["anchor"]},
            ],
        )
        self.assertEqual(self.verification_words, ["Anchor", "later", "low", "anchor"])
        self.assertEqual(len(self.client.notes), 4)
        self.assertNotIn("sync", self.client.actions)
        self.assertIn("deleted=4", stdout)
        self.assertEqual(self.pending_files(), [])
        self.assertEqual(self.clock.sleeps, [2.4] * 7)

    def test_reject_sharing_a_delete_target_keeps_that_source_word(self) -> None:
        code, _, stderr = self.run_import(
            [self.entry(), self.entry(group="reject", encounter_id="rejected")]
        )
        self.assertEqual(code, 0, stderr)
        self.transport.assert_not_called()
        self.assertEqual(self.pending_files(), [])

    def test_partial_anki_import_failure_never_queues_or_deletes_any_word(self) -> None:
        invoke = self.client.invoke

        def fail_second_note(action: str, **params: object) -> object:
            if action == "addNote" and self.client.notes:
                raise anki.AnkiImportError("second note failed")
            return invoke(action, **params)

        with mock.patch.object(self.client, "invoke", side_effect=fail_second_note):
            code, _, stderr = self.run_import([self.entry(), self.entry("second")])
        self.assertEqual(code, 1)
        self.assertIn("second note failed", stderr)
        self.assertEqual(len(self.client.notes), 1)
        self.transport.assert_not_called()
        self.assertEqual(self.pending_files(), [])

    def test_post_write_field_card_or_audio_failure_blocks_the_whole_cleanup(
        self,
    ) -> None:
        for fault in ("field", "encounter", "card", "audio"):
            with self.subTest(fault=fault):
                self.client = MissingModelClient()
                invoke = self.client.invoke

                def corrupt_write(action: str, **params: object) -> object:
                    result = invoke(action, **params)
                    if action == "addNote":
                        saved = self.client.notes[result]
                        if fault == "field":
                            saved["fields"]["英英"] = "a different nonempty definition"
                        elif fault == "encounter":
                            saved["fields"]["遇见记录"] = "[]"
                        elif fault == "card":
                            saved["deck"] = "words::skip"
                        else:
                            self.client.media.clear()
                    return result

                with mock.patch.object(
                    self.client, "invoke", side_effect=corrupt_write
                ):
                    code, _, _ = self.run_import([self.entry()], sync=True)
                self.assertEqual(code, 1)
                self.transport.assert_not_called()
                self.assertEqual(self.pending_files(), [])
                self.assertNotIn("sync", self.client.actions)

    def test_failed_media_upload_is_detected_by_reading_stored_audio(self) -> None:
        audio = self.root / "input.mp3"
        audio.write_bytes(VALID_MP3_BYTES)
        self.client.media.clear()
        self.client.ignore_actions.add("storeMediaFile")
        code, _, stderr = self.run_import(
            [self.entry(audio_html="", audio_path=str(audio))],
            extra=("--audio-provider", "existing"),
        )
        self.assertEqual(code, 1)
        self.assertIn("stored audio verification failed", stderr)
        self.transport.assert_not_called()

    def test_existing_identical_encounter_can_be_deleted_without_reset(self) -> None:
        notes = [self.entry()]
        self.assertEqual(self.run_import(notes, enabled=False)[0], 0)
        self.client.actions.clear()
        code, _, stderr = self.run_import(notes)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.verification_words, ["anchor"])
        self.assertFalse(
            {"addNote", "updateNote", "forgetCards", "changeDeck"}.intersection(
                self.client.actions
            )
        )

    def test_existing_cards_manually_moved_to_skip_remain_authoritative(self) -> None:
        notes = [self.entry()]
        self.assertEqual(self.run_import(notes, enabled=False)[0], 0)
        self.client.notes[100]["deck"] = "words::skip"
        self.client.actions.clear()
        code, _, stderr = self.run_import(notes)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.client.notes[100]["deck"], "words::skip")
        self.assertNotIn("changeDeck", self.client.actions)

    def test_large_group_deletes_in_bounded_batches(self) -> None:
        code, _, stderr = self.run_import(
            [self.entry(f"word{index}") for index in range(101)]
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            [len(body["words"]) for body in self.requests], [100, 100, 1, 1]
        )
        self.assertEqual(
            self.verification_words, ["word0", "word50", "word99", "word100"]
        )
        self.assertEqual(self.pending_files(), [])

    def test_fifty_words_use_two_deletes_and_three_sample_queries(self) -> None:
        code, _, stderr = self.run_import(
            [self.entry(f"word{index}") for index in range(50)]
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.verification_words, ["word0", "word25", "word49"])
        self.assertEqual(self.transport.call_count, 5)

    def test_preview_ping_and_unflagged_import_never_delete(self) -> None:
        self.assertEqual(self.run_import([self.entry()], extra=("--dry-run",))[0], 0)
        self.assertEqual(self.client.notes, {})
        self.assertEqual(
            run_import_cli(["--ping", "--cleanup-eudic"], self.client)[0], 0
        )
        self.assertEqual(self.run_import([self.entry()], enabled=False)[0], 0)
        self.transport.assert_not_called()
        self.assertEqual(self.pending_files(), [])

    def test_empty_import_and_preview_finish_without_any_service_calls(self) -> None:
        for extra in ((), ("--dry-run",)):
            code, stdout, stderr = self.run_import([], extra=extra)
            self.assertEqual(code, 0, stderr)
            self.assertIn("No vocabulary records", stdout)
        self.assertEqual(self.client.actions, [])
        self.transport.assert_not_called()
        self.assertEqual(self.pending_files(), [])

    def test_id3_header_without_audio_cannot_authorize_deletion(self) -> None:
        self.client.media["anchor.mp3"] = base64.b64encode(b"ID3x").decode("ascii")
        code, _, _ = self.run_import([self.entry()])
        self.assertEqual(code, 1)
        self.transport.assert_not_called()
        self.assertEqual(self.pending_files(), [])

    def test_manual_words_and_reject_only_batches_do_not_delete(self) -> None:
        for notes in ([self.entry(eudic_source=None)], [self.entry(group="reject")]):
            code, _, stderr = self.run_import(notes)
            self.assertEqual(code, 0, stderr)
        self.transport.assert_not_called()
        self.assertEqual(self.pending_files(), [])

    def test_bad_provenance_stops_before_anki_writes(self) -> None:
        code, _, _ = self.run_import(
            [
                self.entry(
                    eudic_source={
                        "language": "en",
                        "category_id": "book-1",
                        "word": "other",
                    }
                )
            ]
        )
        self.assertEqual(code, 1)
        self.assertEqual(self.client.actions, [])
        self.transport.assert_not_called()

    def test_partial_delete_retains_only_unfinished_targets_and_resume_never_reimports(
        self,
    ) -> None:
        def partial(request: object, **kwargs: object) -> FakeResponse:
            if (
                request.get_method() == "DELETE"
                and json.loads(request.data)["category_id"] == "book-2"
            ):
                raise http_error(503, {"message": "offline"})
            return self.accept_delete(request, **kwargs)

        self.transport.side_effect = partial
        code, _, stderr = self.run_import(
            [self.entry(), self.entry("second", category="book-2")], sync=True
        )
        self.assertEqual(code, 2)
        self.assertIn("Local Anki import succeeded", stderr)
        self.assertIn("sync", self.client.actions)
        files = self.pending_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(
            [item["word"] for item in json.loads(files[0].read_text())["pending"]],
            ["second"],
        )
        self.client.actions.clear()

        resumed_deletes = 0

        def resumed(request: object, **kwargs: object) -> FakeResponse:
            nonlocal resumed_deletes
            if request.get_method() == "GET":
                if resumed_deletes:
                    raise http_error(404, {"message": "word does not exist"})
                return FakeResponse(
                    {"word": "second", "category_ids": ["book-2"]}
                )
            resumed_deletes += 1
            return self.accept_delete(request, **kwargs)

        self.transport.side_effect = resumed
        code, _, stderr = self.resume()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.pending_files(), [])
        self.assertEqual(
            [body["words"] for body in self.requests],
            [["anchor"], ["anchor"], ["second"], ["second"]],
        )
        self.assertFalse(
            {"addNote", "updateNote", "forgetCards", "changeDeck", "sync"}.intersection(
                self.client.actions
            )
        )

    def test_lost_delete_response_is_reconciled_before_any_retry(self) -> None:
        self.transport.side_effect = urllib.error.URLError(
            "response lost after deletion"
        )
        self.assertEqual(self.run_import([self.entry()])[0], 2)
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(len(self.pending_files()), 1)

        def absent(request: object, **_: object) -> FakeResponse:
            self.assertEqual(request.get_method(), "GET")
            raise http_error(404, {"message": "word does not exist"})

        self.transport.side_effect = absent
        self.assertEqual(self.resume()[0], 0)
        self.assertEqual(self.pending_files(), [])

    def test_resume_after_confirmed_first_pass_runs_only_second_pass(self) -> None:
        delete_attempts = 0

        def lose_second_response(request: object, **kwargs: object) -> FakeResponse:
            nonlocal delete_attempts
            delete_attempts += 1
            if delete_attempts == 2:
                raise urllib.error.URLError("offline")
            return self.accept_delete(request, **kwargs)

        self.transport.side_effect = lose_second_response
        self.assertEqual(self.run_import([self.entry()])[0], 2)
        resumed_delete = False

        def detached_then_absent(request: object, **kwargs: object) -> FakeResponse:
            nonlocal resumed_delete
            if request.get_method() == "DELETE":
                resumed_delete = True
                return self.accept_delete(request, **kwargs)
            if resumed_delete:
                raise http_error(404, {"message": "word does not exist"})
            return FakeResponse({"word": "anchor", "category_ids": []})

        self.transport.side_effect = detached_then_absent
        code, _, stderr = self.resume()
        self.assertEqual(code, 0, stderr)
        self.assertEqual([body["words"] for body in self.requests], [["anchor"], ["anchor"]])
        self.assertEqual(self.pending_files(), [])

    def test_resume_keeps_throttling_across_pending_files(self) -> None:
        self.transport.side_effect = urllib.error.URLError("offline")
        self.assertEqual(self.run_import([self.entry()])[0], 2)
        self.assertEqual(
            self.run_import([self.entry("second", category="book-2")])[0], 2
        )
        starts = []

        deletes_by_word: dict[str, int] = {}

        def present(request: object, **_: object) -> FakeResponse:
            starts.append(self.clock.now)
            if request.get_method() == "GET":
                word = urllib.parse.parse_qs(
                    urllib.parse.urlsplit(request.full_url).query
                )["word"][0]
                if deletes_by_word.get(word, 0) >= 2:
                    raise http_error(404, {"message": "word does not exist"})
                category_id = "book-2" if word == "second" else "book-1"
                return FakeResponse({"word": word, "category_ids": [category_id]})
            word = json.loads(request.data)["words"][0]
            deletes_by_word[word] = deletes_by_word.get(word, 0) + 1
            return FakeResponse({}, 204)

        self.transport.side_effect = present
        code, _, stderr = self.resume()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(starts), 8)
        self.assertTrue(all(b - a >= 2.4 - 1e-9 for a, b in zip(starts, starts[1:])))
        self.assertEqual(self.pending_files(), [])

    def test_delete_requires_204_and_does_not_retry_rate_limits(self) -> None:
        for response in (
            FakeResponse({"message": "not deleted"}, 200),
            http_error(429, {"message": "rate limit"}, retry_after="1"),
        ):
            with self.subTest(response=response):
                self.transport.reset_mock()
                self.transport.side_effect = (
                    response
                    if isinstance(response, Exception)
                    else lambda *_a, **_k: response
                )
                code, _, _ = self.run_import([self.entry()])
                self.assertEqual(code, 2)
                self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(len(self.pending_files()), 2)

    def test_resume_revalidates_anki_before_contacting_eudic(self) -> None:
        self.transport.side_effect = urllib.error.URLError("offline")
        self.assertEqual(self.run_import([self.entry()])[0], 2)
        self.client.notes.clear()
        self.transport.reset_mock()
        self.assertEqual(self.resume()[0], 1)
        self.transport.assert_not_called()
        self.assertEqual(len(self.pending_files()), 1)

    def test_invalid_reconciliation_response_is_not_treated_as_absence(self) -> None:
        self.transport.side_effect = urllib.error.URLError("offline")
        self.assertEqual(self.run_import([self.entry()])[0], 2)

        def malformed(request: object, **_: object) -> FakeResponse:
            self.assertEqual(request.get_method(), "GET")
            return FakeResponse({"message": "something went wrong"})

        self.transport.side_effect = malformed
        code, _, stderr = self.resume()
        self.assertEqual(code, 1)
        self.assertIn("invalid word response", stderr)
        self.assertEqual(len(self.pending_files()), 1)

    def test_sample_still_present_keeps_the_whole_batch_pending(self) -> None:
        def still_present(request: object, **kwargs: object) -> FakeResponse:
            if request.get_method() == "GET":
                return FakeResponse({"word": "anchor", "category_ids": []})
            return self.accept_delete(request, **kwargs)

        self.transport.side_effect = still_present
        code, _, stderr = self.run_import([self.entry()])
        self.assertEqual(code, 2)
        self.assertIn("sampled word 'anchor' still exists", stderr)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(len(self.pending_files()), 1)

    def test_sample_query_accepts_not_found_after_rate_limit_retry(self) -> None:
        verification_attempts = 0

        def rate_limited_once(request: object, **kwargs: object) -> FakeResponse:
            nonlocal verification_attempts
            if request.get_method() == "DELETE":
                return self.accept_delete(request, **kwargs)
            verification_attempts += 1
            if verification_attempts == 1:
                raise http_error(
                    429, {"message": "rate limit"}, retry_after="0"
                )
            raise http_error(404, {"message": "word does not exist"})

        self.transport.side_effect = rate_limited_once
        code, _, stderr = self.run_import([self.entry()])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(verification_attempts, 2)
        self.assertEqual(self.pending_files(), [])

    def test_pending_storage_failure_prevents_deletion(self) -> None:
        with mock.patch.object(
            cleanup, "write_text_atomically", side_effect=OSError("disk full")
        ):
            code, _, stderr = self.run_import([self.entry()])
        self.assertEqual(code, 2)
        self.assertIn("disk full", stderr)
        self.assertEqual(len(self.client.notes), 1)
        self.transport.assert_not_called()

    def test_empty_resume_does_not_need_anki_or_eudic(self) -> None:
        self.assertEqual(self.resume()[0], 0)
        self.assertEqual(self.client.actions, [])
        self.transport.assert_not_called()

    def test_temporary_artifact_cleanup_preserves_unfinished_work(self) -> None:
        self.transport.side_effect = urllib.error.URLError("offline")
        self.assertEqual(self.run_import([self.entry()])[0], 2)
        (self.artifacts / "export.csv").write_text("old export")
        result = subprocess.run(
            ["bash", str(SCRIPTS / "cleanup_import_artifacts.sh")],
            env={
                key: value
                for key, value in os.environ.items()
                if key != "KEEP_EUDIC_IMPORT_ARTIFACTS"
            },
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.artifacts / "export.csv").exists())
        self.assertEqual(len(self.pending_files()), 1)


if __name__ == "__main__":
    unittest.main()
