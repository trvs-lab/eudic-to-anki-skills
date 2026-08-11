#!/usr/bin/env python3
"""Strict shared contract for the bundled TRVS-Lab Anki note type."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from context_anchor import CONTEXT_ANCHOR_FIELDS


CONTEXT_ANCHOR_TEMPLATE = "Context Anchor"
LEGACY_TRVS_FIELDS = frozenset(
    {
        "释义",
        "词根",
        "例句",
        "学习标记",
        "目标短语块",
        "短语块锚点",
        "短语块例句",
        "短语块挖空",
        "常用搭配",
    }
)
MODEL_LOCK_PATH = (
    Path(tempfile.gettempdir()) / f"eudic-to-anki-anki-{os.getuid()}.lock"
)
SHORT_HASH_LENGTH = 12


class ModelContractError(RuntimeError):
    """Raised when the model contract cannot be loaded, applied, or verified."""


class ModelLockError(ModelContractError):
    """Raised when another Anki import or model sync owns the shared lock."""


class ModelApplyError(ModelContractError):
    def __init__(self, completed: tuple[str, ...], failed: str, cause: Exception) -> None:
        self.completed = completed
        self.failed = failed
        self.error_type = type(cause).__name__
        super().__init__(
            f"model update failed at {failed}: error_type={self.error_type}"
        )


@dataclass(frozen=True)
class ModelSpec:
    model_name: str
    fields: tuple[str, ...]
    front: str
    back: str
    css: str
    source_path: Path
    front_hash: str
    back_hash: str
    css_hash: str
    fingerprint: str

    def template_list(self) -> list[dict[str, str]]:
        return [
            {
                "Name": CONTEXT_ANCHOR_TEMPLATE,
                "Front": self.front,
                "Back": self.back,
            }
        ]

    def template_map(self) -> dict[str, dict[str, str]]:
        return {
            CONTEXT_ANCHOR_TEMPLATE: {
                "Front": self.front,
                "Back": self.back,
            }
        }


@dataclass(frozen=True)
class ModelPlan:
    spec: ModelSpec
    action: str
    front: str
    back: str
    css: str
    missing_fields: tuple[str, ...] = ()
    extra_fields: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    note_count: int | None = None
    current_front_hash: str | None = None
    current_back_hash: str | None = None
    current_css_hash: str | None = None
    current_fingerprint: str | None = None

    def mismatched_components(self) -> tuple[str, ...]:
        components = [
            name
            for name, state in (
                ("front", self.front),
                ("back", self.back),
                ("css", self.css),
            )
            if state != "exact"
        ]
        if self.missing_fields:
            components.append("fields")
        if self.issues:
            components.append("structure")
        return tuple(components)


def normalize_model_text(value: str) -> str:
    """Normalize only CRLF and the number of terminal LF characters."""
    normalized = value.replace("\r\n", "\n")
    return normalized.rstrip("\n") + "\n"


def _content_hash(value: str) -> str:
    return hashlib.sha256(normalize_model_text(value).encode("utf-8")).hexdigest()


def _fingerprint(front_hash: str, back_hash: str, css_hash: str) -> str:
    payload = "\n".join((front_hash, back_hash, css_hash)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def short_hash(value: str | None) -> str:
    return value[:SHORT_HASH_LENGTH] if value else "missing"


def _read_required_text(base: Path, raw_path: Any, label: str) -> str:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ModelContractError(f"model spec {label} must be a non-empty path")
    path = (base / raw_path).resolve()
    if not path.is_file():
        raise ModelContractError(f"model spec {label} not found: {path}")
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ModelContractError(
            f"model spec {label} cannot be read: {path}: {exc}"
        ) from exc
    if not value:
        raise ModelContractError(f"model spec {label} is empty: {path}")
    return value


def load_model_spec(path: Path, model_name: str) -> ModelSpec:
    source_path = path.expanduser().resolve()
    if not source_path.is_file():
        raise ModelContractError(f"model spec not found: {source_path}")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelContractError(f"invalid model spec: {source_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ModelContractError("model spec root must be an object")
    if payload.get("model_name") != model_name:
        raise ModelContractError(
            f"model spec name must be {model_name!r}, got {payload.get('model_name')!r}"
        )

    raw_fields = payload.get("fields")
    if (
        not isinstance(raw_fields, list)
        or not raw_fields
        or any(not isinstance(field, str) or not field for field in raw_fields)
        or len(set(raw_fields)) != len(raw_fields)
    ):
        raise ModelContractError(
            "model spec fields must be a non-empty list of unique strings"
        )
    missing_contract_fields = [
        field for field in CONTEXT_ANCHOR_FIELDS if field not in raw_fields
    ]
    if missing_contract_fields:
        raise ModelContractError(
            "model spec fields are missing required Context Anchor fields: "
            + ", ".join(missing_contract_fields)
        )
    legacy_spec_fields = sorted(set(raw_fields) & LEGACY_TRVS_FIELDS)
    if legacy_spec_fields:
        raise ModelContractError(
            "model spec fields contain legacy fields: "
            + ", ".join(legacy_spec_fields)
        )

    raw_templates = payload.get("card_templates")
    if not isinstance(raw_templates, list) or len(raw_templates) != 1:
        raise ModelContractError(
            "model spec must contain exactly one Context Anchor template"
        )
    raw_template = raw_templates[0]
    if (
        not isinstance(raw_template, dict)
        or raw_template.get("Name") != CONTEXT_ANCHOR_TEMPLATE
    ):
        raise ModelContractError(
            "model spec template must be named Context Anchor"
        )

    base = source_path.parent
    front = _read_required_text(base, raw_template.get("FrontPath"), "FrontPath")
    back = _read_required_text(base, raw_template.get("BackPath"), "BackPath")
    css = _read_required_text(base, payload.get("css_path"), "css_path")
    front_hash = _content_hash(front)
    back_hash = _content_hash(back)
    css_hash = _content_hash(css)
    return ModelSpec(
        model_name=model_name,
        fields=tuple(raw_fields),
        front=front,
        back=back,
        css=css,
        source_path=source_path,
        front_hash=front_hash,
        back_hash=back_hash,
        css_hash=css_hash,
        fingerprint=_fingerprint(front_hash, back_hash, css_hash),
    )


def _component_text(templates: Any, component: str) -> str:
    if not isinstance(templates, dict):
        return ""
    template = templates.get(CONTEXT_ANCHOR_TEMPLATE)
    if not isinstance(template, dict):
        return ""
    value = template.get(component)
    return value if isinstance(value, str) else ""


def _model_note_count(client: Any, model_name: str) -> int:
    escaped = model_name.replace('"', '\\"')
    note_ids = client.invoke("findNotes", query=f'note:"{escaped}"') or []
    return len(note_ids)


def inspect_model(client: Any, spec: ModelSpec) -> ModelPlan:
    models = client.invoke("modelNames") or []
    if spec.model_name not in models:
        return ModelPlan(
            spec=spec,
            action="create",
            front="create",
            back="create",
            css="create",
            missing_fields=spec.fields,
        )

    templates = client.invoke("modelTemplates", modelName=spec.model_name) or {}
    fields = tuple(client.invoke("modelFieldNames", modelName=spec.model_name) or [])
    styling = client.invoke("modelStyling", modelName=spec.model_name) or {}
    template_names = set(templates) if isinstance(templates, dict) else set()
    current_fields = set(fields)
    missing_fields = tuple(field for field in spec.fields if field not in current_fields)
    extra_fields = tuple(sorted(current_fields - set(spec.fields)))
    legacy_fields = tuple(sorted(current_fields & LEGACY_TRVS_FIELDS))
    issues: list[str] = []
    if template_names != {CONTEXT_ANCHOR_TEMPLATE}:
        rendered = ", ".join(sorted(str(name) for name in template_names)) or "none"
        issues.append(
            f"card templates are {rendered}, expected {CONTEXT_ANCHOR_TEMPLATE}"
        )
    if legacy_fields:
        issues.append(f"legacy fields remain: {', '.join(legacy_fields)}")

    current_front = _component_text(templates, "Front")
    current_back = _component_text(templates, "Back")
    css_value = styling.get("css") if isinstance(styling, dict) else styling
    current_css = css_value if isinstance(css_value, str) else ""
    current_front_hash = _content_hash(current_front)
    current_back_hash = _content_hash(current_back)
    current_css_hash = _content_hash(current_css)
    current_fingerprint = _fingerprint(
        current_front_hash, current_back_hash, current_css_hash
    )

    if issues:
        return ModelPlan(
            spec=spec,
            action="blocked",
            front="blocked" if template_names != {CONTEXT_ANCHOR_TEMPLATE} else (
                "exact" if current_front_hash == spec.front_hash else "change"
            ),
            back="blocked" if template_names != {CONTEXT_ANCHOR_TEMPLATE} else (
                "exact" if current_back_hash == spec.back_hash else "change"
            ),
            css="exact" if current_css_hash == spec.css_hash else "change",
            missing_fields=missing_fields,
            extra_fields=extra_fields,
            issues=tuple(issues),
            note_count=_model_note_count(client, spec.model_name),
            current_front_hash=current_front_hash,
            current_back_hash=current_back_hash,
            current_css_hash=current_css_hash,
            current_fingerprint=current_fingerprint,
        )

    front_state = "exact" if current_front_hash == spec.front_hash else "change"
    back_state = "exact" if current_back_hash == spec.back_hash else "change"
    css_state = "exact" if current_css_hash == spec.css_hash else "change"
    action = (
        "none"
        if not missing_fields
        and front_state == back_state == css_state == "exact"
        else "update"
    )
    return ModelPlan(
        spec=spec,
        action=action,
        front=front_state,
        back=back_state,
        css=css_state,
        missing_fields=missing_fields,
        extra_fields=extra_fields,
        current_front_hash=current_front_hash,
        current_back_hash=current_back_hash,
        current_css_hash=current_css_hash,
        current_fingerprint=current_fingerprint,
    )


def emit_preflight(plan: ModelPlan) -> None:
    print(
        "Model preflight: "
        f"action={plan.action} "
        f"front={plan.front} back={plan.back} css={plan.css} "
        f"missing_fields={len(plan.missing_fields)} "
        f"extra_fields={len(plan.extra_fields)} "
        f"migration_issues={len(plan.issues)} "
        f"spec={plan.spec.source_path} "
        f"target={short_hash(plan.spec.fingerprint)} "
        f"current={short_hash(plan.current_fingerprint)}"
    )
    print(
        "Model hashes: "
        f"front={short_hash(plan.current_front_hash)}/{short_hash(plan.spec.front_hash)} "
        f"back={short_hash(plan.current_back_hash)}/{short_hash(plan.spec.back_hash)} "
        f"css={short_hash(plan.current_css_hash)}/{short_hash(plan.spec.css_hash)}"
    )
    if plan.missing_fields:
        print(f"Model fields: missing={','.join(plan.missing_fields)}")
    if plan.extra_fields:
        print(f"Model warning: extra_fields={','.join(plan.extra_fields)}")


def emit_blocked(plan: ModelPlan) -> None:
    for issue in plan.issues:
        print(f"Model migration issue: {issue}")
    print(f"Model migration: note_count={plan.note_count or 0}")
    print("Model migration step 1: back up the complete Anki collection")
    print(f"Model migration step 2: delete old {plan.spec.model_name} notes")
    print(f"Model migration step 3: delete the old {plan.spec.model_name} note type")
    print("Model migration step 4: rerun the import to create the current model")


def apply_model_plan(client: Any, plan: ModelPlan) -> tuple[str, ...]:
    if plan.action == "blocked":
        raise ModelContractError("blocked model cannot be updated automatically")
    if plan.action == "none":
        return ()

    completed: list[str] = []
    failed = "create"
    try:
        if plan.action == "create":
            client.invoke(
                "createModel",
                modelName=plan.spec.model_name,
                inOrderFields=list(plan.spec.fields),
                cardTemplates=plan.spec.template_list(),
                css=plan.spec.css,
            )
            completed.append("create")
            return tuple(completed)

        if plan.missing_fields:
            failed = "fields"
            for field in plan.missing_fields:
                client.invoke(
                    "modelFieldAdd",
                    modelName=plan.spec.model_name,
                    fieldName=field,
                )
            completed.append("fields")
        if plan.front == "change" or plan.back == "change":
            failed = "templates"
            client.invoke(
                "updateModelTemplates",
                model={
                    "name": plan.spec.model_name,
                    "templates": plan.spec.template_map(),
                },
            )
            completed.append("templates")
        if plan.css == "change":
            failed = "css"
            client.invoke(
                "updateModelStyling",
                model={"name": plan.spec.model_name, "css": plan.spec.css},
            )
            completed.append("css")
        return tuple(completed)
    except Exception as exc:
        raise ModelApplyError(tuple(completed), failed, exc) from exc


def emit_update(completed: tuple[str, ...], failed: str | None = None) -> None:
    print(
        "Model update: "
        f"completed={','.join(completed) if completed else 'none'} "
        f"failed={failed or 'none'}"
    )


def verify_model(client: Any, spec: ModelSpec) -> ModelPlan:
    verification = inspect_model(client, spec)
    if verification.action != "none":
        mismatches = ",".join(verification.mismatched_components()) or "unknown"
        print(
            "Model verify: "
            f"status=mismatch components={mismatches} "
            f"current={short_hash(verification.current_fingerprint)} "
            f"target={short_hash(spec.fingerprint)}"
        )
        raise ModelContractError(
            f"model verification failed: mismatched components={mismatches}"
        )
    print(
        "Model verify: "
        f"status=exact current={short_hash(verification.current_fingerprint)} "
        f"target={short_hash(spec.fingerprint)}"
    )
    return verification


@contextmanager
def anki_operation_lock() -> Iterator[None]:
    MODEL_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_LOCK_PATH.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ModelLockError(
                "another Anki import or model sync is already running; "
                "this command will not wait or retry"
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
