#!/usr/bin/env python3
"""Export Eudic cloud study list data by date via the official OpenAPI."""

from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


BASE_URL = "https://api.frdic.com/api/open/v1"
DEFAULT_PAGE_SIZE = 100
OPENAPI_DOC_URL = "https://my.eudic.net/OpenAPI/Authorization"


class ApiError(RuntimeError):
    """Raised when the Eudic API returns an error."""


@dataclass
class Category:
    id: str
    language: str
    name: str


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
        default="Asia/Shanghai",
        help="IANA timezone used for date filtering and local timestamps. Default: Asia/Shanghai",
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


def api_request(
    path: str,
    auth_header: str,
    *,
    method: str = "GET",
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    try:
        with urllib.request.urlopen(request, context=eudic_ssl_context()) as response:
            raw = response.read().decode("utf-8")
            if response.status == 204:
                return {}
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        message = body_text
        try:
            parsed = json.loads(body_text)
            message = parsed.get("message") or body_text
        except json.JSONDecodeError:
            pass
        raise ApiError(f"HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Network error: {exc.reason}") from exc


def list_categories(language: str, auth_header: str) -> list[Category]:
    response = api_request(
        "/studylist/category",
        auth_header,
        query={"language": language},
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
    )
    return response.get("data", []) or []


def fetch_all_words(
    *,
    language: str,
    category_id: str,
    page_size: int,
    auth_header: str,
) -> list[dict[str, Any]]:
    for first_page in (1, 0):
        records: list[dict[str, Any]] = []
        page = first_page
        while True:
            items = fetch_words_page(
                language=language,
                category_id=category_id,
                page=page,
                page_size=page_size,
                auth_header=auth_header,
            )
            if page == first_page and not items and first_page == 1:
                records = []
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


def parse_date(date_text: str | None, tz: ZoneInfo, is_end: bool) -> datetime | None:
    if not date_text:
        return None
    try:
        day = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError as exc:
        raise ApiError(f"Invalid date: {date_text}. Expected YYYY-MM-DD.") from exc
    base = day.replace(tzinfo=tz)
    return base + timedelta(days=1) if is_end else base


def parse_api_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def filter_records(
    records: Iterable[dict[str, Any]],
    *,
    start_at: datetime | None,
    end_before: datetime | None,
    tz: ZoneInfo,
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
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
    ensure_output_dir(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    payload = {"meta": meta, "data": rows}
    ensure_output_dir(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def print_categories(categories: list[Category]) -> None:
    if not categories:
        print("No categories found.")
        return
    width = max(len(item.id) for item in categories)
    print("Categories:")
    for item in categories:
        print(f"{item.id.ljust(width)}  {item.name} ({item.language})")


def main() -> int:
    try:
        args = parse_args()
        try:
            tz = ZoneInfo(args.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ApiError(f"Unknown timezone: {args.timezone}") from exc

        auth_header = get_auth_header(args.token)
        categories = list_categories(args.language, auth_header)

        if args.list_categories:
            print_categories(categories)
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
        output_path = Path(args.output) if args.output else default_output_path(
            fmt=args.format,
            category_label=category_label,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        if args.format == "csv":
            write_csv(output_path, rows)
        else:
            write_json(
                output_path,
                rows,
                meta={
                    "language": args.language,
                    "timezone": args.timezone,
                    "start_date": args.start_date,
                    "end_date": args.end_date,
                    "category_ids": [item.id for item in selected],
                    "category_names": [item.name for item in selected],
                    "exported_count": len(rows),
                },
            )

        print(f"Exported {len(rows)} words to {output_path}")
        return 0
    except ApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
