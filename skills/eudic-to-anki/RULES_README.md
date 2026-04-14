# Eudic-to-Anki Rules Playbook (Single-File)

This guide tells an agent to generate one working Codex rules file for
`eudic-to-anki` automation:

- `~/.codex/rules/eudic-to-anki.rules`

Do not split into multiple rule files.

## Objective

The single rules file must cover both command shapes:

- Relative script execution (for example: `python3 scripts/eudic_export.py ...`)
- Absolute installed-skill execution (for example: `python3 <SKILL_ROOT>/scripts/eudic_export.py ...`)

If only one shape is covered, automation may still fail in sandbox mode.

## Key Rules Facts

- `pattern` uses exact command-prefix matching.
- `match` entries are inline tests for verification.
- Do not rely on wildcard path expansion in `pattern`.
- Restart Codex after editing rules so changes are loaded.

Reference: [Codex Rules](https://developers.openai.com/codex/rules)

## Required Output File

- `~/.codex/rules/eudic-to-anki.rules`

This file should include:

- Relative-path rules for skill-root execution.
- Absolute-path rules based on discovered local install path.

## Command Families To Cover

- `python3 scripts/eudic_export.py`
- `python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py`
- `python3 scripts/ankiconnect_import.py`
- `bash scripts/check_env.sh`
- `bash scripts/cleanup_import_artifacts.sh`
- `open -a Anki`

Plus the same families with absolute scripts under discovered `<SKILL_ROOT>`.

## Discover `<SKILL_ROOT>` (No Hardcoded User Path)

Use discovery commands with `$HOME`:

```bash
find "$HOME/.agents/skills" -maxdepth 3 -type f -name SKILL.md | rg '/eudic-to-anki/SKILL.md$'
```

If found at `<SKILL_ROOT>/SKILL.md`, derive absolute script paths:

- `<SKILL_ROOT>/scripts/eudic_export.py`
- `<SKILL_ROOT>/scripts/run_with_login_zsh.py`
- `<SKILL_ROOT>/scripts/ankiconnect_import.py`
- `<SKILL_ROOT>/scripts/check_env.sh`
- `<SKILL_ROOT>/scripts/cleanup_import_artifacts.sh`

## Authoring Rules In One File

In `~/.codex/rules/eudic-to-anki.rules`, include both:

1. Relative rules (for agent runs inside skill root).
2. Absolute rules (for automations invoking installed scripts by full path).

Use date-agnostic examples in `match`; do not lock examples to a fixed day.

## Validation Workflow (Mandatory)

Run `execpolicy check` against the same single file:

```bash
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 <SKILL_ROOT>/scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- python3 <SKILL_ROOT>/scripts/ankiconnect_import.py --ping
codex execpolicy check --pretty --rules "$HOME/.codex/rules/eudic-to-anki.rules" -- bash <SKILL_ROOT>/scripts/cleanup_import_artifacts.sh
```

All checks must return `decision: allow`.

## Anti-Leak Requirement

When writing docs or templates, never include personal paths like `/Users/<name>`.
Only use placeholders such as `<SKILL_ROOT>` and shell variables such as `$HOME`.

## Completion Contract

When finished, the agent should report:

1. Final file path: `~/.codex/rules/eudic-to-anki.rules`
2. Discovered `<SKILL_ROOT>` used for absolute-path rules
3. The exact `execpolicy check` commands executed
4. Which command families are confirmed `allow`
