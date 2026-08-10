---
name: eudic-to-anki
description: Export Eudic vocabulary encounters, author one-card Context Anchor notes, generate required Edge-TTS audio, and upsert them into managed Anki decks. Trigger for 把生词导入 Anki, Eudic words to Anki, or eudic-to-anki.
---

# Eudic to Anki

Execute the complete pipeline. Treat this directory as the working directory.

## Read the relevant modules

- Export: `modules/export/README.md`
- Coach authoring: `modules/coach/README.md`
- Audio: `modules/audio/README.md`
- Import: `modules/import/README.md`
- Exact JSON contract: `references/word-coach-json-prompt.md`

## Defaults

- Export yesterday in the local timezone unless a date range is given.
- Export all Eudic categories unless one is named.
- Use note type `TRVS-Lab` and deck root `words`.
- Use an absolute artifact directory such as `/Users/alice/Documents/eudic-to-anki-temp`.
- Import into `words::learn`、`words::defer`、`words::skip`. Keep `reject` internal and do not import it.

## Execute

1. Create the artifact directory in a separate command.
2. Run `bash scripts/check_env.sh`.
3. Export every encounter, retaining `category_id`、`category_name`、`add_time_utc`、`add_time_local` and `context_line`:
   `python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output <ABS_TEMP_DIR>/_day_<D>_export.csv`
4. Build placeholders without deduplicating repeated encounters:
   `python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_day_<D>_export.csv --output <ABS_TEMP_DIR>/_day_<D>_partial.json --eudic-words-only`
5. Author coach JSON using `references/word-coach-json-prompt.md`, then merge it with every exported row:
   `python3 scripts/merge_coach_with_partial.py --partial <ABS_TEMP_DIR>/_day_<D>_partial.json --coach <ABS_TEMP_DIR>/coach.json -o <ABS_TEMP_DIR>/_day_<D>_import.json`
6. Validate:
   `python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/_day_<D>_import.json`
7. Preview:
   `python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`
8. Import with required audio:
   `python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}" --voice "{voice}"'`
9. After success, run `bash scripts/cleanup_import_artifacts.sh`.

Run rule-covered commands directly. Do not wrap them in a login shell or join them with shell operators.

## Authoring contract

- Make exactly one Context Anchor card per normalized word or phrase. Never create a recall or cloze card.
- The front contains only `word` and `card_sentence`; tapping the word plays its audio.
- Choose `card_sentence` as follows:
  - `source`: use a clean, concise source sentence.
  - `adapted`: minimally trim or rewrite a long, noisy, or truncated source while preserving its sense, facts, and tone.
  - `generated`: when no source exists, write a practical 8–16 word sentence containing the word or a valid inflection.
- Preserve the untouched Eudic sentence in `source_context`. Generated sentences are never historical source context.
- Back content is immediately visible in this order: contextual Chinese meaning, IPA, English definition, optional source chunk and meaning, optional useful word-family/morphology hint, real historical contexts, encounter count, latest encounter time.
- Omit low-value `word_family` and `source_chunk` fields instead of writing placeholders.

## Classification

- `learn`: high-transfer vocabulary worth meeting on every import.
- `defer`: useful but lower priority. A later distinct encounter automatically promotes it to `learn`.
- `skip`: a complete word or phrase kept in Anki for manual deletion or movement. A later import does not override this deck.
- `reject`: an invalid fragment or garbage entry; never import it.

When a card is already in one of the three managed decks, its current Anki deck is authoritative. A distinct encounter updates the same note and resets its single card to new. An identical encounter ID changes nothing and does not reset progress.

## Audio hard gate

- Use Microsoft Edge online TTS through `edge-tts`; the default voice is `en-US-GuyNeural`.
- Probe the same provider and voice before import. For a transient failure, retry exactly once with identical arguments.
- If the second attempt fails or the MP3 is missing, empty, or invalid, stop the whole import and report the service, word, voice, attempts, and reason.
- Do not use macOS `say`, system/browser TTS, another provider, another voice, or any synthesized fallback.
- Generate and validate all local audio before changing any Anki note/card or syncing. Existing valid `[sound:...]` values and explicit valid local MP3 files may be reused.

## Model migration

The legacy two-template `Chunk Anchor` / `Chunk Recall` model cannot be converted safely in place. If detected, stop. Tell the user to back up Anki, remove the legacy `TRVS-Lab` notes/note type, and rerun the import. Search by normalized word across the note type so legacy deck placement cannot create duplicates.

## Safety

- Never write the Eudic token into tracked files.
- Prefer `EUDIC_TOKEN` from the environment.
- Stop with setup guidance if AnkiConnect is unavailable.
- Do not sync after validation, audio, model, or import failure.
