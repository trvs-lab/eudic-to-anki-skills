#!/usr/bin/env python3
"""Import generated vocabulary notes into Anki via AnkiConnect."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from coach_fields import (
    LEARNING_PRIORITY_VALUES,
    TARGET_CHUNK_CLOZE_KEYS,
    TARGET_CHUNK_KEYS,
    TARGET_CHUNK_MEANING_KEYS,
    TARGET_CHUNK_SENTENCE_KEYS,
    first_text_field,
    fuse_pos_into_meaning,
    learning_priority_marker,
    normalize_learning_priority,
)


DEFAULT_ANKI_URL = "http://127.0.0.1:8765"
DEFAULT_DECK = "words"
STRUCTURED_VOCAB_MODEL = "TRVS-Lab"
DEFAULT_MODEL = STRUCTURED_VOCAB_MODEL
DEFAULT_AUDIO_FIELD = "发音"
DEFAULT_AUDIO_FORMAT = "mp3"
API_VERSION = 6
STATIC_TAGS_TO_DROP = {"english", "vocab", "eudic"}
CHUNK_ANCHOR_TEMPLATE = "Chunk Anchor"
CHUNK_RECALL_TEMPLATE = "Chunk Recall"
CHUNK_TEMPLATE_BY_ORD = {
    0: CHUNK_ANCHOR_TEMPLATE,
    1: CHUNK_RECALL_TEMPLATE,
}
TRVS_REQUIRED_FIELDS = (
    "音标",
    "释义",
    "英英",
    "词根",
    "常用搭配",
    "目标短语块",
    "短语块锚点",
    "短语块例句",
    "学习标记",
)
ROOT_PLACEHOLDERS = {"-", "无"}

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_MODEL_SPEC_PATH = SKILL_DIR / "assets" / "trvs_lab_model.json"
DEFAULT_ARTIFACT_DIR = Path.home() / "Documents" / "eudic-to-anki-temp"
DEFAULT_AUDIO_DIR = DEFAULT_ARTIFACT_DIR / "generated_audio"


class AnkiImportError(RuntimeError):
    """Raised when note import or validation fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import generated vocabulary notes into Anki via AnkiConnect."
    )
    parser.add_argument(
        "--input",
        help="Path to a JSON, CSV, or TSV file containing structured notes.",
    )
    parser.add_argument(
        "--deck",
        default=DEFAULT_DECK,
        help=(
            f"Base deck name. Default: {DEFAULT_DECK}. "
            f"For {STRUCTURED_VOCAB_MODEL}, notes are created in this deck, then generated "
            "cards route to <deck>::chunk-anchor::<focus|passive|ignore> and "
            "<deck>::chunk-recall::focus when priority decks are enabled."
        ),
    )
    parser.add_argument(
        "--no-priority-decks",
        action="store_true",
        help=(
            f"{STRUCTURED_VOCAB_MODEL} only: keep generated cards in --deck instead of "
            "routing them to phrase chunk card decks."
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Note type name. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--model-spec",
        default=str(DEFAULT_MODEL_SPEC_PATH),
        help="JSON file describing a note type to auto-create when missing.",
    )
    parser.add_argument(
        "--no-ensure-model",
        action="store_true",
        help="Do not auto-create the requested model if it is missing.",
    )
    parser.add_argument(
        "--front-field",
        default="Front",
        help="Field name for the card front when not using a known structured model.",
    )
    parser.add_argument(
        "--back-field",
        default="Back",
        help="Field name for the card back when not using a known structured model.",
    )
    parser.add_argument(
        "--audio-provider",
        choices=["none", "existing", "command"],
        default="none",
        help=(
            "Audio strategy. 'existing' uploads audio files referenced in notes. "
            "'command' generates files through an external command. Default: none"
        ),
    )
    parser.add_argument(
        "--audio-command",
        help=(
            "Argument template for --audio-provider command. It is parsed with shlex "
            "and executed without a shell. Supported placeholders: {word}, {text}, "
            "{output}, {voice}."
        ),
    )
    parser.add_argument(
        "--audio-dir",
        default=str(DEFAULT_AUDIO_DIR),
        help=(
            "Output directory for generated audio when using --audio-provider command. "
            f"Default: {DEFAULT_AUDIO_DIR}"
        ),
    )
    parser.add_argument(
        "--audio-field",
        default=DEFAULT_AUDIO_FIELD,
        help=f"Field name that stores the [sound:...] tag. Default: {DEFAULT_AUDIO_FIELD}",
    )
    parser.add_argument(
        "--audio-format",
        default=DEFAULT_AUDIO_FORMAT,
        help=f"Generated audio extension. Default: {DEFAULT_AUDIO_FORMAT}",
    )
    parser.add_argument(
        "--audio-voice",
        default="default",
        help="Optional voice identifier passed into {voice} for command-based TTS.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Global tag to add to every note. Repeatable.",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow duplicate notes according to Anki's duplicate rules.",
    )
    parser.add_argument(
        "--dia-upsert",
        action="store_true",
        help=(
            f"{STRUCTURED_VOCAB_MODEL} only: match existing notes in the base deck plus chunk decks "
            "by the 单词 field, update fields/tags, route generated cards by template, "
            "then reset existing cards to new by default. "
            "Words appearing multiple times in the input keep the last payload per word."
        ),
    )
    parser.add_argument(
        "--preserve-progress-on-update",
        action="store_true",
        help=(
            f"{STRUCTURED_VOCAB_MODEL} --dia-upsert only: update existing notes without "
            "forgetting cards, preserving scheduling/progress. Off by default."
        ),
    )
    parser.add_argument(
        "--create-deck",
        action="store_true",
        help="Create the deck if it does not already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the notes and show a summary without importing.",
    )
    parser.add_argument(
        "--require-audio",
        action="store_true",
        help=(
            f"{STRUCTURED_VOCAB_MODEL} only: require every final 发音 field to contain "
            "a [sound:...] tag. Use with --audio-provider command/existing."
        ),
    )
    parser.add_argument(
        "--verify-required-fields",
        action="store_true",
        help=(
            f"{STRUCTURED_VOCAB_MODEL} only: verify required card fields in the payload "
            "and, after import/upsert, in the affected Anki notes."
        ),
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip Anki sync after a successful import (default: sync runs).",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Check that AnkiConnect is reachable and exit.",
    )
    parser.add_argument(
        "--anki-url",
        default=DEFAULT_ANKI_URL,
        help=f"AnkiConnect URL. Default: {DEFAULT_ANKI_URL}",
    )
    return parser.parse_args()


class AnkiConnectClient:
    def __init__(self, url: str) -> None:
        self.url = url

    def invoke(self, action: str, **params: Any) -> Any:
        payload: dict[str, Any] = {"action": action, "version": API_VERSION}
        if params:
            payload["params"] = params

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise AnkiImportError(connection_help(self.url)) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AnkiImportError(
                f"Unexpected AnkiConnect response from {self.url}: {body[:200]}"
            ) from exc

        if parsed.get("error"):
            raise AnkiImportError(f"AnkiConnect error for '{action}': {parsed['error']}")
        return parsed.get("result")


def connection_help(url: str) -> str:
    return "\n".join(
        [
            f"Could not reach AnkiConnect at {url}.",
            "",
            "To fix this:",
            "1. Open Anki Desktop",
            "2. Go to Tools -> Add-ons -> Get Add-ons...",
            "3. Enter code 2055492159 to install AnkiConnect",
            "4. Save changes and restart Anki",
            f"5. Re-run: python3 scripts/ankiconnect_import.py --ping --anki-url {url}",
        ]
    )


def filter_static_tags(tags: list[str]) -> list[str]:
    return [tag for tag in tags if tag not in STATIC_TAGS_TO_DROP]


def split_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).replace(";", ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text == "-":
        return []
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    return [text]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text == "-" else text


def load_notes(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        if isinstance(payload, dict) and isinstance(payload.get("notes"), list):
            return [dict(item) for item in payload["notes"]]
        raise AnkiImportError("JSON input must be a list of notes or an object with a 'notes' array.")

    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            return [dict(row) for row in reader]

    raise AnkiImportError("Unsupported input format. Use JSON, CSV, or TSV.")


def load_model_spec(path: Path, model_name: str) -> dict[str, Any]:
    if not path.exists():
        raise AnkiImportError(f"Model spec not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["model_name"] = model_name
    base_dir = path.parent

    if "css_path" in payload:
        css_path = base_dir / payload["css_path"]
        if not css_path.exists():
            raise AnkiImportError(f"Model CSS file not found: {css_path}")
        payload["css"] = css_path.read_text(encoding="utf-8")

    if "card_templates" in payload:
        expanded_templates = []
        for template in payload["card_templates"]:
            expanded = dict(template)
            if "FrontPath" in expanded:
                front_path = base_dir / expanded.pop("FrontPath")
                if not front_path.exists():
                    raise AnkiImportError(f"Model front template not found: {front_path}")
                expanded["Front"] = front_path.read_text(encoding="utf-8")
            if "BackPath" in expanded:
                back_path = base_dir / expanded.pop("BackPath")
                if not back_path.exists():
                    raise AnkiImportError(f"Model back template not found: {back_path}")
                expanded["Back"] = back_path.read_text(encoding="utf-8")
            expanded_templates.append(expanded)
        payload["card_templates"] = expanded_templates

    return payload


def field_value(note: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in note and note[key] not in (None, ""):
            return normalize_text(note[key])
    return ""


def root_field_value(note: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key not in note or note[key] in (None, ""):
            continue
        text = str(note[key]).strip()
        if text in ROOT_PLACEHOLDERS:
            return text
        normalized = normalize_text(note[key])
        if normalized:
            return normalized
    return ""


def list_to_text(values: list[str], delimiter: str = "<br>") -> str:
    return delimiter.join(values)


def note_learning_priority(note: dict[str, Any]) -> str:
    for key in ("learning_priority", "priority", "学习优先级"):
        value = note.get(key)
        if value not in (None, ""):
            priority = normalize_learning_priority(value)
            if priority not in LEARNING_PRIORITY_VALUES:
                raise AnkiImportError(
                    "learning_priority must be one of "
                    f"{', '.join(LEARNING_PRIORITY_VALUES)} (got {value!r})."
                )
            return priority
    return "passive"


def note_learning_marker(note: dict[str, Any]) -> str:
    explicit = field_value(note, "学习标记", "learning_marker")
    if explicit:
        return explicit
    return learning_priority_marker(note_learning_priority(note))


def priority_decks_enabled(model: str, no_priority_decks: bool) -> bool:
    return model == STRUCTURED_VOCAB_MODEL and not no_priority_decks


def priority_deck_name(base_deck: str, priority: str) -> str:
    deck = base_deck.strip() or DEFAULT_DECK
    if deck.split("::")[-1] in LEARNING_PRIORITY_VALUES:
        return deck
    return f"{deck}::{priority}"


def chunk_anchor_deck_name(base_deck: str, priority: str) -> str:
    deck = base_deck.strip() or DEFAULT_DECK
    return f"{deck}::chunk-anchor::{priority}"


def chunk_recall_deck_name(base_deck: str) -> str:
    deck = base_deck.strip() or DEFAULT_DECK
    return f"{deck}::chunk-recall::focus"


def chunk_decks_for_priority(base_deck: str, priority: str) -> list[str]:
    decks = [chunk_anchor_deck_name(base_deck, priority)]
    if priority == "focus":
        decks.append(chunk_recall_deck_name(base_deck))
    return decks


def all_chunk_decks(base_deck: str) -> list[str]:
    return [
        chunk_anchor_deck_name(base_deck, priority)
        for priority in LEARNING_PRIORITY_VALUES
    ] + [chunk_recall_deck_name(base_deck)]


def note_target_deck(
    note: dict[str, Any],
    *,
    base_deck: str,
    model: str,
    use_priority_decks: bool,
) -> str:
    if use_priority_decks:
        return priority_deck_name(base_deck, note_learning_priority(note))
    return base_deck


def priority_search_decks(
    base_deck: str, target_deck: str, use_priority_decks: bool
) -> list[str]:
    decks = [target_deck]
    if use_priority_decks:
        decks = [
            base_deck,
            *[priority_deck_name(base_deck, p) for p in LEARNING_PRIORITY_VALUES],
            target_deck,
        ]
    seen: set[str] = set()
    unique_decks: list[str] = []
    for deck in decks:
        if deck not in seen:
            unique_decks.append(deck)
            seen.add(deck)
    return unique_decks


def deck_counts_text(payloads: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for payload in payloads:
        deck = str(payload.get("deckName") or "")
        counts[deck] = counts.get(deck, 0) + 1
    return ", ".join(f"{deck}: {count}" for deck, count in sorted(counts.items()))


def _priority_from_fields(fields: dict[str, Any], subject: str) -> str:
    marker = _field_text_value(fields.get("学习标记"))
    if marker == "★":
        return "focus"
    if marker == "◇":
        return "passive"
    if marker == "×":
        return "ignore"
    raise AnkiImportError(
        f"Cannot route cards for {subject}: unknown 学习标记 {marker!r}"
    )


def planned_chunk_deck_counts(
    payloads: list[dict[str, Any]],
    base_deck: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for payload in payloads:
        fields = payload.get("fields") or {}
        word = _field_text_value(fields.get("单词")) or "<unknown>"
        priority = _priority_from_fields(fields, word)
        for deck in chunk_decks_for_priority(base_deck, priority):
            counts[deck] = counts.get(deck, 0) + 1
    return counts


def planned_chunk_deck_counts_text(
    payloads: list[dict[str, Any]],
    base_deck: str,
) -> str:
    counts = planned_chunk_deck_counts(payloads, base_deck)
    return ", ".join(f"{deck}: {count}" for deck, count in sorted(counts.items()))


def build_trvs_lab_fields(note: dict[str, Any], audio_html: str) -> dict[str, str]:
    """Map JSON / coach notes onto the fresh-start TRVS-Lab phrase chunk note type."""
    meaning_values = normalize_list(note.get("meaning") or note.get("释义"))
    pos = field_value(note, "词性", "part_of_speech", "pos")
    meaning_values = fuse_pos_into_meaning(meaning_values, pos)
    collocation_values = normalize_list(note.get("collocations") or note.get("常用搭配"))
    return {
        "单词": field_value(note, "单词", "word"),
        "音标": field_value(note, "音标", "pronunciation"),
        "释义": list_to_text(meaning_values, "；"),
        "英英": field_value(note, "英英", "english_definition", "definition_en"),
        "词根": root_field_value(note, "词根", "root", "root_affix"),
        "例句": field_value(note, "例句", "example"),
        "常用搭配": list_to_text(collocation_values, "<br>"),
        "目标短语块": first_text_field(note, TARGET_CHUNK_KEYS),
        "短语块锚点": first_text_field(note, TARGET_CHUNK_MEANING_KEYS),
        "短语块例句": first_text_field(note, TARGET_CHUNK_SENTENCE_KEYS),
        "短语块挖空": first_text_field(note, TARGET_CHUNK_CLOZE_KEYS),
        "发音": audio_html or field_value(note, "发音", "audio_html"),
        "学习标记": note_learning_marker(note),
    }


def build_basic_fields(note: dict[str, Any], front_field: str, back_field: str) -> dict[str, str]:
    front = field_value(note, "front", "word")
    back = field_value(note, "back")
    if not front:
        raise AnkiImportError("Each note needs 'front' or 'word'.")
    if not back:
        raise AnkiImportError(
            f"Each note needs 'back' when not using the {STRUCTURED_VOCAB_MODEL} model."
        )
    return {
        front_field: front,
        back_field: back,
    }


def _field_text_value(raw: Any) -> str:
    if isinstance(raw, dict):
        return normalize_text(raw.get("value"))
    return normalize_text(raw)


def _root_field_text_value(raw: Any) -> str:
    value = raw.get("value") if isinstance(raw, dict) else raw
    text = str(value or "").strip()
    if text in ROOT_PLACEHOLDERS:
        return text
    return normalize_text(value)


def _missing_required_field_names(fields: dict[str, Any], require_audio: bool) -> list[str]:
    required = list(TRVS_REQUIRED_FIELDS)
    if require_audio:
        required.append("发音")
    missing: list[str] = []
    for name in required:
        if name == "词根":
            value = _root_field_text_value(fields.get(name))
        else:
            value = _field_text_value(fields.get(name))
        if not value:
            missing.append(name)
            continue
        if name == "发音" and require_audio and not value.startswith("[sound:"):
            missing.append(name)
    return missing


def verify_payload_required_fields(
    payloads: list[dict[str, Any]],
    *,
    require_audio: bool,
) -> None:
    problems: list[str] = []
    for payload in payloads:
        if payload.get("modelName") != STRUCTURED_VOCAB_MODEL:
            continue
        fields = payload.get("fields") or {}
        word = _field_text_value(fields.get("单词")) or "<unknown>"
        missing = _missing_required_field_names(fields, require_audio)
        if missing:
            problems.append(f"{word}: missing/invalid {', '.join(missing)}")
    if problems:
        detail = "; ".join(problems[:10])
        extra = "" if len(problems) <= 10 else f"; ... and {len(problems) - 10} more"
        raise AnkiImportError(f"Required TRVS-Lab fields failed payload check: {detail}{extra}")


def verify_anki_required_fields(
    client: AnkiConnectClient,
    note_ids: list[int],
    *,
    require_audio: bool,
) -> None:
    if not note_ids:
        return
    infos = client.invoke("notesInfo", notes=note_ids)
    problems: list[str] = []
    for info in infos or []:
        fields = info.get("fields") or {}
        word = _field_text_value(fields.get("单词")) or f"note:{info.get('noteId', '?')}"
        missing = _missing_required_field_names(fields, require_audio)
        if missing:
            problems.append(f"{word}: missing/invalid {', '.join(missing)}")
    if problems:
        detail = "; ".join(problems[:10])
        extra = "" if len(problems) <= 10 else f"; ... and {len(problems) - 10} more"
        raise AnkiImportError(f"Required TRVS-Lab fields failed Anki check: {detail}{extra}")


def sanitize_filename(text: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._")
    return base or "audio"


def pick_audio_source(note: dict[str, Any]) -> Path | None:
    for key in ("audio_path", "audio_file", "audio_source_path"):
        value = normalize_text(note.get(key))
        if value:
            return Path(value)
    return None


def store_audio_file(client: AnkiConnectClient, source_path: Path, target_name: str) -> str:
    if not source_path.exists():
        raise AnkiImportError(f"Audio file not found: {source_path}")
    result = client.invoke(
        "storeMediaFile",
        filename=target_name,
        path=str(source_path.resolve()),
    )
    return result or target_name


def generate_audio_with_command(
    *,
    command_template: str,
    word: str,
    text: str,
    output_path: Path,
    voice: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        template_args = shlex.split(command_template)
    except ValueError as exc:
        raise AnkiImportError(f"Invalid --audio-command template: {exc}") from exc
    if not template_args:
        raise AnkiImportError("--audio-command must not be empty.")

    format_values = {
        "word": word,
        "text": text,
        "output": str(output_path),
        "voice": voice,
    }
    try:
        command_args = [arg.format(**format_values) for arg in template_args]
    except KeyError as exc:
        placeholder = exc.args[0]
        raise AnkiImportError(
            "Unsupported placeholder in --audio-command: "
            f"{placeholder!r}. Supported placeholders: "
            "{word}, {text}, {output}, {voice}."
        ) from exc
    try:
        subprocess.run(command_args, shell=False, check=True, cwd=Path.cwd())
    except subprocess.CalledProcessError as exc:
        raise AnkiImportError(
            f"Audio generation command failed for '{word}': {shlex.join(command_args)}"
        ) from exc
    if not output_path.exists():
        raise AnkiImportError(
            "Audio generation command finished but no file was created: "
            f"{output_path}"
        )
    return output_path


def prepare_audio_html(
    *,
    note: dict[str, Any],
    client: AnkiConnectClient,
    audio_provider: str,
    audio_command: str | None,
    audio_dir: Path,
    audio_format: str,
    audio_voice: str,
) -> str:
    existing_html = field_value(note, "发音", "audio_html")
    if existing_html.startswith("[sound:"):
        return existing_html

    source_path = pick_audio_source(note)
    word = field_value(note, "word", "单词")
    if not word:
        return ""

    if audio_provider == "none":
        return existing_html

    if audio_provider == "existing":
        if not source_path:
            raise AnkiImportError(
                f"Audio provider 'existing' needs audio_path/audio_file for word '{word}'."
            )
        stored_name = store_audio_file(
            client,
            source_path,
            f"{sanitize_filename(word)}.{audio_format.lstrip('.')}",
        )
        return f"[sound:{stored_name}]"

    if audio_provider == "command":
        if not audio_command:
            raise AnkiImportError(
                "Audio provider 'command' requires --audio-command."
            )
        filename = f"{sanitize_filename(word)}.{audio_format.lstrip('.')}"
        generated_path = generate_audio_with_command(
            command_template=audio_command,
            word=word,
            text=word,
            output_path=audio_dir / filename,
            voice=audio_voice,
        )
        stored_name = store_audio_file(client, generated_path, filename)
        return f"[sound:{stored_name}]"

    raise AnkiImportError(f"Unsupported audio provider: {audio_provider}")


def note_to_anki_payload(
    note: dict[str, Any],
    *,
    client: AnkiConnectClient,
    deck: str,
    model: str,
    front_field: str,
    back_field: str,
    allow_duplicates: bool,
    global_tags: list[str],
    audio_provider: str,
    audio_command: str | None,
    audio_dir: Path,
    audio_format: str,
    audio_voice: str,
    use_priority_decks: bool,
) -> dict[str, Any]:
    tags = global_tags + split_tags(note.get("tags"))
    target_deck = deck
    if model == STRUCTURED_VOCAB_MODEL:
        priority = note_learning_priority(note)
        tags.append(f"priority::{priority}")
    tags = sorted(set(filter_static_tags(tags)))
    audio_html = prepare_audio_html(
        note=note,
        client=client,
        audio_provider=audio_provider,
        audio_command=audio_command,
        audio_dir=audio_dir,
        audio_format=audio_format,
        audio_voice=audio_voice,
    )

    if model == STRUCTURED_VOCAB_MODEL:
        fields = build_trvs_lab_fields(note, audio_html)
        if not fields["单词"]:
            raise AnkiImportError(
                f"Each {STRUCTURED_VOCAB_MODEL} note needs 'word' or '单词'."
            )
    else:
        fields = build_basic_fields(note, front_field, back_field)

    return {
        "deckName": target_deck,
        "modelName": model,
        "fields": fields,
        "tags": tags,
        "options": {
            "allowDuplicate": allow_duplicates,
        },
    }


def ensure_model(
    client: AnkiConnectClient,
    model_name: str,
    *,
    ensure_if_missing: bool,
    model_spec_path: Path,
) -> None:
    models = client.invoke("modelNames")
    if model_name in models:
        if ensure_if_missing and model_name == STRUCTURED_VOCAB_MODEL:
            spec = load_model_spec(model_spec_path, model_name)
            ensure_structured_model_schema(client, model_name, spec)
        return
    if not ensure_if_missing:
        raise AnkiImportError(
            f"Anki note type not found: {model_name}. Create it in Anki first or remove --no-ensure-model."
        )

    spec = load_model_spec(model_spec_path, model_name)
    client.invoke(
        "createModel",
        modelName=spec["model_name"],
        inOrderFields=spec["fields"],
        cardTemplates=spec["card_templates"],
        css=spec["css"],
    )


def _template_map_from_spec(spec: dict[str, Any]) -> dict[str, dict[str, str]]:
    templates: dict[str, dict[str, str]] = {}
    for template in spec.get("card_templates", []):
        name = str(template.get("Name") or template.get("name") or "Card 1")
        templates[name] = {
            "Front": str(template.get("Front") or ""),
            "Back": str(template.get("Back") or ""),
        }
    return templates


def _model_templates_need_update(templates: Any) -> bool:
    if not isinstance(templates, dict):
        return True
    required = {CHUNK_ANCHOR_TEMPLATE, CHUNK_RECALL_TEMPLATE}
    if not required.issubset(set(templates.keys())):
        return True
    anchor = str((templates.get(CHUNK_ANCHOR_TEMPLATE) or {}).get("Front") or "")
    anchor_back = str((templates.get(CHUNK_ANCHOR_TEMPLATE) or {}).get("Back") or "")
    recall = str((templates.get(CHUNK_RECALL_TEMPLATE) or {}).get("Front") or "")
    recall_back = str((templates.get(CHUNK_RECALL_TEMPLATE) or {}).get("Back") or "")
    return (
        "{{目标短语块}}" not in anchor
        or "{{短语块例句}}" not in anchor
        or "{{短语块锚点}}" not in anchor_back
        or "{{#例句}}" not in anchor_back
        or "{{短语块挖空}}" not in recall
        or "{{短语块例句}}" not in recall_back
    )


def _model_css_needs_update(styling: Any) -> bool:
    if isinstance(styling, dict):
        css = str(styling.get("css") or "")
    else:
        css = str(styling or "")
    return ".chunk-main" not in css or ".priority-marker" not in css


def ensure_structured_model_schema(
    client: AnkiConnectClient, model_name: str, spec: dict[str, Any]
) -> None:
    current_fields = client.invoke("modelFieldNames", modelName=model_name)
    if not isinstance(current_fields, list):
        raise AnkiImportError(f"Could not inspect fields for Anki note type {model_name!r}.")

    missing_fields = [field for field in spec["fields"] if field not in current_fields]
    for field in missing_fields:
        client.invoke("modelFieldAdd", modelName=model_name, fieldName=field)

    templates = client.invoke("modelTemplates", modelName=model_name)
    if missing_fields or _model_templates_need_update(templates):
        client.invoke(
            "updateModelTemplates",
            model={"name": model_name, "templates": _template_map_from_spec(spec)},
        )

    styling = client.invoke("modelStyling", modelName=model_name)
    if missing_fields or _model_css_needs_update(styling):
        client.invoke(
            "updateModelStyling",
            model={"name": model_name, "css": str(spec.get("css") or "")},
        )


def _dia_word_search_term(word: str) -> str:
    """Build an Anki search fragment for the 单词 field (TRVS-Lab / structured vocab)."""
    w = word.strip()
    if not w:
        return '单词:""'
    if any(c in w for c in ' "\n\t'):
        escaped = w.replace("\\", "\\\\").replace('"', '\\"')
        return f'单词:"{escaped}"'
    return f"单词:{w}"


def find_dia_note_ids(
    client: AnkiConnectClient, deck: str, model: str, word: str
) -> list[int]:
    deck_esc = deck.replace("\\", "\\\\").replace('"', '\\"')
    model_esc = model.replace("\\", "\\\\").replace('"', '\\"')
    query = f'deck:"{deck_esc}" note:"{model_esc}" {_dia_word_search_term(word)}'
    return client.invoke("findNotes", query=query)


def find_dia_note_ids_in_decks(
    client: AnkiConnectClient, decks: list[str], model: str, word: str
) -> list[int]:
    note_ids: list[int] = []
    seen: set[int] = set()
    for deck in decks:
        for nid in find_dia_note_ids(client, deck, model, word):
            int_nid = int(nid)
            if int_nid not in seen:
                note_ids.append(int_nid)
                seen.add(int_nid)
    return note_ids


def dedupe_dia_payloads_last_wins(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order: list[str] = []
    by_word: dict[str, dict[str, Any]] = {}
    for p in payloads:
        w = p["fields"]["单词"]
        if w not in by_word:
            order.append(w)
        by_word[w] = p
    return [by_word[w] for w in order]


def _card_template_name(card_info: dict[str, Any]) -> str:
    explicit = str(
        card_info.get("template") or card_info.get("templateName") or ""
    ).strip()
    if explicit:
        return explicit
    if "ord" in card_info:
        try:
            return CHUNK_TEMPLATE_BY_ORD[int(card_info["ord"])]
        except (KeyError, TypeError, ValueError) as exc:
            raise AnkiImportError(
                f"Could not identify card template for card {card_info.get('cardId')}: "
                f"unexpected ord {card_info.get('ord')!r}"
            ) from exc
    raise AnkiImportError(
        f"Could not identify card template for card {card_info.get('cardId')}: "
        "cardsInfo response has no template/templateName/ord"
    )


def _priority_from_note_info(info: dict[str, Any]) -> str:
    fields = info.get("fields") or {}
    word = _field_text_value(fields.get("单词")) or f"note:{info.get('noteId', '?')}"
    return _priority_from_fields(fields, word)


def _duplicate_ids(ids: list[int]) -> list[int]:
    seen: set[int] = set()
    duplicates: list[int] = []
    for item in ids:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def _raise_if_ids_do_not_match(
    *,
    expected: list[int],
    actual: list[int],
    label: str,
) -> None:
    expected_set = set(expected)
    actual_set = set(actual)
    duplicate_actual = _duplicate_ids(actual)
    if actual_set == expected_set and not duplicate_actual:
        return
    problems: list[str] = []
    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set)
    if missing:
        problems.append(f"missing {missing}")
    if unexpected:
        problems.append(f"unexpected {unexpected}")
    if duplicate_actual:
        problems.append(f"duplicate {sorted(duplicate_actual)}")
    raise AnkiImportError(
        f"{label}: malformed AnkiConnect response ({'; '.join(problems)})"
    )


def route_trvs_chunk_cards(
    client: AnkiConnectClient,
    note_ids: list[int],
    *,
    base_deck: str,
) -> None:
    if not note_ids:
        return
    requested_note_ids = [int(note_id) for note_id in note_ids]
    note_infos = client.invoke("notesInfo", notes=requested_note_ids) or []
    returned_note_ids = [
        int(info.get("noteId") or info.get("note") or 0)
        for info in note_infos
    ]
    _raise_if_ids_do_not_match(
        expected=requested_note_ids,
        actual=returned_note_ids,
        label="notesInfo",
    )
    all_grouped: dict[str, list[int]] = {}
    for info in note_infos:
        note_id = int(info.get("noteId") or info.get("note") or 0)
        word = (
            _field_text_value((info.get("fields") or {}).get("单词"))
            or f"note:{note_id}"
        )
        priority = _priority_from_note_info(info)
        card_ids = [int(card_id) for card_id in info.get("cards") or []]
        if not card_ids:
            raise AnkiImportError(f"{word}: no generated cards to route")
        card_infos = client.invoke("cardsInfo", cards=card_ids) or []
        returned_card_ids = [
            int(card.get("cardId") or card.get("card") or 0)
            for card in card_infos
        ]
        _raise_if_ids_do_not_match(
            expected=card_ids,
            actual=returned_card_ids,
            label=f"{word}: cardsInfo",
        )
        grouped: dict[str, list[int]] = {}
        seen_templates: set[str] = set()
        for card in card_infos:
            card_id = int(card.get("cardId") or card.get("card") or 0)
            template = _card_template_name(card)
            seen_templates.add(template)
            if template == CHUNK_ANCHOR_TEMPLATE:
                deck = chunk_anchor_deck_name(base_deck, priority)
            elif template == CHUNK_RECALL_TEMPLATE and priority == "focus":
                deck = chunk_recall_deck_name(base_deck)
            elif template == CHUNK_RECALL_TEMPLATE:
                raise AnkiImportError(f"{word}: non-focus note generated a Chunk Recall card")
            else:
                raise AnkiImportError(
                    f"{word}: unexpected card template {template!r} for card {card_id}"
                )
            grouped.setdefault(deck, []).append(card_id)
        if CHUNK_ANCHOR_TEMPLATE not in seen_templates:
            raise AnkiImportError(f"{word}: missing Chunk Anchor card")
        if priority == "focus" and CHUNK_RECALL_TEMPLATE not in seen_templates:
            raise AnkiImportError(f"{word}: focus note did not generate a Chunk Recall card")
        for deck, cards in grouped.items():
            all_grouped.setdefault(deck, []).extend(cards)
    for deck, cards in all_grouped.items():
        client.invoke("changeDeck", cards=cards, deck=deck)


def upsert_dia_notes(
    client: AnkiConnectClient,
    payloads: list[dict[str, Any]],
    *,
    base_deck: str,
    use_priority_decks: bool,
    preserve_progress_on_update: bool,
) -> tuple[int, int, list[dict[str, Any]], list[int]]:
    """Update existing notes or collect payloads to add."""
    to_add: list[dict[str, Any]] = []
    updated_note_ids: list[int] = []
    updated_notes = 0
    for payload in payloads:
        word = payload["fields"]["单词"]
        search_decks = (
            [base_deck, *all_chunk_decks(base_deck)]
            if use_priority_decks
            else [payload["deckName"]]
        )
        nids = find_dia_note_ids_in_decks(
            client,
            search_decks,
            payload["modelName"],
            word,
        )
        if nids:
            updated_note_ids.extend(int(nid) for nid in nids)
            for nid in nids:
                infos = client.invoke("notesInfo", notes=[nid])
                card_ids: list[int] = []
                for info in infos or []:
                    card_ids.extend(info.get("cards") or [])
                client.invoke(
                    "updateNote",
                    note={
                        "id": nid,
                        "fields": payload["fields"],
                        "tags": payload["tags"],
                    },
                )
                if not preserve_progress_on_update:
                    if card_ids:
                        client.invoke("forgetCards", cards=card_ids)
            updated_notes += len(nids)
        else:
            to_add.append(payload)
    return updated_notes, len(to_add), to_add, updated_note_ids


def ensure_deck(client: AnkiConnectClient, deck_name: str, create_if_missing: bool) -> None:
    decks = client.invoke("deckNames")
    if deck_name in decks:
        return
    if not create_if_missing:
        raise AnkiImportError(
            f"Anki deck not found: {deck_name}. Re-run with --create-deck to create it."
        )
    client.invoke("createDeck", deck=deck_name)


def main() -> int:
    try:
        args = parse_args()
        client = AnkiConnectClient(args.anki_url)
        version = client.invoke("version")

        if args.ping and not args.input:
            print(f"AnkiConnect is reachable at {args.anki_url} (version {version}).")
            return 0

        if not args.input:
            raise AnkiImportError("--input is required unless you only want --ping.")

        input_path = Path(args.input)
        if not input_path.exists():
            raise AnkiImportError(f"Input file not found: {input_path}")

        ensure_model(
            client,
            args.model,
            ensure_if_missing=not args.no_ensure_model,
            model_spec_path=Path(args.model_spec),
        )

        if args.dia_upsert and args.model != STRUCTURED_VOCAB_MODEL:
            raise AnkiImportError(
                f"--dia-upsert is only supported with --model {STRUCTURED_VOCAB_MODEL}."
            )
        if args.preserve_progress_on_update and not args.dia_upsert:
            raise AnkiImportError("--preserve-progress-on-update requires --dia-upsert.")
        if (args.require_audio or args.verify_required_fields) and args.model != STRUCTURED_VOCAB_MODEL:
            raise AnkiImportError(
                f"--require-audio/--verify-required-fields are only supported with --model {STRUCTURED_VOCAB_MODEL}."
            )

        raw_notes = load_notes(input_path)
        if not raw_notes:
            raise AnkiImportError("Input file did not contain any notes.")

        use_priority_decks = priority_decks_enabled(args.model, args.no_priority_decks)
        chunk_routing_enabled = args.model == STRUCTURED_VOCAB_MODEL and use_priority_decks
        if chunk_routing_enabled:
            target_decks = {
                deck_name
                for note in raw_notes
                for deck_name in chunk_decks_for_priority(
                    args.deck,
                    note_learning_priority(note),
                )
            }
        else:
            target_decks = {
                note_target_deck(
                    note,
                    base_deck=args.deck,
                    model=args.model,
                    use_priority_decks=use_priority_decks,
                )
                for note in raw_notes
            }
        decks_to_ensure = {args.deck, *target_decks}
        for deck_name in sorted(decks_to_ensure):
            ensure_deck(client, deck_name, args.create_deck)

        audio_dir = Path(args.audio_dir)
        payload_notes = [
            note_to_anki_payload(
                note,
                client=client,
                deck=args.deck,
                model=args.model,
                front_field=args.front_field,
                back_field=args.back_field,
                allow_duplicates=args.allow_duplicates or args.dia_upsert,
                global_tags=args.tag,
                audio_provider=args.audio_provider,
                audio_command=args.audio_command,
                audio_dir=audio_dir,
                audio_format=args.audio_format,
                audio_voice=args.audio_voice,
                use_priority_decks=use_priority_decks,
            )
            for note in raw_notes
        ]

        skipped_duplicates = 0
        if args.dia_upsert:
            payload_notes = dedupe_dia_payloads_last_wins(payload_notes)
        elif not args.allow_duplicates:
            allowed = client.invoke("canAddNotes", notes=payload_notes)
            filtered_notes = [
                note for note, can_add in zip(payload_notes, allowed) if can_add
            ]
            skipped_duplicates = len(payload_notes) - len(filtered_notes)
            payload_notes = filtered_notes

        if args.require_audio or args.verify_required_fields:
            verify_payload_required_fields(payload_notes, require_audio=args.require_audio)

        if args.dry_run:
            print(
                f"Validated {len(raw_notes)} notes for base deck '{args.deck}' "
                f"with model '{args.model}'."
            )
            if payload_notes:
                if chunk_routing_enabled:
                    print(
                        "Planned phrase chunk card decks: "
                        f"{planned_chunk_deck_counts_text(payload_notes, args.deck)}."
                    )
                else:
                    print(f"Target decks: {deck_counts_text(payload_notes)}.")
            if args.dia_upsert:
                would_update = 0
                would_add = 0
                for p in payload_notes:
                    w = p["fields"]["单词"]
                    search_decks = (
                        [args.deck, *all_chunk_decks(args.deck)]
                        if use_priority_decks
                        else [p["deckName"]]
                    )
                    nids = find_dia_note_ids_in_decks(
                        client,
                        search_decks,
                        args.model,
                        w,
                    )
                    if nids:
                        would_update += len(nids)
                    else:
                        would_add += 1
                print(
                    f"{STRUCTURED_VOCAB_MODEL} upsert dry-run: {would_update} existing note(s) would update "
                    f"and route generated cards if needed; {would_add} new note(s) would be added."
                )
                if would_update and not args.preserve_progress_on_update:
                    print("Existing updated cards would be reset to new.")
                if args.preserve_progress_on_update and would_update:
                    print("Preserve-progress-on-update is enabled: existing note scheduling would be preserved.")
            elif skipped_duplicates:
                print(f"Would skip {skipped_duplicates} duplicate notes.")
            if payload_notes:
                preview_fields = payload_notes[0]["fields"]
                preview_key = "单词" if args.model == STRUCTURED_VOCAB_MODEL else args.front_field
                print(f"Preview front: {preview_fields.get(preview_key, '')}")
            if args.verify_required_fields:
                print("Verified required TRVS-Lab payload fields.")
            return 0

        if not payload_notes:
            print(
                f"No notes imported. {skipped_duplicates} notes were skipped as duplicates."
            )
            return 0

        if args.dia_upsert:
            updated_ct, _pending_add_ct, to_add, updated_note_ids = upsert_dia_notes(
                client,
                payload_notes,
                base_deck=args.deck,
                use_priority_decks=use_priority_decks,
                preserve_progress_on_update=args.preserve_progress_on_update,
            )
            imported = 0
            affected_note_ids = list(updated_note_ids)
            if to_add:
                note_ids = client.invoke("addNotes", notes=to_add)
                added_note_ids = [int(note_id) for note_id in note_ids if note_id is not None]
                affected_note_ids.extend(added_note_ids)
                imported = len(added_note_ids)
            print(
                f"{STRUCTURED_VOCAB_MODEL} upsert: updated {updated_ct} note(s) "
                f"(fields + tags, scheduling {'preserved' if args.preserve_progress_on_update else 'reset to new'}), "
                f"added {imported} new note(s). "
                + (
                    "Planned phrase chunk card decks: "
                    f"{planned_chunk_deck_counts_text(payload_notes, args.deck)}."
                    if chunk_routing_enabled
                    else f"Target decks: {deck_counts_text(payload_notes)}."
                )
            )
        else:
            note_ids = client.invoke("addNotes", notes=payload_notes)
            affected_note_ids = [int(note_id) for note_id in note_ids if note_id is not None]
            imported = len(affected_note_ids)
            print(
                f"Imported {imported} notes using model '{args.model}'. "
                + (
                    "Planned phrase chunk card decks: "
                    f"{planned_chunk_deck_counts_text(payload_notes, args.deck)}."
                    if chunk_routing_enabled
                    else f"Target decks: {deck_counts_text(payload_notes)}."
                )
            )
            if skipped_duplicates:
                print(f"Skipped {skipped_duplicates} duplicate notes.")

        if chunk_routing_enabled and not args.dry_run:
            route_trvs_chunk_cards(client, affected_note_ids, base_deck=args.deck)
            print(
                "Routed generated cards into phrase chunk decks for "
                f"{len(affected_note_ids)} note(s)."
            )

        if args.verify_required_fields:
            verify_anki_required_fields(
                client,
                affected_note_ids,
                require_audio=args.require_audio,
            )
            print(f"Verified required TRVS-Lab fields in {len(affected_note_ids)} Anki note(s).")

        if not args.no_sync:
            client.invoke("sync")
            print("Triggered Anki sync.")
        return 0
    except AnkiImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
