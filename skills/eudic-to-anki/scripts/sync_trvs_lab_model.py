#!/usr/bin/env python3
"""Check or fully synchronize the strict TRVS-Lab model contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ankiconnect_import import (
    DEFAULT_ANKI_URL,
    DEFAULT_MODEL_SPEC_PATH,
    STRUCTURED_VOCAB_MODEL,
    AnkiConnectClient,
    AnkiImportError,
)
from model_contract import (
    ModelApplyError,
    ModelContractError,
    anki_operation_lock,
    apply_model_plan,
    emit_blocked,
    emit_preflight,
    emit_update,
    inspect_model,
    load_model_spec,
    verify_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check or fully synchronize the one-card TRVS-Lab Context Anchor "
            "note type. Incompatible legacy models require manual migration."
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
        help="Complete model spec used as the strict synchronization target.",
    )
    parser.add_argument(
        "--anki-url",
        default=DEFAULT_ANKI_URL,
        help=f"AnkiConnect URL. Default: {DEFAULT_ANKI_URL}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report the model plan without modifying Anki.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Trigger Anki cloud sync after an exact model verification.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.model != STRUCTURED_VOCAB_MODEL:
        print(
            "Error: this command supports the one-card TRVS-Lab model only.",
            file=sys.stderr,
        )
        return 1

    try:
        spec = load_model_spec(Path(args.model_spec), args.model)
        with anki_operation_lock():
            client = AnkiConnectClient(args.anki_url)
            client.invoke("version")
            plan = inspect_model(client, spec)
            emit_preflight(plan)

            if args.check:
                if plan.action == "blocked":
                    emit_blocked(plan)
                    return 1
                return 0

            if plan.action == "blocked":
                emit_blocked(plan)
                return 1

            try:
                completed = apply_model_plan(client, plan)
            except ModelApplyError as exc:
                emit_update(exc.completed, exc.failed)
                raise
            emit_update(completed)
            verify_model(client, spec)
            if args.sync:
                client.invoke("sync")
                print("Triggered Anki sync.")
            return 0
    except (AnkiImportError, ModelContractError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
