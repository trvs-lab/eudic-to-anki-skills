---
name: eudic-to-anki
description: Unified Eudic to Anki pipeline skill. Agent-only entry for export, coach authoring, audio, and Anki import. Trigger e.g. 把昨天的生词导入 anki / eudic words to Anki / eudic-to-anki.
---

# Eudic Anki Pipeline (Unified Skill)

## Audience

This file is for the executing agent. The user gives natural-language goals; the agent executes end-to-end.

## Distribution

This skill lives under `skills/eudic-to-anki/` in the source repository so it can be installed with the Vercel skills CLI (`npx skills add <owner>/<repo> --skill eudic-to-anki`). After install, treat **this directory** (where `SKILL.md` lives) as the cwd for every command below. See the repository root `README.md` for the exact install line once the repo is public on GitHub.

## Scope

Single skill, modular internals:

- Export module: `modules/export/README.md`
- Coach module: `modules/coach/README.md`
- Import module: `modules/import/README.md`
- Audio module: `modules/audio/README.md`
- Workflow playbooks: `workflows/*.md`

All commands below assume cwd is this skill root: `eudic-to-anki/`.

## Defaults

- Date: yesterday (local timezone) unless user specifies range.
- Source: all Eudic categories unless user specifies category.
- Deck: `words` unless user specifies.
- Note type: `TRVS-Lab`.
- Intermediate artifacts: the user's dedicated Documents artifact dir only. Use the canonical absolute form `<ABS_TEMP_DIR>` such as `/Users/alice/Documents/eudic-to-anki-temp`.
- Optional override for local testing/custom setups: `EUDIC_TO_ANKI_TEMP_DIR=/path/to/temp`.
- For rule-sensitive runs, expand artifact paths to an absolute directory such as `/Users/alice/Documents/eudic-to-anki-temp`; do not execute them with `~` or `$HOME`.

## Execution Discipline

`<ABS_TEMP_DIR>` below means the user's expanded artifact directory, for example `/Users/alice/Documents/eudic-to-anki-temp`.

- Run rule-covered commands as direct argv commands only.
- Do not wrap them in `/bin/zsh -lc ...`, `zsh -lc ...`, `bash -lc ...`, `env ...`, or `FOO=bar ...`.
- Do not chain prep with `&&`, `||`, `;`, pipes, or subshells around a rule-covered command. Run prep and the main command as separate tool calls.
- When cwd is this skill root, use relative script paths like `python3 scripts/eudic_export.py ...`.
- When cwd is elsewhere, use absolute installed-skill paths like `python3 /Users/alice/.agents/skills/eudic-to-anki/scripts/eudic_export.py ...`.
- If login zsh is required for token loading, call `python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py ...` directly; do not add another shell wrapper around it.
- If `<ABS_TEMP_DIR>` does not exist, create it first with a separate direct command: `mkdir -p /Users/alice/Documents/eudic-to-anki-temp`.

## Quick Start (agent flow)

1. Ensure temp dir exists:
  - `mkdir -p <ABS_TEMP_DIR>`
2. Environment check:
  - `bash scripts/check_env.sh`
3. Export words:
  - `python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output <ABS_TEMP_DIR>/_day_<D>_export.csv`
4. Build placeholder + author coach:
  - `python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_day_<D>_export.csv --output <ABS_TEMP_DIR>/_day_<D>_partial.json --batch-date <D> --eudic-words-only`
  - Agent writes refined coach JSON. Each note must include `part_of_speech`, and every `meaning` line must start with a POS marker such as `n.`, `vt.`, `vi.`, `adj.`, or `adv.`. Then merge (single file or batches + `scripts/merge_coach_with_partial.py`).
5. Validate:
  - `python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/_day_<D>_import.json`
6. Import with audio (successful import triggers Anki sync by default; use `--no-sync` to skip):
  - `python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}"'`
  - `--audio-command` is parsed as argv and executed without a shell; shell operators like pipes/redirection are unsupported.
7. Cleanup after success:
  - `bash scripts/cleanup_import_artifacts.sh`

## Quality Gates

- Agent authors coach content; do not bulk-copy Eudic `exp`/`phon` into coach fields by default.
- Coach JSON must preserve POS explicitly: include `part_of_speech` on every note, and keep POS markers at the start of each Chinese `meaning` line.
- For large lists, use batched subagents and validate each batch before merge.
- If subagent output is base64, decode via:
  - `python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o <ABS_TEMP_DIR>/coach_batch_01.json`
- Block import on validator errors (`U+FFFD`, mojibake markers, wrong field types, missing POS markers in `meaning`, or missing `part_of_speech`).
- After a successful import, `ankiconnect_import.py` runs Anki sync by default; pass `--no-sync` to skip.
- If validation fails (especially `root` format), regenerate only the failed batch/words and re-run validator before merge/import.

## Playbooks

- Yesterday flow: `workflows/yesterday.md`
- Date range flow: `workflows/date-range.md`
- User word list flow: `workflows/word-list.md`

## Safety

- Never store token values in tracked files.
- Prefer `EUDIC_TOKEN` from environment.
- If AnkiConnect is unavailable, stop and provide setup guidance.
