#!/usr/bin/env python3
"""Generate pronunciation audio via Microsoft Edge online TTS (edge-tts)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


DEFAULT_VOICE = "en-US-GuyNeural"


class EdgeTtsError(RuntimeError):
    """Raised when edge-tts cannot synthesize audio."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TTS via edge-tts (Microsoft neural voices, requires network)."
    )
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output", required=True, help="Output audio path (.mp3).")
    parser.add_argument(
        "--voice",
        default=os.getenv("EDGE_TTS_VOICE", DEFAULT_VOICE),
        help=(
            "Voice id, e.g. en-US-GuyNeural. List: edge-tts --list-voices. "
            f"Default: {DEFAULT_VOICE} or EDGE_TTS_VOICE env."
        ),
    )
    return parser.parse_args()


async def _synthesize(text: str, voice: str, output: Path) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise EdgeTtsError(
            "Missing dependency. Install with: pip install edge-tts\n"
            "Upstream: https://github.com/rany2/edge-tts"
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text.strip(), voice)
    await communicate.save(str(output))


def main() -> int:
    try:
        args = parse_args()
        out = Path(args.output).expanduser().resolve()
        asyncio.run(_synthesize(args.text, args.voice, out))
        print(f"Generated audio at {out}")
        return 0
    except EdgeTtsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: edge-tts failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
