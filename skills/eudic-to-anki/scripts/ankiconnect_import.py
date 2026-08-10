#!/usr/bin/env python3
"""Import one-card context-anchor vocabulary notes through AnkiConnect."""

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

from coach_fields import MANAGED_LEARNING_GROUPS, normalize_word_key
from context_anchor import (
    build_fields as build_context_anchor_fields,
    note_learning_group,
)

DEFAULT_ANKI_URL = "http://127.0.0.1:8765"
DEFAULT_DECK = "words"
STRUCTURED_VOCAB_MODEL = "TRVS-Lab"
DEFAULT_MODEL = STRUCTURED_VOCAB_MODEL
DEFAULT_AUDIO_FIELD = "发音"
DEFAULT_AUDIO_FORMAT = "mp3"
DEFAULT_AUDIO_VOICE = "en-US-GuyNeural"
API_VERSION = 6
CONTEXT_ANCHOR_TEMPLATE = "Context Anchor"
TRVS_REQUIRED_FIELDS = (
    "单词",
    "规范词形",
    "音标",
    "语境释义",
    "英英",
    "卡片例句",
    "例句来源",
    "遇见次数",
    "最近遇见",
    "遇见记录",
    "学习分组",
)
STATIC_TAGS_TO_DROP = {"english", "vocab", "eudic"}

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_MODEL_SPEC_PATH = SKILL_DIR / "assets" / "trvs_lab_model.json"
DEFAULT_ARTIFACT_DIR = Path.home() / "Documents" / "eudic-to-anki-temp"
DEFAULT_AUDIO_DIR = DEFAULT_ARTIFACT_DIR / "generated_audio"


class AnkiImportError(RuntimeError):
    """Raised when validation or an atomic import step fails."""


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
            raise AnkiImportError(
                f"AnkiConnect error for '{action}': {parsed['error']}"
            )
        return parsed.get("result")


