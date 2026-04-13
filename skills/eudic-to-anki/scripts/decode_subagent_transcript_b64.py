#!/usr/bin/env python3
"""Decode base64-wrapped coach JSON from a Cursor subagent transcript (.jsonl).

Subagents sometimes return a single long base64 line (transport-safe). This script
reads one transcript file, scans assistant message text for the longest plausible
base64 token, decodes UTF-8, parses JSON, and writes pretty-printed output.

Typical transcript location (machine-specific):
  ~/.cursor/projects/<project>/agent-transcripts/<chat-uuid>/subagents/<subagent-uuid>.jsonl

Usage (from repo .agents/skills):
  python3 eudic-to-anki/scripts/decode_subagent_transcript_b64.py \\
    /path/to/subagent.jsonl -o eudic-to-anki/import_scratch/coach_batch_01.json
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

# Avoid tiny false positives; coach payloads are large.
_MIN_B64_LEN = 200
_B64_RE = re.compile(r"[A-Za-z0-9+/]{" + str(_MIN_B64_LEN) + r",}={0,2}")


def _extract_assistant_texts(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        role = obj.get("role")
        if role == "assistant":
            c = obj.get("content")
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, list):
                for part in c:
                    if isinstance(part, dict) and part.get("type") == "text":
                        t = part.get("text")
                        if isinstance(t, str):
                            out.append(t)
                    elif isinstance(part, str):
                        out.append(part)
        for v in obj.values():
            out.extend(_extract_assistant_texts(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_extract_assistant_texts(item))
    return out


def _longest_b64_token(text: str) -> str | None:
    best: str | None = None
    for m in _B64_RE.finditer(text):
        tok = m.group(0)
        if best is None or len(tok) > len(best):
            best = tok
    return best


def _decode_coach_from_transcript(raw: str) -> dict[str, Any]:
    texts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        texts.extend(_extract_assistant_texts(obj))

    haystack = "\n".join(texts) if texts else raw
    token = _longest_b64_token(haystack)
    if not token:
        raise SystemExit(
            "No base64 token found (min length %d). "
            "If the subagent returned raw JSON, parse it directly instead of this script."
            % _MIN_B64_LEN
        )

    try:
        decoded = base64.b64decode(token, validate=True)
    except Exception as e:
        raise SystemExit("base64 decode failed: %s" % e) from e

    try:
        s = decoded.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit("decoded payload is not valid UTF-8: %s" % e) from e

    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        raise SystemExit("decoded payload is not JSON: %s" % e) from e

    if not isinstance(data, dict):
        raise SystemExit("decoded JSON root must be an object")
    return data


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "jsonl",
        type=Path,
        help="Path to subagent transcript .jsonl",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Write pretty-printed JSON here (UTF-8)",
    )
    args = p.parse_args()

    raw = args.jsonl.read_text(encoding="utf-8", errors="replace")
    data = _decode_coach_from_transcript(raw)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
