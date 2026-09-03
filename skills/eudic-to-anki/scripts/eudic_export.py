#!/usr/bin/env python3
"""Export Eudic cloud study list data by date via the official OpenAPI."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import os
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


BASE_URL = "https://api.frdic.com/api/open/v1"
DEFAULT_PAGE_SIZE = 100
OPENAPI_DOC_URL = "https://my.eudic.net/OpenAPI/Authorization"
EXPORT_LOCK_PATH = Path(tempfile.gettempdir()) / "eudic-to-anki-export.lock"
REQUEST_INTERVAL_SECONDS = 2.4
MAX_RETRY_AFTER_SECONDS = 120.0


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RequestTimeSource:
    monotonic: Callable[[], float]
    sleep: Callable[[float], None]
    utc_now: Callable[[], datetime]


REQUEST_TIME_SOURCE = RequestTimeSource(
    monotonic=time.monotonic,
    sleep=time.sleep,
    utc_now=current_utc_time,
)


class ApiError(RuntimeError):
    """Raised when the Eudic API returns an error."""


class HttpResponseError(RuntimeError):
    def __init__(
        self,
        code: int,
        message: str,
        headers: Any,
        response_text: str,
    ) -> None:
        super().__init__(f"HTTP {code}: {message}")
        self.code = code
        self.message = message
        self.headers = headers
        self.response_text = response_text


def acquire_export_lock() -> TextIO:
    EXPORT_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = EXPORT_LOCK_PATH.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise ApiError(
            "Another Eudic export is already running. Do not start concurrent "
            "exports; wait for it to finish, then use one single date-range command."
        ) from exc
    return handle


def release_export_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


@dataclass
class Category:
    id: str
    language: str
    name: str


@dataclass
class RequestStats:
    category_requests: int = 0
    word_page_requests: int = 0
    retry_requests: int = 0
    delete_requests: int = 0
    verification_requests: int = 0

    @property
    def total_requests(self) -> int:
        return (
            self.category_requests
            + self.word_page_requests
            + self.retry_requests
            + self.delete_requests
            + self.verification_requests
        )

    def summary(self) -> str:
        deletion_stats = (
            f"deletes={self.delete_requests}, " if self.delete_requests else ""
        )
        verification_stats = (
            f"verifications={self.verification_requests}, "
            if self.verification_requests
            else ""
        )
        return (
            "Request stats: "
            f"categories={self.category_requests}, "
            f"word_pages={self.word_page_requests}, "
            f"retries={self.retry_requests}, "
            f"{deletion_stats}"
            f"{verification_stats}"
            f"total={self.total_requests}"
        )


class RequestController:
    def __init__(
        self,
        stats: RequestStats,
        *,
        time_source: RequestTimeSource,
        interval_seconds: float = REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self.stats = stats
        self.time_source = time_source
        self.interval_seconds = interval_seconds
        self.last_started_at: float | None = None

    def before_request(
        self,
        request_kind: Literal[
            "category", "word_page", "retry", "delete", "verification"
        ],
    ) -> None:
        now = self.time_source.monotonic()
        if self.last_started_at is not None:
            wait_seconds = self.interval_seconds - (now - self.last_started_at)
            if wait_seconds > 0:
                self.time_source.sleep(wait_seconds)
                now = self.time_source.monotonic()
        self.last_started_at = now

        if request_kind == "category":
            self.stats.category_requests += 1
        elif request_kind == "word_page":
            self.stats.word_page_requests += 1
        elif request_kind == "delete":
            self.stats.delete_requests += 1
        elif request_kind == "verification":
            self.stats.verification_requests += 1
        else:
            self.stats.retry_requests += 1

    def before_retry(self, retry_after_seconds: float) -> None:
        if retry_after_seconds > 0:
            self.time_source.sleep(retry_after_seconds)
        self.before_request("retry")


def _timezone_candidates_from_system() -> list[str]:
    candidates: list[str] = []

    env_tz = os.getenv("TZ", "").strip()
    if env_tz:
        candidates.append(env_tz)

    etc_timezone = Path("/etc/timezone")
    if etc_timezone.exists():
        try:
            text = etc_timezone.read_text(encoding="utf-8").strip()
        except OSError:
            text = ""
        if text:
            candidates.append(text)

    localtime = Path("/etc/localtime")
    if localtime.is_symlink():
        try:
            resolved = localtime.resolve()
        except OSError:
            resolved = None
        if resolved is not None:
            parts = resolved.parts
            if "zoneinfo" in parts:
                idx = parts.index("zoneinfo")
                candidate = "/".join(parts[idx + 1 :]).strip()
                if candidate:
                    candidates.append(candidate)

    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def resolve_timezone(requested_name: str | None) -> tuple[tzinfo, str]:
    if requested_name:
        try:
            return ZoneInfo(requested_name), requested_name
        except ZoneInfoNotFoundError as exc:
            raise ApiError(f"Unknown timezone: {requested_name}") from exc

    for candidate in _timezone_candidates_from_system():
        try:
            return ZoneInfo(candidate), candidate
        except ZoneInfoNotFoundError:
            continue

    local_tz = datetime.now().astimezone().tzinfo
    if local_tz is None:
        raise ApiError("Could not determine system timezone. Pass --timezone explicitly.")

    fallback_name = (
        getattr(local_tz, "key", None)
        or getattr(local_tz, "zone", None)
        or datetime.now().astimezone().tzname()
        or "local"
    )
    return local_tz, fallback_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Eudic cloud study list words to CSV or JSON."
    )
    parser.add_argument(
        "--language",
        default="en",
        choices=["en", "fr", "de", "es"],
        help="Study list language. Default: en",
    )
    parser.add_argument(
        "--token",
        help=(
            "OpenAPI token. You can also use EUDIC_TOKEN or EUDIC_AUTH. "
            "If it does not start with 'NIS ', the prefix will be added automatically."
        ),
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List cloud study list categories and exit.",
    )
    parser.add_argument(
        "--category-id",
        help="Export a specific category by id.",
    )
    parser.add_argument(
        "--category-name",
        help="Export a specific category by exact name.",
    )
    parser.add_argument(
        "--all-categories",
        action="store_true",
        help="Export all categories under the selected language.",
    )
    parser.add_argument(
        "--start-date",
        help="Inclusive local start date in YYYY-MM-DD, for example 2026-04-01.",
    )
    parser.add_argument(
        "--end-date",
        help="Inclusive local end date in YYYY-MM-DD, for example 2026-04-09.",
    )
    parser.add_argument(
        "--timezone",
        help=(
            "IANA timezone used for date filtering and local timestamps. "
            "Default: system local timezone"
        ),
    )
    parser.add_argument(
        "--format",
        default="csv",
        choices=["csv", "json"],
        help="Output format. Default: csv",
    )
    parser.add_argument(
        "--output",
        help="Output file path. Default: auto-generated in the current directory.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="API page size. Default: 100",
    )
    return parser.parse_args()


def token_setup_message() -> str:
    return "\n".join(
        [
            "Missing token.",
            "",
            "Set up your Eudic OpenAPI token first:",
            f"1. Open {OPENAPI_DOC_URL}",
            "2. Log in to your Eudic account",
            "3. Copy your personal authorization string",
            "4. Run: export EUDIC_TOKEN='NIS your-token'",
            "5. Re-run this command",
            "",
            "You can also pass --token for a one-off run, but avoid saving tokens in tracked files.",
        ]
    )


def get_auth_header(raw_token: str | None) -> str:
    token = raw_token or os.getenv("EUDIC_TOKEN") or os.getenv("EUDIC_AUTH")
    if not token:
        raise ApiError(token_setup_message())
    token = token.strip()
    return token if token.startswith("NIS ") else f"NIS {token}"


def eudic_ssl_context() -> ssl.SSLContext:
    """TLS 1.3 + Authorization on api.frdic.com can fail with EOF; pin to TLS 1.2."""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def _http_error_details(exc: urllib.error.HTTPError) -> tuple[str, str]:
    body_text = exc.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(body_text)
    except json.JSONDecodeError:
        return body_text or exc.reason, body_text
    if isinstance(parsed, dict) and parsed.get("message"):
        return str(parsed["message"]), body_text
    return body_text or exc.reason, body_text


def _perform_http_request(request: urllib.request.Request) -> dict[str, Any]:
    try:
        options = {"timeout": 30} if request.get_method() == "DELETE" else {}
        with urllib.request.urlopen(
            request, context=eudic_ssl_context(), **options
        ) as response:
            if request.get_method() == "DELETE" and response.status != 204:
                raise ApiError(
                    f"Eudic deletion was not confirmed (HTTP {response.status}; expected 204)."
                )
            raw = response.read().decode("utf-8")
            if response.status == 204:
                return {}
            try:
                return json.loads(raw) if raw else {}
            except json.JSONDecodeError as exc:
                raise ApiError("Eudic returned an invalid JSON response.") from exc
    except urllib.error.HTTPError as exc:
        message, response_text = _http_error_details(exc)
        raise HttpResponseError(
            exc.code,
            message,
            exc.headers,
            response_text,
        ) from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Network error: {exc.reason}") from exc


def _is_rate_limit_error(error: HttpResponseError) -> bool:
    if error.code == 429:
        return True
    if error.code != 403:
        return False
    message = f"{error.message}\n{error.response_text}".casefold()
    markers = (
        "too many requests",
        "rate limit",
        "request too frequently",
        "access too frequently",
        "访问过于频繁",
        "请求过于频繁",
        "访问频率过高",
        "请求频率过高",
    )
    return any(marker in message for marker in markers)


def _retry_after_seconds(
    headers: Any,
    utc_now: Callable[[], datetime],
) -> float | None:
    raw_value = headers.get("Retry-After") if headers is not None else None
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = (retry_at.astimezone(timezone.utc) - utc_now()).total_seconds()

    if not math.isfinite(seconds) or not 0 <= seconds <= MAX_RETRY_AFTER_SECONDS:
        return None
    return seconds


def api_request(
    path: str,
    auth_header: str,
    *,
    method: str = "GET",
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    request_controller: RequestController,
    request_kind: Literal["category", "word_page", "delete", "verification"],
    allow_not_found: bool = False,
) -> dict[str, Any] | None:
    url = f"{BASE_URL}{path}"
    if query:
        query = {k: v for k, v in query.items() if v is not None}
        url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"

    payload = None
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": auth_header,
        "Accept": "application/json",
    }
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    request_controller.before_request(request_kind)
    try:
        return _perform_http_request(request)
    except HttpResponseError as exc:
        if allow_not_found and exc.code == 404:
            return None
        # A lost/failed DELETE response must be reconciled on the next run,
        # never blindly replayed by the exporter's read retry policy.
        if method == "DELETE":
            raise ApiError(
                f"Eudic deletion failed (HTTP {exc.code}); not retried."
            ) from exc
        if not _is_rate_limit_error(exc):
            raise ApiError(str(exc)) from exc
        retry_after = _retry_after_seconds(
            exc.headers,
            request_controller.time_source.utc_now,
        )
        if retry_after is None:
            raise ApiError(
                f"{exc}. Rate limit response did not include a valid Retry-After "
                "between 0 and 120 seconds; export stopped without retrying."
            ) from exc

        request_controller.before_retry(retry_after)
        try:
            return _perform_http_request(request)
        except HttpResponseError as retry_exc:
            if allow_not_found and retry_exc.code == 404:
                return None
            raise ApiError(
                f"{retry_exc}. The single allowed rate-limit retry failed; export stopped."
            ) from retry_exc


def list_categories(
    language: str, auth_header: str, request_controller: RequestController
) -> list[Category]:
    response = api_request(
        "/studylist/category",
        auth_header,
        query={"language": language},
        request_controller=request_controller,
        request_kind="category",
    )
    return [
        Category(
            id=str(item["id"]),
            language=str(item["language"]),
            name=str(item["name"]),
        )
        for item in response.get("data", [])
    ]


def fetch_words_page(
    *,
    language: str,
    category_id: str,
    page: int,
    page_size: int,
    auth_header: str,
    request_controller: RequestController,
) -> list[dict[str, Any]]:
    response = api_request(
        "/studylist/words",
        auth_header,
        query={
            "language": language,
            "category_id": category_id,
            "page": page,
            "page_size": page_size,
        },
        request_controller=request_controller,
        request_kind="word_page",
    )
    return response.get("data", []) or []


def fetch_all_words(
    *,
    language: str,
    category_id: str,
    page_size: int,
    auth_header: str,
    request_controller: RequestController,
) -> list[dict[str, Any]]:
    for first_page in (0, 1):
        records: list[dict[str, Any]] = []
        page = first_page
        while True:
            items = fetch_words_page(
                language=language,
                category_id=category_id,
                page=page,
                page_size=page_size,
                auth_header=auth_header,
                request_controller=request_controller,
            )
            if page == first_page and not items:
                break
            if not items:
                return records
            records.extend(items)
            if len(items) < page_size:
                return records
            page += 1
        if records:
            return records
    return []


def parse_date(date_text: str | None, tz: tzinfo, is_end: bool) -> datetime | None:
    if not date_text:
        return None
    try:
        day = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError as exc:
        raise ApiError(f"Invalid date: {date_text}. Expected YYYY-MM-DD.") from exc
    base = day.replace(tzinfo=tz)
    return base + timedelta(days=1) if is_end else base


def parse_api_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ApiError(f"Invalid Eudic encounter timestamp: {value!r}") from exc


def filter_records(
    records: Iterable[dict[str, Any]],
    *,
    start_at: datetime | None,
    end_before: datetime | None,
    tz: tzinfo,
    category: Category,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in records:
        add_time_raw = item.get("add_time")
        add_time_utc = parse_api_time(add_time_raw) if add_time_raw else None
        add_time_local = add_time_utc.astimezone(tz) if add_time_utc else None
        if start_at and add_time_local and add_time_local < start_at:
            continue
        if end_before and add_time_local and add_time_local >= end_before:
            continue

        filtered.append(
            {
                "language": category.language,
                "category_id": category.id,
                "category_name": category.name,
                "word": item.get("word", ""),
                "phon": item.get("phon", ""),
                "exp": item.get("exp", ""),
                "add_time_utc": add_time_utc.isoformat().replace("+00:00", "Z")
                if add_time_utc
                else "",
                "add_time_local": add_time_local.isoformat() if add_time_local else "",
                "star": item.get("star", ""),
                "context_line": item.get("context_line", ""),
            }
        )
    return filtered


def resolve_categories(
    all_categories: list[Category],
    *,
    category_id: str | None,
    category_name: str | None,
    all_selected: bool,
) -> list[Category]:
    if all_selected:
        return all_categories
    if category_id:
        matched = [item for item in all_categories if item.id == str(category_id)]
        if not matched:
            raise ApiError(f"Category id not found: {category_id}")
        return matched
    if category_name:
        matched = [item for item in all_categories if item.name == category_name]
        if not matched:
            raise ApiError(f"Category name not found: {category_name}")
        return matched
    raise ApiError(
        "Please choose one of --list-categories, --category-id, --category-name, or --all-categories."
    )


def default_output_path(
    *,
    fmt: str,
    category_label: str,
    start_date: str | None,
    end_date: str | None,
) -> Path:
    safe_label = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in category_label
    ).strip("_")
    parts = ["eudic", safe_label or "export"]
    if start_date:
        parts.append(f"from_{start_date}")
    if end_date:
        parts.append(f"to_{end_date}")
    return Path.cwd() / ("_".join(parts) + f".{fmt}")


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text_atomically(
    path: Path,
    write_content: Callable[[TextIO], None],
    *,
    newline: str | None = None,
) -> None:
    ensure_output_dir(path)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline=newline,
        ) as handle:
            descriptor = -1
            write_content(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        temp_path.unlink(missing_ok=True)
        raise


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "language",
        "category_id",
        "category_name",
        "word",
        "phon",
        "exp",
        "add_time_utc",
        "add_time_local",
        "star",
        "context_line",
    ]
    def write_content(handle: TextIO) -> None:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    try:
        write_text_atomically(path, write_content, newline="")
    except Exception as exc:
        raise ApiError(f"Could not write CSV output atomically to {path}: {exc}") from exc


def write_json(path: Path, rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    payload = {"meta": meta, "data": rows}

    def write_content(handle: TextIO) -> None:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    try:
        write_text_atomically(path, write_content)
    except Exception as exc:
        raise ApiError(f"Could not write JSON output atomically to {path}: {exc}") from exc


def print_categories(categories: list[Category]) -> None:
    if not categories:
        print("No categories found.")
        return
    width = max(len(item.id) for item in categories)
    print("Categories:")
    for item in categories:
        print(f"{item.id.ljust(width)}  {item.name} ({item.language})")


def main() -> int:
    lock_handle: TextIO | None = None
    stats = RequestStats()
    try:
        args = parse_args()
        tz, timezone_name = resolve_timezone(args.timezone)

        auth_header = get_auth_header(args.token)
        lock_handle = acquire_export_lock()
        request_controller = RequestController(
            stats,
            time_source=REQUEST_TIME_SOURCE,
        )
        categories = list_categories(args.language, auth_header, request_controller)

        if args.list_categories:
            print_categories(categories)
            print(stats.summary())
            return 0

        selected = resolve_categories(
            categories,
            category_id=args.category_id,
            category_name=args.category_name,
            all_selected=args.all_categories,
        )

        start_at = parse_date(args.start_date, tz, is_end=False)
        end_before = parse_date(args.end_date, tz, is_end=True)
        if start_at and end_before and start_at >= end_before:
            raise ApiError("--start-date must be earlier than or equal to --end-date.")

        rows: list[dict[str, Any]] = []
        for category in selected:
            words = fetch_all_words(
                language=args.language,
                category_id=category.id,
                page_size=args.page_size,
                auth_header=auth_header,
                request_controller=request_controller,
            )
            rows.extend(
                filter_records(
                    words,
                    start_at=start_at,
                    end_before=end_before,
                    tz=tz,
                    category=category,
                )
            )

        category_label = "all_categories" if args.all_categories else selected[0].name
        output_path = (
            Path(args.output)
            if args.output
            else default_output_path(
                fmt=args.format,
                category_label=category_label,
                start_date=args.start_date,
                end_date=args.end_date,
            )
        )

        if args.format == "csv":
            write_csv(output_path, rows)
        else:
            write_json(
                output_path,
                rows,
                meta={
                    "language": args.language,
                    "timezone": timezone_name,
                    "start_date": args.start_date,
                    "end_date": args.end_date,
                    "category_ids": [item.id for item in selected],
                    "category_names": [item.name for item in selected],
                    "exported_count": len(rows),
                },
            )

        print(f"Exported {len(rows)} words to {output_path}")
        print(stats.summary())
        return 0
    except ApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(stats.summary(), file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"Error: Unexpected export failure ({type(exc).__name__}).",
            file=sys.stderr,
        )
        print(stats.summary(), file=sys.stderr)
        return 1
    finally:
        if lock_handle is not None:
            release_export_lock(lock_handle)


if __name__ == "__main__":
    raise SystemExit(main())
