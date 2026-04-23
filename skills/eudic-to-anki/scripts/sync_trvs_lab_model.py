#!/usr/bin/env python3
"""Sync the bundled TRVS-Lab Anki note type templates via AnkiConnect."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from ankiconnect_import import (
    DEFAULT_ANKI_URL,
    DEFAULT_MODEL_SPEC_PATH,
    STRUCTURED_VOCAB_MODEL,
    AnkiConnectClient,
    AnkiImportError,
    load_model_spec,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update the existing TRVS-Lab Anki note type with the bundled front/back "
            "templates and styling."
        )
    )
    parser.add_argument(
        "--model",
        default=STRUCTURED_VOCAB_MODEL,
        help=f"Anki note type name to update. Default: {STRUCTURED_VOCAB_MODEL}",
    )
    parser.add_argument(
        "--model-spec",
        default=str(DEFAULT_MODEL_SPEC_PATH),
        help="JSON model spec whose FrontPath/BackPath/css_path should be synced.",
    )
    parser.add_argument(
        "--anki-url",
        default=DEFAULT_ANKI_URL,
        help=f"AnkiConnect URL. Default: {DEFAULT_ANKI_URL}",
    )
    parser.add_argument(
        "--create-if-missing",
        action="store_true",
        help="Create the note type from the bundled spec if it does not exist yet.",
    )
    parser.add_argument(
        "--templates-only",
        action="store_true",
        help="Only update card front/back templates; leave styling unchanged.",
    )
    parser.add_argument(
        "--css-only",
        action="store_true",
        help="Only update note type styling; leave card templates unchanged.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load the bundled spec and print what would change without calling AnkiConnect.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip Anki sync after a successful update.",
    )
    return parser.parse_args()


def build_template_payload(spec: dict[str, Any]) -> dict[str, dict[str, str]]:
    templates: dict[str, dict[str, str]] = {}
    for template in spec.get("card_templates", []):
        name = template.get("Name")
        front = template.get("Front")
        back = template.get("Back")
        if not name or front is None or back is None:
            raise AnkiImportError(
                "Each card template in the model spec must include Name, Front, and Back."
            )
        templates[str(name)] = {"Front": str(front), "Back": str(back)}
    if not templates:
        raise AnkiImportError("Model spec does not contain any expanded card templates.")
    return templates


def describe_plan(
    *,
    model_name: str,
    spec: dict[str, Any],
    sync_templates: bool,
    sync_css: bool,
    create_if_missing: bool,
) -> None:
    print(f"Model: {model_name}")
    print(f"Fields in bundled spec: {', '.join(spec.get('fields', []))}")
    if sync_templates:
        names = [str(template.get("Name", "")) for template in spec.get("card_templates", [])]
        print(f"Templates to sync: {', '.join(name for name in names if name)}")
    else:
        print("Templates to sync: skipped")
    print(f"Styling to sync: {'yes' if sync_css else 'skipped'}")
    print(f"Create if missing: {'yes' if create_if_missing else 'no'}")


def create_model(client: AnkiConnectClient, spec: dict[str, Any]) -> None:
    client.invoke(
        "createModel",
        modelName=spec["model_name"],
        inOrderFields=spec["fields"],
        cardTemplates=spec["card_templates"],
        css=spec["css"],
    )


def sync_model_templates(client: AnkiConnectClient, model_name: str, spec: dict[str, Any]) -> None:
    client.invoke(
        "updateModelTemplates",
        model={"name": model_name, "templates": build_template_payload(spec)},
    )


def sync_model_styling(client: AnkiConnectClient, model_name: str, spec: dict[str, Any]) -> None:
    css = spec.get("css")
    if css is None:
        raise AnkiImportError("Model spec does not contain expanded CSS.")
    client.invoke("updateModelStyling", model={"name": model_name, "css": css})


def warn_on_field_mismatch(
    client: AnkiConnectClient,
    model_name: str,
    expected_fields: list[str],
) -> None:
    current_fields = client.invoke("modelFieldNames", modelName=model_name)
    missing = [field for field in expected_fields if field not in current_fields]
    extra = [field for field in current_fields if field not in expected_fields]
    if missing:
        print(f"Warning: existing note type is missing bundled field(s): {', '.join(missing)}")
    if extra:
        print(f"Warning: existing note type has extra field(s): {', '.join(extra)}")


def main() -> int:
    args = parse_args()
    if args.templates_only and args.css_only:
        print("Error: --templates-only and --css-only cannot be used together.", file=sys.stderr)
        return 2

    sync_templates = not args.css_only
    sync_css = not args.templates_only
    model_spec_path = Path(args.model_spec).expanduser()

    try:
        spec = load_model_spec(model_spec_path, args.model)
        if args.dry_run:
            describe_plan(
                model_name=args.model,
                spec=spec,
                sync_templates=sync_templates,
                sync_css=sync_css,
                create_if_missing=args.create_if_missing,
            )
            return 0

        client = AnkiConnectClient(args.anki_url)
        models = client.invoke("modelNames")
        model_exists = args.model in models

        if not model_exists:
            if not args.create_if_missing:
                raise AnkiImportError(
                    f"Anki note type not found: {args.model}. "
                    "Open Anki, then re-run with --create-if-missing to create it from the bundled spec."
                )
            create_model(client, spec)
            print(f"Created Anki note type '{args.model}' from bundled spec.")
        else:
            warn_on_field_mismatch(client, args.model, list(spec.get("fields", [])))
            if sync_templates:
                sync_model_templates(client, args.model, spec)
                print(f"Updated card template(s) for '{args.model}'.")
            if sync_css:
                sync_model_styling(client, args.model, spec)
                print(f"Updated styling for '{args.model}'.")

        if not args.no_sync:
            client.invoke("sync")
            print("Triggered Anki sync.")
        return 0
    except AnkiImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
