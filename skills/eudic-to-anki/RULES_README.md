# eudic-to-anki Rules README (Single File, Actually Usable)

This README is for agents.

Generate exactly one rules file:

- `~/.codex/rules/eudic-to-anki.rules`

Do not split into multiple rule files.

## Why network blocks can still happen

Even when rules exist, export may still be blocked if command shape does not match `prefix_rule`.

Most common mismatch causes:

1. Environment-variable prefix before command, for example:
  - `EUDIC_TO_ANKI_TEMP_DIR=... python3 ...`
2. Shell wrapper command, for example:
  - `/bin/zsh -lc 'python3 ...'`

Use direct command invocation instead.

## Hard requirements for generated rules

The single file must cover both execution shapes:

1. Relative script paths (skill root cwd), for example:
  - `python3 scripts/eudic_export.py ...`
2. Absolute installed-skill paths (automation cwd may differ), for example:
  - `python3 <SKILL_ROOT>/scripts/eudic_export.py ...`

Command families to include:

- `eudic_export.py`
- `run_with_login_zsh.py ... eudic_export.py`
- `ankiconnect_import.py`
- `edge_tts_runner.py` (direct probe/generation)
- `say` (offline fallback probe)
- `check_env.sh`
- `cleanup_import_artifacts.sh`
- `open -a Anki`

## How to discover `<SKILL_ROOT>` safely

Do not hardcode personal paths in docs/templates.
Discover at runtime:

```bash
find "$HOME/.agents/skills" -maxdepth 3 -type f -name SKILL.md | rg '/eudic-to-anki/SKILL.md$'
```

If found at `<SKILL_ROOT>/SKILL.md`, then use:

- `<SKILL_ROOT>/scripts/eudic_export.py`
- `<SKILL_ROOT>/scripts/run_with_login_zsh.py`
- `<SKILL_ROOT>/scripts/ankiconnect_import.py`
- `<SKILL_ROOT>/scripts/check_env.sh`
- `<SKILL_ROOT>/scripts/cleanup_import_artifacts.sh`

## Validation (must pass)

Validate against the same single file:

```bash
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 <SKILL_ROOT>/scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 <SKILL_ROOT>/scripts/ankiconnect_import.py --ping
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 <SKILL_ROOT>/scripts/edge_tts_runner.py --text test --output /tmp/test.mp3
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- say test
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- bash <SKILL_ROOT>/scripts/cleanup_import_artifacts.sh
```

Expected result for each command: `decision: allow`.

## Agent do/don't checklist

Do:

- Generate one file at `~/.codex/rules/eudic-to-anki.rules`.
- Include both relative and absolute command-prefix rules.
- Keep `match` examples date-agnostic.
- Restart Codex after rule changes.

Don't:

- Do not run export/import as `FOO=bar python3 ...` in automation.
- Do not wrap export/import in `/bin/zsh -lc '...'`.
- Do not claim rules are valid without `execpolicy check`.
- Do not conclude "Edge-TTS network broken" from a sandboxed probe command that did not match rules.

