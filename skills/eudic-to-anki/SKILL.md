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
- Base deck: `words` unless user specifies. `TRVS-Lab` routes generated cards into phrase chunk anchor and recall decks under the base deck.
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
  - `python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_day_<D>_export.csv --output <ABS_TEMP_DIR>/_day_<D>_partial.json --eudic-words-only`
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
- Coach JSON must classify every note with `learning_priority` for the user's core goal: fluent listening, speaking, reading, and writing, while supporting 20000-vocab / IELTS 8+. Use `focus` for words worth active speaking/writing or high-impact comprehension, `passive` for recognition-only words, and `ignore` for noise or words with little real fluency value. When unsure, choose `passive`.
- For polysemous words, classify by the highest-transfer common sense, not only the most concrete sense: common abstract, verbal, rhetorical, or high-value collocational senses that improve expression or comprehension should make the word `focus` (e.g. `foil`); stable concrete concept terms usually remain `passive` (e.g. `carbon dioxide`).
- Do not classify by part of speech. Nouns, verbs, adjectives, and adverbs can all be `focus` or `passive`; judge only by real fluency value and whether the word is worth active output.
- Protect core common vocabulary: high-frequency, polysemous, collocation-rich, easily misused, or phrase-forming everyday words should be `focus` even if they are not advanced, because they carry more fluency value than many rare hard words.
- `TRVS-Lab` is a fresh-start phrase chunk model. Before upgrading an existing Anki setup, the user should clear old `TRVS-Lab` notes or relevant decks; old notes without phrase chunk fields are not supported by the new templates.
- Every coach note must include `target_chunk`, `target_chunk_meaning`, and `target_chunk_sentence`. `target_chunk_sentence` is the clean learning sentence shown on anchor cards and must contain `target_chunk` exactly. `focus` notes must include `target_chunk_cloze` derived by blanking `target_chunk` from that same sentence; `passive` and `ignore` notes must leave `target_chunk_cloze` empty so they do not generate recall cards.
- Anki import routes generated cards by review action: Chunk Anchor cards go to `words::chunk-anchor::<focus|passive|ignore>`, while Chunk Recall cards for focus notes go to `words::chunk-recall::focus`.
- Anchor and recall cards are separate templates/decks for learning phrase chunks, not isolated words. Anchor fronts show `target_chunk` plus `target_chunk_sentence`; anchor backs reveal `target_chunk_meaning` first and show `example` only when it is a real source example. Recall card fronts show the cloze before the Chinese phrase meaning; recall backs show the left-aligned target chunk, optional source `example`, word-level Chinese meaning, and 1-2 collocations. There is no chunk-specific audio; both card types use the main word audio.
- Anki import stores priority in the `学习标记` field as symbols (`★`, `◇`, `×`) and stable tags (`priority::focus`, `priority::passive`, `priority::ignore`). The card template shows this only as a subtle back-side hint, never on the front.
- `ignore` anchor cards are still imported normally into `words::chunk-anchor::ignore`. Do not suspend, skip, or exclude them unless the user explicitly asks.
- The pipeline no longer adds static tags `english`, `vocab`, or `eudic`; only priority tags and user-supplied `--tag` values are kept.
- Every final import note must have complete AmE IPA in `pronunciation`, a non-empty `target_chunk_sentence`, and at least two common `collocations`. `example` is source-only and may be empty when no real source context exists.
- Chinese `meaning` must be regenerated as short, natural, dictionary-style Chinese labels. Do not paste Eudic `exp`, and do not write explanatory definitions such as `n. 由一个碳原子和两个氧原子组成的气体`; write `n. 二氧化碳` and put explanations in `english_definition`.
- `english_definition` is required and must be a concise, friendly, explanatory learner definition in plain English, similar to vocabulary.com style; avoid bare synonyms, Chinese text, or long encyclopedia definitions.
- Audio is required in the final Anki note. The import command must generate or preserve a `[sound:...]` tag in `发音`; use `--require-audio --verify-required-fields` on the real import.
- Prefer clear learner translations over stiff terms: e.g. `sprites` can be `n. 游戏里的小图；角色图`, and `interconnect` can be `v. 连在一起；互相关联`.
- `root` must be generated for each word when useful, using `形式（中文义）+ ...`; use `-` (or `无`) for genuinely unsplittable or unhelpful cases. Never use the whole word itself as the only root segment, e.g. `crimson（深红）`; that should be `-`. A whole batch of placeholder roots is invalid.
- `example` follows source-only rules: keep or lightly clean a complete, natural, not-too-long `source_context` sentence; lightly complete noisy, truncated, or overly long source only while preserving the original situation; leave `example` empty when no source sentence exists. Invented learning sentences belong in `target_chunk_sentence`, not `example`.
- Treat suspicious one-letter entries other than `a`/`I` as likely export fragments and stop for review instead of importing blindly.
- For large lists, use batched subagents and validate each batch before merge.
- If subagent output is base64, decode via:
  - `python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o <ABS_TEMP_DIR>/coach_batch_01.json`
- Block import on validator errors (`U+FFFD`, mojibake markers, wrong field types, missing IPA/collocations/english_definition, weak English definitions, long/explanatory meanings, missing POS markers, missing `part_of_speech`, invalid `learning_priority`, missing or inconsistent phrase chunk fields, whole-word pseudo-roots, all-placeholder roots, or suspicious single-letter words).
- Run `ankiconnect_import.py --dry-run --verify-required-fields` before the real import, then run the real import with `--require-audio --verify-required-fields` and spot-check several notes in Anki, especially `音标`、`释义`、`英英`、`词根`、`短语块例句`、`常用搭配`、`发音`、`学习标记`; `例句` is optional source context.
- `--dia-upsert` searches the base deck and generated phrase chunk decks, then updates matching notes without duplicate notes. It resets existing Anki cards to new by default when updating. Only add `--preserve-progress-on-update` when the user explicitly says not to reset learning progress.
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
