"""Delete verified Eudic source words; retain only unfinished cleanup work."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from coach_fields import normalize_word_key
from context_anchor import encounter_id, note_learning_group
from eudic_export import (
    REQUEST_TIME_SOURCE,
    RequestController,
    RequestStats,
    acquire_export_lock,
    api_request,
    get_auth_header,
    release_export_lock,
    write_text_atomically,
)

PENDING_DIR_NAME = ".eudic-pending"
BATCH_SIZE = 100
VERIFY_SAMPLE_SIZE = 3
DELETE_PASSES_BY_STATE = {"in_source": 0, "detached": 1, "absent": 2}


class CleanupError(RuntimeError):
    """Local Anki data is saved, but Eudic cleanup is incomplete."""


def pending_directory() -> Path:
    root = os.getenv("EUDIC_TO_ANKI_TEMP_DIR")
    return (
        Path(root).expanduser()
        if root
        else Path.home() / "Documents" / "eudic-to-anki-temp"
    ) / PENDING_DIR_NAME


def _source_key(source: dict[str, Any]) -> tuple[str, str, str]:
    if not isinstance(source, dict):
        raise CleanupError(
            "eudic_source must contain language, category_id and original word."
        )
    values = tuple(source.get(key) for key in ("language", "category_id", "word"))
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise CleanupError(
            "Incomplete Eudic source identity; re-export instead of guessing deletion targets."
        )
    if values[0] not in {"en", "fr", "de", "es"}:
        raise CleanupError("Unsupported Eudic source language.")
    return values


def collect_targets(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets: dict[tuple[str, str, str], dict[str, Any]] = {}
    rejected: set[tuple[str, str, str]] = set()
    for note in notes:
        source = note.get("eudic_source")
        if source is None:
            continue  # Manual lists and old files without provenance cannot delete words.
        key = _source_key(source)
        if normalize_word_key(key[2]) != normalize_word_key(
            note.get("word") or note.get("单词")
        ):
            raise CleanupError("Eudic source word does not match its Anki note.")
        if str(note.get("category_id", "")) != key[1]:
            raise CleanupError("Eudic source category does not match its encounter.")
        if note_learning_group(note) == "reject":
            rejected.add(key)
            continue
        target = targets.setdefault(
            key,
            {
                "language": key[0],
                "category_id": key[1],
                "word": key[2],
                "encounter_ids": [],
            },
        )
        identity = encounter_id(note)
        if identity not in target["encounter_ids"]:
            target["encounter_ids"].append(identity)
    return [target for key, target in targets.items() if key not in rejected]


def _save(path: Path, receipt: dict[str, Any]) -> None:
    if not receipt["pending"]:
        path.unlink(missing_ok=True)
        return

    def write(handle: Any) -> None:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    write_text_atomically(path, write)


def save_verified_batch(
    targets: list[dict[str, Any]],
    verified: dict[str, int],
    *,
    anki_url: str,
    model: str,
    deck: str,
) -> Path | None:
    """Called only after the whole import, including non-Eudic notes, verifies."""
    if not targets:
        return None
    pending = []
    for target in targets:
        key = normalize_word_key(target["word"])
        if key not in verified:
            raise CleanupError("Cannot queue an unverified Eudic source word.")
        pending.append({**target, "note_id": verified[key]})
    path = pending_directory() / f"{uuid4().hex}.json"
    _save(
        path,
        {
            "version": 1,
            "anki_url": anki_url,
            "model": model,
            "deck": deck,
            "pending": pending,
        },
    )
    return path


def _load(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(receipt, dict)
        or receipt.get("version") != 1
        or receipt.get("model") != "TRVS-Lab"
    ):
        raise CleanupError(f"Invalid pending cleanup file: {path}")
    if not all(
        isinstance(receipt.get(key), str) and receipt[key]
        for key in ("anki_url", "deck")
    ):
        raise CleanupError(f"Missing Anki identity in pending cleanup file: {path}")
    if not isinstance(receipt.get("pending"), list):
        raise CleanupError(f"Missing pending targets: {path}")
    seen = set()
    for target in receipt["pending"]:
        key = _source_key(target)
        ids = target.get("encounter_ids")
        if (
            type(target.get("note_id")) is not int
            or target["note_id"] <= 0
            or not isinstance(ids, list)
            or not ids
            or any(not isinstance(value, str) or not value for value in ids)
            or key in seen
        ):
            raise CleanupError(f"Invalid pending target: {path}")
        seen.add(key)
    return receipt


def _sample_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(targets) <= VERIFY_SAMPLE_SIZE:
        return targets
    indexes = (0, len(targets) // 2, len(targets) - 1)
    return [targets[index] for index in indexes]


def _word_state(
    target: dict[str, Any], auth: str, controller: RequestController
) -> str:
    """Return the global/source state used to verify or resume a batch."""
    response = api_request(
        "/studylist/word",
        auth,
        query={"language": target["language"], "word": target["word"]},
        request_controller=controller,
        request_kind="verification",
        allow_not_found=True,
    )
    if response is None:
        return "absent"
    category_ids = response.get("category_ids") if isinstance(response, dict) else None
    returned_word = response.get("word") if isinstance(response, dict) else None
    if (
        not isinstance(returned_word, str)
        or normalize_word_key(returned_word) != normalize_word_key(target["word"])
        or not isinstance(category_ids, list)
        or any(not isinstance(value, (str, int)) for value in category_ids)
    ):
        raise CleanupError(
            "Cannot verify deletion: Eudic returned an invalid word response."
        )
    source_id = str(target["category_id"])
    return (
        "in_source"
        if source_id in {str(value) for value in category_ids}
        else "detached"
    )


def _sample_batch_state(
    targets: list[dict[str, Any]], auth: str, controller: RequestController
) -> str:
    states = [_word_state(target, auth, controller) for target in _sample_targets(targets)]
    return min(states, key=DELETE_PASSES_BY_STATE.__getitem__)


def _verify_batch_absent(
    targets: list[dict[str, Any]], auth: str, controller: RequestController
) -> None:
    for target in _sample_targets(targets):
        if _word_state(target, auth, controller) != "absent":
            raise CleanupError(
                f"Eudic cleanup verification failed: sampled word "
                f"{target['word']!r} still exists."
            )


def delete_pending(
    path: Path,
    *,
    reconcile: bool = False,
    controller: RequestController | None = None,
) -> int:
    receipt = _load(path)
    if not receipt["pending"]:
        _save(path, receipt)
        return 0
    auth = get_auth_header(None)
    if controller is None:
        controller = RequestController(RequestStats(), time_source=REQUEST_TIME_SOURCE)
    lock = acquire_export_lock()
    completed = 0
    try:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for target in receipt["pending"]:
            groups.setdefault((target["language"], target["category_id"]), []).append(
                target
            )
        for (language, category_id), targets in groups.items():
            for offset in range(0, len(targets), BATCH_SIZE):
                batch = targets[offset : offset + BATCH_SIZE]
                completed_passes = 0
                if reconcile:
                    state = _sample_batch_state(batch, auth, controller)
                    if state == "absent":
                        receipt["pending"] = [
                            target
                            for target in receipt["pending"]
                            if target not in batch
                        ]
                        completed += len(batch)
                        _save(path, receipt)
                        continue
                    completed_passes = 1 if state == "detached" else 0
                body = {
                    "language": language,
                    "category_id": category_id,
                    "words": [target["word"] for target in batch],
                }
                for _ in range(completed_passes, 2):
                    api_request(
                        "/studylist/words",
                        auth,
                        method="DELETE",
                        body=body,
                        request_controller=controller,
                        request_kind="delete",
                    )
                _verify_batch_absent(batch, auth, controller)
                receipt["pending"] = [
                    target for target in receipt["pending"] if target not in batch
                ]
                completed += len(batch)
                _save(path, receipt)
    finally:
        release_export_lock(lock)
    return completed


def resume_pending(
    client: Any, verify_import: Callable[..., dict[str, int]], *, anki_url: str
) -> int:
    paths = sorted(pending_directory().glob("*.json"))
    if not paths:
        print("No pending Eudic cleanup.")
        return 0
    completed = 0
    controller = RequestController(RequestStats(), time_source=REQUEST_TIME_SOURCE)
    for path in paths:
        receipt = _load(path)
        if receipt["anki_url"] != anki_url:
            raise CleanupError(
                "Pending cleanup belongs to a different Anki URL; use the original --anki-url."
            )
        notes = [
            {
                "word": target["word"],
                "encounter_id": identity,
                "learning_group": "learn",
            }
            for target in receipt["pending"]
            for identity in target["encounter_ids"]
        ]
        verified = verify_import(
            client, notes, model=receipt["model"], base_deck=receipt["deck"]
        )
        if any(
            verified.get(normalize_word_key(target["word"])) != target["note_id"]
            for target in receipt["pending"]
        ):
            raise CleanupError(
                "Pending source no longer matches its verified Anki note."
            )
        completed += delete_pending(path, reconcile=True, controller=controller)
    print(
        f"Eudic cleanup resumed: completed={completed}; no completed records retained."
    )
    return 0
