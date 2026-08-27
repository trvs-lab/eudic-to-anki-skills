from __future__ import annotations

import contextlib
import csv
import fcntl
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "eudic-to-anki" / "scripts" / "eudic_export.py"

spec = importlib.util.spec_from_file_location("eudic_export_safety", SCRIPT)
assert spec is not None and spec.loader is not None
eudic_export = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = eudic_export
spec.loader.exec_module(eudic_export)


class FakeResponse:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class FakeClock:
    def __init__(
        self,
        start_utc: datetime = datetime(2026, 8, 10, tzinfo=timezone.utc),
    ) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self.start_utc = start_utc

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def utc_now(self) -> datetime:
        return self.start_utc + timedelta(seconds=self.now)


def http_error(
    code: int,
    payload: dict[str, object],
    *,
    retry_after: str | None = None,
) -> urllib.error.HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(
        "https://api.frdic.com/test",
        code,
        "error",
        headers,
        io.BytesIO(json.dumps(payload).encode("utf-8")),
    )


class EudicExportSafetyTests(unittest.TestCase):
    def run_main(
        self,
        args: list[str],
        *,
        lock_path: Path,
        urlopen: object,
        clock: FakeClock | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, "argv", [str(SCRIPT), *args]))
            stack.enter_context(
                mock.patch.object(
                    eudic_export, "EXPORT_LOCK_PATH", lock_path, create=True
                )
            )
            stack.enter_context(
                mock.patch.object(eudic_export.urllib.request, "urlopen", urlopen)
            )
            if clock is not None:
                stack.enter_context(
                    mock.patch.object(
                        eudic_export,
                        "REQUEST_TIME_SOURCE",
                        eudic_export.RequestTimeSource(
                            monotonic=clock.monotonic,
                            sleep=clock.sleep,
                            utc_now=clock.utc_now,
                        ),
                        create=True,
                    )
                )
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            result = eudic_export.main()
        return result, stdout.getvalue(), stderr.getvalue()

    def test_second_export_stops_before_any_http_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "shared-export.lock"
            lock_path.touch()
            calls: list[object] = []

            def fake_urlopen(request: object, **_: object) -> FakeResponse:
                calls.append(request)
                return FakeResponse({"data": []})

            with lock_path.open("a+") as holder:
                fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                result, _, stderr = self.run_main(
                    ["--token", "test-token", "--list-categories"],
                    lock_path=lock_path,
                    urlopen=fake_urlopen,
                )

            self.assertEqual(result, 1)
            self.assertEqual(calls, [])
            self.assertIn("already running", stderr)
            self.assertIn("single date-range command", stderr)

    def test_one_range_invocation_paces_five_requests_for_four_categories(self) -> None:
        clock = FakeClock()
        starts: list[float] = []

        def fake_urlopen(request: object, **_: object) -> FakeResponse:
            starts.append(clock.now)
            url = getattr(request, "full_url")
            if "/studylist/category" in url:
                return FakeResponse(
                    {
                        "data": [
                            {
                                "id": str(index),
                                "language": "en",
                                "name": f"List {index}",
                            }
                            for index in range(1, 5)
                        ]
                    }
                )
            return FakeResponse(
                {
                    "data": [
                        {
                            "word": "anchor",
                            "add_time": "2026-08-05T10:00:00Z",
                            "context_line": "A stable context anchors the word.",
                        }
                    ]
                }
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "week.csv"
            result, stdout, stderr = self.run_main(
                [
                    "--token",
                    "test-token",
                    "--all-categories",
                    "--start-date",
                    "2026-08-04",
                    "--end-date",
                    "2026-08-10",
                    "--timezone",
                    "UTC",
                    "--output",
                    str(output),
                ],
                lock_path=tmp_path / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

            self.assertEqual(result, 0, stderr)
            self.assertTrue(output.exists())
            rows = list(csv.DictReader(io.StringIO(output.read_text(encoding="utf-8"))))
            self.assertEqual([row["language"] for row in rows], ["en"] * 4)
            self.assertEqual(rows[0]["word"], "anchor")
            self.assertEqual(len(starts), 5)
            self.assertTrue(
                all(
                    later - earlier >= 2.4 - 1e-9
                    for earlier, later in zip(starts, starts[1:])
                )
            )
            self.assertIn(
                "Request stats: categories=1, word_pages=4, retries=0, total=5",
                stdout,
            )

    def test_429_with_retry_after_retries_current_request_once(self) -> None:
        clock = FakeClock()
        calls = 0

        def fake_urlopen(_: object, **__: object) -> FakeResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise http_error(
                    429,
                    {"message": "Too many requests"},
                    retry_after="5",
                )
            return FakeResponse({"data": []})

        with tempfile.TemporaryDirectory() as tmp:
            result, stdout, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=Path(tmp) / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(calls, 2)
        self.assertEqual(clock.sleeps, [5.0])
        self.assertIn(
            "Request stats: categories=1, word_pages=0, retries=1, total=2",
            stdout,
        )

    def test_rate_limited_403_with_http_date_obeys_pacing_and_retries(self) -> None:
        clock = FakeClock()
        calls = 0

        def fake_urlopen(_: object, **__: object) -> FakeResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise http_error(
                    403,
                    {"message": "访问过于频繁"},
                    retry_after="Mon, 10 Aug 2026 00:00:01 GMT",
                )
            return FakeResponse({"data": []})

        with tempfile.TemporaryDirectory() as tmp:
            result, _, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=Path(tmp) / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(calls, 2)
        self.assertEqual(clock.sleeps, [1.0, 1.4])

    def test_plain_403_is_not_retried_even_with_retry_after(self) -> None:
        clock = FakeClock()
        calls = 0

        def fake_urlopen(_: object, **__: object) -> FakeResponse:
            nonlocal calls
            calls += 1
            raise http_error(
                403,
                {"message": "Invalid authorization token"},
                retry_after="10",
            )

        with tempfile.TemporaryDirectory() as tmp:
            result, _, stderr = self.run_main(
                ["--token", "secret-test-token", "--list-categories"],
                lock_path=Path(tmp) / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

        self.assertEqual(result, 1)
        self.assertEqual(calls, 1)
        self.assertEqual(clock.sleeps, [])
        self.assertIn("HTTP 403", stderr)
        self.assertNotIn("secret-test-token", stderr)
        self.assertIn(
            "Request stats: categories=1, word_pages=0, retries=0, total=1",
            stderr,
        )

    def test_rate_limited_403_detects_detail_beside_generic_message(self) -> None:
        clock = FakeClock()
        calls = 0

        def fake_urlopen(_: object, **__: object) -> FakeResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise http_error(
                    403,
                    {
                        "message": "Forbidden",
                        "detail": "Too many requests; access is temporarily limited",
                    },
                    retry_after="0",
                )
            return FakeResponse({"data": []})

        with tempfile.TemporaryDirectory() as tmp:
            result, stdout, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=Path(tmp) / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(calls, 2)
        self.assertIn(
            "Request stats: categories=1, word_pages=0, retries=1, total=2",
            stdout,
        )

    def test_invalid_retry_after_stops_without_guessing(self) -> None:
        invalid_values = (None, "not-a-delay", "-1", "121")
        for retry_after in invalid_values:
            with self.subTest(retry_after=retry_after):
                clock = FakeClock()
                calls = 0

                def fake_urlopen(_: object, **__: object) -> FakeResponse:
                    nonlocal calls
                    calls += 1
                    raise http_error(
                        429,
                        {"message": "Too many requests"},
                        retry_after=retry_after,
                    )

                with tempfile.TemporaryDirectory() as tmp:
                    result, _, stderr = self.run_main(
                        ["--token", "test-token", "--list-categories"],
                        lock_path=Path(tmp) / "export.lock",
                        urlopen=fake_urlopen,
                        clock=clock,
                    )

                self.assertEqual(result, 1)
                self.assertEqual(calls, 1)
                self.assertEqual(clock.sleeps, [])
                self.assertIn("valid Retry-After", stderr)

    def test_failed_retry_stops_later_categories_and_preserves_existing_output(
        self,
    ) -> None:
        clock = FakeClock()
        calls = 0

        def fake_urlopen(_: object, **__: object) -> FakeResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                return FakeResponse(
                    {
                        "data": [
                            {"id": "1", "language": "en", "name": "First"},
                            {"id": "2", "language": "en", "name": "Second"},
                        ]
                    }
                )
            raise http_error(
                429,
                {"message": "Too many requests"},
                retry_after="0",
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "week.csv"
            output.write_text("previous complete export\n", encoding="utf-8")
            result, _, stderr = self.run_main(
                [
                    "--token",
                    "test-token",
                    "--all-categories",
                    "--output",
                    str(output),
                ],
                lock_path=tmp_path / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

            self.assertEqual(result, 1)
            self.assertEqual(calls, 3)
            self.assertEqual(
                output.read_text(encoding="utf-8"), "previous complete export\n"
            )
            self.assertIn("single allowed rate-limit retry failed", stderr)
            self.assertIn(
                "Request stats: categories=1, word_pages=1, retries=1, total=3",
                stderr,
            )

    def test_output_write_failure_is_atomic_and_releases_lock(self) -> None:
        clock = FakeClock()

        def successful_urlopen(request: object, **_: object) -> FakeResponse:
            url = getattr(request, "full_url")
            if "/studylist/category" in url:
                return FakeResponse(
                    {"data": [{"id": "1", "language": "en", "name": "Main"}]}
                )
            return FakeResponse(
                {
                    "data": [
                        {
                            "word": "atomic",
                            "add_time": "2026-08-05T10:00:00Z",
                        }
                    ]
                }
            )

        def broken_dump(_: object, handle: object, **__: object) -> None:
            getattr(handle, "write")("partial")
            raise OSError("disk interrupted")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lock_path = tmp_path / "export.lock"
            output = tmp_path / "week.json"
            output.write_text("previous complete export\n", encoding="utf-8")
            with mock.patch.object(eudic_export.json, "dump", broken_dump):
                result, _, stderr = self.run_main(
                    [
                        "--token",
                        "test-token",
                        "--all-categories",
                        "--format",
                        "json",
                        "--output",
                        str(output),
                    ],
                    lock_path=lock_path,
                    urlopen=successful_urlopen,
                    clock=clock,
                )

            self.assertEqual(result, 1)
            self.assertEqual(
                output.read_text(encoding="utf-8"), "previous complete export\n"
            )
            self.assertEqual(
                [path for path in tmp_path.iterdir() if path.name.startswith(".week.json")],
                [],
            )
            self.assertIn("write", stderr.casefold())
            self.assertIn(
                "Request stats: categories=1, word_pages=1, retries=0, total=2",
                stderr,
            )

            result, _, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=lock_path,
                urlopen=lambda *_args, **_kwargs: FakeResponse({"data": []}),
                clock=clock,
            )
            self.assertEqual(result, 0, stderr)

    def test_invalid_encounter_timestamp_stops_cleanly_without_output(self) -> None:
        clock = FakeClock()

        def fake_urlopen(request: object, **_: object) -> FakeResponse:
            url = getattr(request, "full_url")
            if "/studylist/category" in url:
                return FakeResponse(
                    {"data": [{"id": "1", "language": "en", "name": "Main"}]}
                )
            return FakeResponse(
                {"data": [{"word": "broken", "add_time": "not-a-timestamp"}]}
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "week.csv"
            result, _, stderr = self.run_main(
                [
                    "--token",
                    "test-token",
                    "--all-categories",
                    "--output",
                    str(output),
                ],
                lock_path=tmp_path / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

            self.assertEqual(result, 1)
            self.assertFalse(output.exists())
            self.assertIn("timestamp", stderr.casefold())
            self.assertIn(
                "Request stats: categories=1, word_pages=1, retries=0, total=2",
                stderr,
            )

    def test_zero_based_pagination_and_json_contract_remain_compatible(self) -> None:
        clock = FakeClock()
        requested_urls: list[str] = []

        def fake_urlopen(request: object, **_: object) -> FakeResponse:
            url = getattr(request, "full_url")
            requested_urls.append(url)
            if "/studylist/category" in url:
                return FakeResponse(
                    {"data": [{"id": "1", "language": "en", "name": "Main"}]}
                )
            if "page=1" in url:
                return FakeResponse({"data": []})
            return FakeResponse(
                {
                    "data": [
                        {
                            "word": "context",
                            "phon": "kɒntekst",
                            "exp": "the situation in which something happens",
                            "add_time": "2026-08-05T10:00:00Z",
                            "star": 1,
                            "context_line": "Context makes a new word easier to retain.",
                        }
                    ]
                }
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "day.json"
            result, stdout, stderr = self.run_main(
                [
                    "--token",
                    "test-token",
                    "--all-categories",
                    "--start-date",
                    "2026-08-05",
                    "--end-date",
                    "2026-08-05",
                    "--timezone",
                    "UTC",
                    "--format",
                    "json",
                    "--output",
                    str(output),
                ],
                lock_path=tmp_path / "export.lock",
                urlopen=fake_urlopen,
                clock=clock,
            )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["start_date"], "2026-08-05")
            self.assertEqual(payload["meta"]["end_date"], "2026-08-05")
            self.assertEqual(payload["data"][0]["word"], "context")
            self.assertEqual(
                payload["data"][0]["context_line"],
                "Context makes a new word easier to retain.",
            )
            self.assertEqual(len(requested_urls), 3)
            self.assertIn("page=1", requested_urls[1])
            self.assertIn("page=0", requested_urls[2])
            self.assertIn(
                "Request stats: categories=1, word_pages=2, retries=0, total=3",
                stdout,
            )

    def test_api_failure_releases_lock_for_next_export(self) -> None:
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "export.lock"
            result, _, _ = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=lock_path,
                urlopen=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    http_error(403, {"message": "Invalid authorization token"})
                ),
                clock=clock,
            )
            self.assertEqual(result, 1)

            result, _, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=lock_path,
                urlopen=lambda *_args, **_kwargs: FakeResponse({"data": []}),
                clock=clock,
            )
            self.assertEqual(result, 0, stderr)

    def test_unhandled_exception_still_releases_lock(self) -> None:
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "export.lock"
            result, _, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=lock_path,
                urlopen=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("unexpected boundary failure with secret detail")
                ),
                clock=clock,
            )
            self.assertEqual(result, 1)
            self.assertIn("Unexpected export failure (RuntimeError)", stderr)
            self.assertNotIn("secret detail", stderr)
            self.assertIn(
                "Request stats: categories=1, word_pages=0, retries=0, total=1",
                stderr,
            )

            result, _, stderr = self.run_main(
                ["--token", "test-token", "--list-categories"],
                lock_path=lock_path,
                urlopen=lambda *_args, **_kwargs: FakeResponse({"data": []}),
                clock=clock,
            )
            self.assertEqual(result, 0, stderr)


if __name__ == "__main__":
    unittest.main()
