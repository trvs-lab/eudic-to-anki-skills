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
  - The partial JSON preserves Eudic `context_line` as `source_context`; use it when authoring examples. Agent writes refined coach JSON per `references/word-coach-json-prompt.md`, then merge (single file or batches + `scripts/merge_coach_with_partial.py`).
5. Validate:
  - `python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/_day_<D>_import.json`
6. Dry-run import:
  - `python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`
7. Import with audio (successful import triggers Anki sync by default; use `--no-sync` to skip):
  - `python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}"'`
  - `--audio-command` is parsed as argv and executed without a shell; shell operators like pipes/redirection are unsupported.
8. Cleanup after success:
  - `bash scripts/cleanup_import_artifacts.sh`

## Quality Gates

- Agent authors coach content; do not bulk-copy Eudic `exp`/`phon` into coach fields by default.
- Coach JSON must preserve POS explicitly: include `part_of_speech` on every note, and keep POS markers at the start of each Chinese `meaning` line.
- Every final import note must have complete AmE IPA in `pronunciation`, a non-empty `example`, and at least two common `collocations`.
- Chinese `meaning` must be regenerated as short, natural, dictionary-style Chinese labels. Do not paste Eudic `exp`, and do not write explanatory definitions such as `n. 由一个碳原子和两个氧原子组成的气体`; write `n. 二氧化碳` and put explanations in `english_definition`.
- `english_definition` is required and must be a concise, friendly, explanatory learner definition in plain English, similar to vocabulary.com style; avoid bare synonyms, Chinese text, or long encyclopedia definitions.
- Audio is required in the final Anki note. The import command must generate or preserve a `[sound:...]` tag in `发音`; use `--require-audio --verify-required-fields` on the real import.
- Prefer clear learner translations over stiff terms: e.g. `sprites` can be `n. 游戏里的小图；角色图`, and `interconnect` can be `v. 连在一起；互相关联`.
- `root` must be generated for each word when useful, using `形式（中文义）+ ...`; use `-` only for genuinely unsplittable or unhelpful cases. A whole batch of `root: "-"` is invalid.
- Examples follow source-first rules: keep a complete, natural, not-too-long `source_context` sentence; shorten/rewrite noisy, truncated, or overly long source while preserving the original situation; invent a simple example only when no source sentence exists.
- Treat suspicious one-letter entries other than `a`/`I` as likely export fragments and stop for review instead of importing blindly.
- For large lists, use batched subagents and validate each batch before merge.
- If subagent output is base64, decode via:
  - `python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o <ABS_TEMP_DIR>/coach_batch_01.json`
- Block import on validator errors (`U+FFFD`, mojibake markers, wrong field types, missing IPA/example/collocations/english_definition, weak English definitions, long/explanatory meanings, missing POS markers, missing `part_of_speech`, all-placeholder roots, or suspicious single-letter words).
- Run `ankiconnect_import.py --dry-run --verify-required-fields` before the real import, then run the real import with `--require-audio --verify-required-fields` and spot-check several notes in Anki, especially `音标`、`释义`、`英英`、`词根`、`例句`、`常用搭配`、`发音`.
- `--dia-upsert` preserves existing Anki scheduling/progress by default. Only use `--reset-progress-on-update` when the user explicitly wants updated cards reset to new.
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