def connection_help(url: str) -> str:
    return "\n".join(
        [
            f"Could not reach AnkiConnect at {url}.",
            "Open Anki Desktop, install/enable AnkiConnect (2055492159), restart Anki,",
            f"then retry with --anki-url {url}.",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import context-anchor vocabulary notes into Anki."
    )
    parser.add_argument("--input", help="JSON, CSV, or TSV structured-note file.")
    parser.add_argument("--deck", default=DEFAULT_DECK, help="Managed deck root.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-spec", default=str(DEFAULT_MODEL_SPEC_PATH))
    parser.add_argument("--no-ensure-model", action="store_true")
    parser.add_argument("--front-field", default="Front")
    parser.add_argument("--back-field", default="Back")
    parser.add_argument(
        "--audio-provider",
        choices=["none", "existing", "command"],
        default="none",
    )
    parser.add_argument("--audio-command")
    parser.add_argument("--audio-dir", default=str(DEFAULT_AUDIO_DIR))
    parser.add_argument("--audio-field", default=DEFAULT_AUDIO_FIELD)
    parser.add_argument("--audio-format", default=DEFAULT_AUDIO_FORMAT)
    parser.add_argument("--audio-voice", default=DEFAULT_AUDIO_VOICE)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--allow-duplicates", action="store_true")
    parser.add_argument("--dia-upsert", action="store_true")
    parser.add_argument("--preserve-progress-on-update", action="store_true")
    parser.add_argument("--create-deck", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--verify-required-fields", action="store_true")
    parser.add_argument("--no-sync", action="store_true")
    parser.add_argument("--ping", action="store_true")
    parser.add_argument("--anki-url", default=DEFAULT_ANKI_URL)
    # Retained only to fail clearly for old invocations.
    parser.add_argument(
        "--no-priority-decks", action="store_true", help=argparse.SUPPRESS
    )
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text == "-" else text


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def field_value(note: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if note.get(key) not in (None, ""):
            return normalize_text(note[key])
    return ""


def split_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        part.strip() for part in str(value).replace(";", ",").split(",") if part.strip()
    ]


def filter_static_tags(tags: list[str]) -> list[str]:
    return [tag for tag in tags if tag not in STATIC_TAGS_TO_DROP]


def load_notes(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        if isinstance(payload, dict) and isinstance(payload.get("notes"), list):
            return [dict(item) for item in payload["notes"]]
        raise AnkiImportError(
            "JSON input must be a list or an object with a notes array."
        )
    if path.suffix.lower() in {".csv", ".tsv"}:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle, delimiter=delimiter)]
    raise AnkiImportError("Unsupported input format. Use JSON, CSV, or TSV.")


def load_model_spec(path: Path, model_name: str) -> dict[str, Any]:
    if not path.is_file():
        raise AnkiImportError(f"Model spec not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["model_name"] = model_name
    base = path.parent
    payload["css"] = (base / payload["css_path"]).read_text(encoding="utf-8")
    templates: list[dict[str, str]] = []
    for raw in payload["card_templates"]:
        template = dict(raw)
        template["Front"] = (base / template.pop("FrontPath")).read_text(
            encoding="utf-8"
        )
        template["Back"] = (base / template.pop("BackPath")).read_text(encoding="utf-8")
        templates.append(template)
    payload["card_templates"] = templates
    return payload


def _template_map_from_spec(spec: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        str(template["Name"]): {
            "Front": str(template.get("Front") or ""),
            "Back": str(template.get("Back") or ""),
        }
        for template in spec.get("card_templates", [])
    }


def _model_templates_need_update(templates: Any) -> bool:
    if not isinstance(templates, dict) or set(templates) != {CONTEXT_ANCHOR_TEMPLATE}:
        return True
    template = templates[CONTEXT_ANCHOR_TEMPLATE] or {}
    front = str(template.get("Front") or "")
    back = str(template.get("Back") or "")
    return not (
        "{{单词}}" in front
        and "{{卡片例句}}" in front
        and "playAudio" in front
        and all(
            f"{{{{{field}}}}}" in back
            for field in (
                "语境释义",
                "音标",
                "英英",
                "来源词块",
                "词块释义",
                "词族构词",
                "历史语境",
                "遇见次数",
                "最近遇见",
            )
        )
        and "{{学习分组}}" not in back
    )


def _model_css_needs_update(styling: Any) -> bool:
    css = (
        str(styling.get("css") or "")
        if isinstance(styling, dict)
        else str(styling or "")
    )
    return "trvs-style-version: context-anchor-v1" not in css


def _migration_error(model_name: str) -> AnkiImportError:
    return AnkiImportError(
        f"{model_name} still contains a legacy or incompatible card model. "
        "Removing or renaming a generated card template in place can destroy scheduling data. "
        "Export a backup, delete the legacy TRVS-Lab notes/note type, then rerun the "
        "import to create the one-card Context Anchor model."
    )


def assert_model_migration_safe(client: AnkiConnectClient, model_name: str) -> None:
    models = client.invoke("modelNames") or []
    if model_name not in models:
        return
    templates = client.invoke("modelTemplates", modelName=model_name) or {}
    names = set(templates) if isinstance(templates, dict) else set()
    if names != {CONTEXT_ANCHOR_TEMPLATE}:
        raise _migration_error(model_name)


def ensure_model(
    client: AnkiConnectClient,
    model_name: str,
    *,
    ensure_if_missing: bool,
    model_spec_path: Path,
) -> None:
    models = client.invoke("modelNames") or []
    spec = load_model_spec(model_spec_path, model_name)
    if model_name not in models:
        if not ensure_if_missing:
            raise AnkiImportError(f"Anki note type not found: {model_name}")
        client.invoke(
            "createModel",
            modelName=model_name,
            inOrderFields=spec["fields"],
            cardTemplates=spec["card_templates"],
            css=spec["css"],
        )
        return
    assert_model_migration_safe(client, model_name)
    fields = client.invoke("modelFieldNames", modelName=model_name) or []
    for field in spec["fields"]:
        if field not in fields:
            client.invoke("modelFieldAdd", modelName=model_name, fieldName=field)
    templates = client.invoke("modelTemplates", modelName=model_name)
    if _model_templates_need_update(templates):
        client.invoke(
            "updateModelTemplates",
            model={"name": model_name, "templates": _template_map_from_spec(spec)},
        )
    styling = client.invoke("modelStyling", modelName=model_name)
    if _model_css_needs_update(styling):
        client.invoke(
            "updateModelStyling", model={"name": model_name, "css": spec["css"]}
        )


def managed_deck_name(base_deck: str, group: str) -> str:
    root = base_deck.strip() or DEFAULT_DECK
    if root.split("::")[-1] in MANAGED_LEARNING_GROUPS:
        root = "::".join(root.split("::")[:-1])
    return f"{root}::{group}"


def managed_decks(base_deck: str) -> list[str]:
    return [managed_deck_name(base_deck, group) for group in MANAGED_LEARNING_GROUPS]


def ensure_deck(
    client: AnkiConnectClient, deck_name: str, create_if_missing: bool
) -> None:
    decks = client.invoke("deckNames") or []
    if deck_name in decks:
        return
    if not create_if_missing:
        raise AnkiImportError(
            f"Anki deck not found: {deck_name}. Re-run with --create-deck."
        )
    client.invoke("createDeck", deck=deck_name)


def build_trvs_lab_fields(
    note: dict[str, Any],
    audio_html: str,
    *,
    existing_fields: dict[str, Any] | None = None,
    forced_group: str | None = None,
) -> dict[str, str]:
    fields, _changed = build_context_anchor_fields(
        note,
        audio_html,
        existing_fields=existing_fields,
        forced_group=forced_group,
    )
    return fields


def _field_text_value(raw: Any) -> str:
    if isinstance(raw, dict):
        raw = raw.get("value")
    return normalize_text(raw)


def _missing_required_field_names(
    fields: dict[str, Any], require_audio: bool
) -> list[str]:
    required = list(TRVS_REQUIRED_FIELDS)
    if require_audio:
        required.append("发音")
    missing: list[str] = []
    for name in required:
        value = _field_text_value(fields.get(name))
        if not value or (name == "发音" and not value.startswith("[sound:")):
            missing.append(name)
    return missing


def verify_payload_required_fields(
    payloads: list[dict[str, Any]], *, require_audio: bool
) -> None:
    problems: list[str] = []
    for payload in payloads:
        fields = payload.get("fields") or {}
        missing = _missing_required_field_names(fields, require_audio)
        if missing:
            word = _field_text_value(fields.get("单词")) or "<unknown>"
            problems.append(f"{word}: missing/invalid {', '.join(missing)}")
    if problems:
        raise AnkiImportError("Required TRVS-Lab fields failed: " + "; ".join(problems))


def _search_term(field: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{field}:"{escaped}"'


def find_context_anchor_note_ids(
    client: AnkiConnectClient, model: str, word: str
) -> list[int]:
    model_escaped = model.replace("\\", "\\\\").replace('"', '\\"')
    key = normalize_word_key(word)
    query = f'note:"{model_escaped}" {_search_term("规范词形", key)}'
    ids = [int(item) for item in (client.invoke("findNotes", query=query) or [])]
    if ids:
        return list(dict.fromkeys(ids))
    legacy_query = f'note:"{model_escaped}" {_search_term("单词", word.strip())}'
    return list(
        dict.fromkeys(
            int(item) for item in (client.invoke("findNotes", query=legacy_query) or [])
        )
    )


def _managed_group_for_info(
    client: AnkiConnectClient, info: dict[str, Any], base_deck: str
) -> tuple[str, list[int], str]:
    cards = [int(card) for card in info.get("cards") or []]
    if len(cards) != 1:
        raise _migration_error(STRUCTURED_VOCAB_MODEL)
    card_infos = client.invoke("cardsInfo", cards=cards) or []
    if len(card_infos) != 1:
        raise AnkiImportError(
            "cardsInfo did not return the single Context Anchor card."
        )
    current_deck = str(card_infos[0].get("deckName") or "")
    root = base_deck.strip() or DEFAULT_DECK
    for group in MANAGED_LEARNING_GROUPS:
        if current_deck == managed_deck_name(root, group):
            return group, cards, current_deck
    stored = _field_text_value((info.get("fields") or {}).get("学习分组"))
    group = stored if stored in MANAGED_LEARNING_GROUPS else "defer"
    return group, cards, current_deck


def _group_notes(notes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    order: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for note in notes:
        if note_learning_group(note) == "reject":
            continue
        word = field_value(note, "word", "单词")
        if not word:
            raise AnkiImportError("Every importable note needs word/单词.")
        key = normalize_word_key(word)
        if key not in grouped:
            order.append(key)
            grouped[key] = []
        grouped[key].append(note)
    for group in grouped.values():
        group.sort(
            key=lambda note: field_value(
                note, "add_time_utc", "add_time_local", "encountered_at"
            )
        )
    return [grouped[key] for key in order]


def _tags_for_note(
    note: dict[str, Any], global_tags: list[str], *, group: str | None = None
) -> list[str]:
    group = group or note_learning_group(note)
    tags = [*global_tags, *split_tags(note.get("tags")), f"group::{group}"]
    return sorted(set(filter_static_tags(tags)))


def upsert_context_anchor_notes(
    client: AnkiConnectClient,
    notes: list[dict[str, Any]],
    *,
    base_deck: str,
    model: str,
    global_tags: list[str] | None = None,
    preserve_progress_on_update: bool = False,
    require_audio: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Apply one-note-per-normalized-word behavior at the AnkiConnect boundary."""
    if preserve_progress_on_update:
        raise AnkiImportError(
            "Context Anchor updates always reset the single card for a distinct encounter."
        )
    summary = {
        "new": 0,
        "updated": 0,
        "defer_to_learn": 0,
        "idempotent": 0,
        "reset": 0,
        "reject": sum(note_learning_group(note) == "reject" for note in notes),
    }
    for note_group in _group_notes(notes):
        latest = note_group[-1]
        word = field_value(latest, "word", "单词")
        note_ids = find_context_anchor_note_ids(client, model, word)
        if len(note_ids) > 1:
            raise AnkiImportError(
                f"Found {len(note_ids)} notes for normalized word {normalize_word_key(word)!r}; "
                "merge/delete duplicates before importing."
            )
        if note_ids:
            info_rows = client.invoke("notesInfo", notes=note_ids) or []
            if len(info_rows) != 1:
                raise AnkiImportError("notesInfo did not return the matched note.")
            info = info_rows[0]
            existing_fields = info.get("fields") or {}
            current_group, cards, current_deck = _managed_group_for_info(
                client, info, base_deck
            )
            fields: dict[str, str] | None = None
            changed = False
            target_group = current_group
            for note in note_group:
                candidate_group = current_group
                if current_group == "defer":
                    candidate_group = "learn"
                fields, item_changed = build_context_anchor_fields(
                    note,
                    field_value(note, "audio_html", "发音"),
                    existing_fields=fields or existing_fields,
                    forced_group=candidate_group,
                )
                if item_changed:
                    changed = True
                    target_group = candidate_group
            if not changed or fields is None:
                summary["idempotent"] += 1
                continue
            if current_group == "defer" and target_group == "learn":
                summary["defer_to_learn"] += 1
            fields["学习分组"] = target_group
            summary["updated"] += 1
            summary["reset"] += 1
            verify_payload_required_fields(
                [{"fields": fields}], require_audio=require_audio
            )
            if dry_run:
                continue
            client.invoke(
                "updateNote",
                note={
                    "id": note_ids[0],
                    "fields": fields,
                    "tags": _tags_for_note(
                        latest, global_tags or [], group=target_group
                    ),
                },
            )
            client.invoke("forgetCards", cards=cards)
            target_deck = managed_deck_name(base_deck, target_group)
            if current_deck != target_deck:
                client.invoke("changeDeck", cards=cards, deck=target_deck)
            continue

        fields: dict[str, str] | None = None
        for note in note_group:
            fields, _changed = build_context_anchor_fields(
                note,
                field_value(note, "audio_html", "发音"),
                existing_fields=fields,
            )
        assert fields is not None
        verify_payload_required_fields(
            [{"fields": fields}], require_audio=require_audio
        )
        summary["new"] += 1
        if dry_run:
            continue
        payload = {
            "deckName": managed_deck_name(base_deck, fields["学习分组"]),
            "modelName": model,
            "fields": fields,
            "tags": _tags_for_note(latest, global_tags or [], group=fields["学习分组"]),
            "options": {"allowDuplicate": False},
        }
        note_id = client.invoke("addNote", note=payload)
        if note_id is None:
            raise AnkiImportError(f"Anki refused new note for {word!r}.")
    return summary


def sanitize_filename(text: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._")
    return base or "audio"


def _validate_mp3(path: Path, *, word: str) -> None:
    if not path.is_file() or path.stat().st_size < 4:
        raise AnkiImportError(f"Audio for {word!r} is missing or empty: {path}")
    with path.open("rb") as handle:
        header = handle.read(3)
    if header != b"ID3" and not (header[0] == 0xFF and header[1] & 0xE0 == 0xE0):
        raise AnkiImportError(f"Audio for {word!r} is not a valid MP3: {path}")


def generate_audio_with_command(
    *,
    command_template: str,
    word: str,
    text: str,
    output_path: Path,
    voice: str,
) -> Path:
    """Run the configured service twice at most; never switch providers or voices."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        template_args = shlex.split(command_template)
    except ValueError as exc:
        raise AnkiImportError(f"Invalid --audio-command template: {exc}") from exc
    if not template_args:
        raise AnkiImportError("--audio-command must not be empty.")
    values = {"word": word, "text": text, "output": str(output_path), "voice": voice}
    try:
        command = [part.format(**values) for part in template_args]
    except KeyError as exc:
        raise AnkiImportError(
            f"Unsupported --audio-command placeholder {exc.args[0]!r}."
        ) from exc

    reasons: list[str] = []
    for attempt in (1, 2):
        if output_path.exists():
            output_path.unlink()
        try:
            subprocess.run(
                command,
                shell=False,
                check=True,
                cwd=Path.cwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _validate_mp3(output_path, word=word)
            return output_path
        except OSError as exc:
            output_path.unlink(missing_ok=True)
            raise AnkiImportError(
                "Audio generation configuration failed before retry: "
                f"service=edge-tts word={word!r} voice={voice!r} attempts=1 "
                f"reason={exc}"
            ) from exc
        except (subprocess.CalledProcessError, AnkiImportError) as exc:
            if isinstance(exc, subprocess.CalledProcessError):
                reason = (exc.stderr or exc.stdout or str(exc)).strip()
            else:
                reason = str(exc)
            reasons.append(reason or f"attempt {attempt} failed")
    output_path.unlink(missing_ok=True)
    raise AnkiImportError(
        "Audio generation aborted before Anki note/card changes: "
        f"service=edge-tts word={word!r} voice={voice!r} attempts=2 "
        f"reason={reasons[-1]}"
    )


def _audio_source(note: dict[str, Any]) -> Path | None:
    for key in ("audio_path", "audio_file", "audio_source_path"):
        if note.get(key):
            return Path(str(note[key]))
    return None


def reuse_existing_anki_audio(
    client: AnkiConnectClient, notes: list[dict[str, Any]], *, model: str
) -> None:
    """Hydrate missing input audio from an existing note without mutating Anki."""
    by_key: dict[str, list[dict[str, Any]]] = {}
    for note in notes:
        if note_learning_group(note) == "reject":
            continue
        key = normalize_word_key(field_value(note, "word", "单词"))
        by_key.setdefault(key, []).append(note)
    for key, grouped_notes in by_key.items():
        if any(
            field_value(note, "audio_html", "发音").startswith("[sound:")
            for note in grouped_notes
        ):
            continue
        note_ids = find_context_anchor_note_ids(
            client, model, field_value(grouped_notes[-1], "word", "单词")
        )
        if len(note_ids) > 1:
            raise AnkiImportError(
                f"Found duplicate Anki notes while looking up audio for {key!r}."
            )
        if not note_ids:
            continue
        infos = client.invoke("notesInfo", notes=note_ids) or []
        if len(infos) != 1:
            raise AnkiImportError(f"notesInfo could not read audio for {key!r}.")
        sound = _field_text_value((infos[0].get("fields") or {}).get("发音"))
        if not sound.startswith("[sound:"):
            continue
        for note in grouped_notes:
            note["audio_html"] = sound


def prepare_all_audio(
    notes: list[dict[str, Any]],
    *,
    provider: str,
    command_template: str | None,
    audio_dir: Path,
    audio_format: str,
    voice: str,
) -> dict[str, Path]:
    """Generate and validate every file locally before any Anki mutation."""
    pending: dict[str, Path] = {}
    importable = [note for note in notes if note_learning_group(note) != "reject"]
    if not importable:
        return pending
    generated: list[Path] = []
    try:
        if provider == "command":
            if not command_template:
                raise AnkiImportError(
                    "Audio provider 'command' requires --audio-command."
                )
            probe = generate_audio_with_command(
                command_template=command_template or "",
                word="audio-service-probe",
                text="audio service probe",
                output_path=audio_dir / "_edge_tts_probe.mp3",
                voice=voice,
            )
            probe.unlink(missing_ok=True)
        for note in importable:
            if field_value(note, "audio_html", "发音").startswith("[sound:"):
                continue
            word = field_value(note, "word", "单词")
            key = normalize_word_key(word)
            if key in pending or provider == "none":
                continue
            filename = f"{sanitize_filename(key)}.{audio_format.lstrip('.')}"
            if provider == "existing":
                source = _audio_source(note)
                if source is None:
                    raise AnkiImportError(f"No explicit audio file for {word!r}.")
                _validate_mp3(source, word=word)
                pending[key] = source
            elif provider == "command":
                generated_path = generate_audio_with_command(
                    command_template=command_template or "",
                    word=word,
                    text=word,
                    output_path=audio_dir / filename,
                    voice=voice,
                )
                pending[key] = generated_path
                generated.append(generated_path)
    except Exception:
        for path in generated:
            path.unlink(missing_ok=True)
        (audio_dir / "_edge_tts_probe.mp3").unlink(missing_ok=True)
        raise
    return pending


def upload_prepared_audio(
    client: AnkiConnectClient,
    notes: list[dict[str, Any]],
    prepared: dict[str, Path],
    *,
    audio_format: str,
) -> None:
    stored: dict[str, str] = {}
    for key, path in prepared.items():
        filename = f"{sanitize_filename(key)}.{audio_format.lstrip('.')}"
        result = client.invoke(
            "storeMediaFile", filename=filename, path=str(path.resolve())
        )
        stored[key] = str(result or filename)
    for note in notes:
        key = normalize_word_key(field_value(note, "word", "单词"))
        if key in stored:
            note["audio_html"] = f"[sound:{stored[key]}]"


def _summary_text(summary: dict[str, int]) -> str:
    return ", ".join(f"{name}={value}" for name, value in summary.items())


def main() -> int:
    generated_audio_to_clean: list[Path] = []
    try:
        args = parse_args()
        client = AnkiConnectClient(args.anki_url)
        version = client.invoke("version")
        if args.ping and not args.input:
            print(f"AnkiConnect is reachable at {args.anki_url} (version {version}).")
            return 0
        if not args.input:
            raise AnkiImportError("--input is required unless only --ping is used.")
        if args.model != STRUCTURED_VOCAB_MODEL:
            raise AnkiImportError(
                "This importer now supports the one-card TRVS-Lab model only."
            )
        if args.no_priority_decks:
            raise AnkiImportError(
                "--no-priority-decks is incompatible with managed learn/defer/skip decks."
            )
        if args.preserve_progress_on_update:
            raise AnkiImportError(
                "Context Anchor updates always reset the card for a distinct encounter."
            )
        if args.allow_duplicates:
            raise AnkiImportError(
                "Context Anchor enforces one note per normalized word; duplicates cannot be enabled."
            )
        input_path = Path(args.input)
        if not input_path.is_file():
            raise AnkiImportError(f"Input file not found: {input_path}")
        notes = load_notes(input_path)
        if not notes:
            raise AnkiImportError("Input did not contain notes.")

        assert_model_migration_safe(client, args.model)
        if args.dry_run:
            summary = upsert_context_anchor_notes(
                client,
                notes,
                base_deck=args.deck,
                model=args.model,
                global_tags=args.tag,
                preserve_progress_on_update=args.preserve_progress_on_update,
                require_audio=args.require_audio,
                dry_run=True,
            )
            counts = {
                group: sum(note_learning_group(note) == group for note in notes)
                for group in (*MANAGED_LEARNING_GROUPS, "reject")
            }
            print(f"Classification: {_summary_text(counts)}")
            print(f"Import preview: {_summary_text(summary)}")
            return 0

        reuse_existing_anki_audio(client, notes, model=args.model)
        prepared = prepare_all_audio(
            notes,
            provider=args.audio_provider,
            command_template=args.audio_command,
            audio_dir=Path(args.audio_dir),
            audio_format=args.audio_format,
            voice=args.audio_voice,
        )
        if args.audio_provider == "command":
            generated_audio_to_clean = list(prepared.values())
        ensure_model(
            client,
            args.model,
            ensure_if_missing=not args.no_ensure_model,
            model_spec_path=Path(args.model_spec),
        )
        for deck in managed_decks(args.deck):
            ensure_deck(client, deck, args.create_deck)
        upload_prepared_audio(client, notes, prepared, audio_format=args.audio_format)
        summary = upsert_context_anchor_notes(
            client,
            notes,
            base_deck=args.deck,
            model=args.model,
            global_tags=args.tag,
            preserve_progress_on_update=args.preserve_progress_on_update,
            require_audio=args.require_audio,
        )
        print(f"Context Anchor import: {_summary_text(summary)}")
        if not args.no_sync:
            client.invoke("sync")
            print("Triggered Anki sync.")
        return 0
    except (AnkiImportError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        for path in generated_audio_to_clean:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
