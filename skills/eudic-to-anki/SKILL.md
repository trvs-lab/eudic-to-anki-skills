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
- Intermediate artifacts: `import_scratch/` only.

## Quick Start (agent flow)

1. Environment check:
  - `bash scripts/check_env.sh`
2. Export words:
  - `python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output import_scratch/_day_<D>_export.csv`
3. Build placeholder + author coach:
  - `python3 scripts/build_dia_json_from_csv.py --csv import_scratch/_day_<D>_export.csv --output import_scratch/_day_<D>_partial.json --batch-date <D> --eudic-words-only`
  - Agent writes refined coach JSON (8 fields) and merges (single file or batches + `scripts/merge_coach_with_partial.py`).
4. Validate:
  - `python3 scripts/validate_trvs_coach_json.py import_scratch/_day_<D>_import.json`
5. Import with audio (successful import triggers Anki sync by default; use `--no-sync` to skip):
  - `python3 scripts/ankiconnect_import.py --input import_scratch/_day_<D>_import.json --deck words --create-deck --dia-upsert --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}"'`
6. Cleanup after success:
  - `bash scripts/cleanup_import_artifacts.sh`

## Quality Gates

- Agent authors coach content; do not bulk-copy Eudic `exp`/`phon` into coach fields by default.
- For large lists, use batched subagents and validate each batch before merge.
- If subagent output is base64, decode via:
  - `python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o import_scratch/coach_batch_01.json`
- Block import on validator errors (`U+FFFD`, mojibake markers, wrong field types).
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