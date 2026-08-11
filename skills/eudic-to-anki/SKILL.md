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

## Route before executing

Select exactly one workflow before running any export command:

- A single day or「昨天」: read and follow `workflows/yesterday.md`.
- A 连续日期范围, including「过去一周」or「最近 N 天」: read and follow `workflows/date-range.md`.
- A user-supplied word list: read and follow `workflows/word-list.md`.

Resolve a relative range in the system local timezone as one inclusive start/end pair. One continuous-range request must produce exactly one export process. Never expand it into daily commands, parallel tool calls, or sub-agent exports.

## Execute the selected workflow

1. Create the artifact directory in a separate command.
2. Run `bash scripts/check_env.sh`.
3. Run the selected workflow's export and placeholder commands exactly. Preserve every encounter and its `category_id`、`category_name`、`add_time_utc`、`add_time_local` and `context_line`.
4. Author coach JSON using `references/word-coach-json-prompt.md`, merge it with every placeholder row, then validate the resulting `<IMPORT_JSON>`.
5. Preview `<IMPORT_JSON>` with `python3 scripts/ankiconnect_import.py --input <IMPORT_JSON> --deck words --create-deck --dry-run`. Confirm the model preflight is `create`, `update`, or `none`; stop on `blocked`.
6. Import with required audio:
   `python3 scripts/ankiconnect_import.py --input <IMPORT_JSON> --deck words --create-deck --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}" --voice "{voice}"'`
7. After success, run `bash scripts/cleanup_import_artifacts.sh`.

If export reports a concurrent export, rate limit, network failure, or parse failure, stop the entire pipeline. Do not generate placeholders, coach content, audio, or Anki changes, and do not retry by splitting the range.

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
- Author a non-empty `word_family` as exactly two plain-text lines: `拆解：...` then `联想：...`. Give every complete word its relevant POS and concise Chinese meaning; give roots and affixes a Chinese construction meaning without a POS; include 1–3 translated associations. The card shows these inline labels without a separate section title.
- Omit low-value `word_family` and `source_chunk` fields instead of writing placeholders.

## Classification

- `learn`: high-transfer vocabulary worth meeting on every import.
- `defer`: useful but lower priority. A later distinct encounter automatically promotes it to `learn`.
- `skip`: a complete word or phrase kept in Anki for manual deletion or movement. A later import does not override this deck.
- `reject`: an invalid fragment or garbage entry; never import it.

When a card is already in one of the three managed decks, its current Anki deck is authoritative. A distinct encounter updates the same note and resets its single card to new. An identical encounter ID changes nothing and does not reset progress; if its stored audio is missing or invalid, repair only the audio and still do not reset the card.

## Audio hard gate

- Use Microsoft Edge online TTS through `edge-tts`; the default voice is `en-US-GuyNeural`.
- When any note still needs generated audio, probe the same provider and voice before generation. If every required sound is already valid in Anki, reuse it without calling Edge-TTS. For a transient failure, retry exactly once with identical arguments.
- If the second attempt fails or the MP3 is missing, empty, or invalid, stop the whole import and report the service, word, voice, attempts, and reason.
- Do not use macOS `say`, system/browser TTS, another provider, another voice, or any synthesized fallback.
- Generate and validate all local audio before changing any Anki note/card or syncing. Verify existing `[sound:...]` media through AnkiConnect before reuse; explicit valid local MP3 files may also be reused. Every new or changed note must have valid audio—this is unconditional, not a CLI option.

## Model migration

Treat the bundled complete model spec as the source of truth. Before Edge-TTS or any deck, media, note, card, or sync write, acquire the shared nonblocking Anki lock and compare Front, Back, and CSS by SHA-256. Normalize only CRLF/LF and terminal newlines; every other HTML, JavaScript, CSS, or whitespace difference requires an update. Create a missing model automatically. Add missing required fields and overwrite changed template or styling content, then reread and verify the complete model before continuing. Preserve unknown extra fields and report them.

The legacy two-template `Chunk Anchor` / `Chunk Recall` model, a wrong template name, or known legacy fields cannot be converted safely in place. If detected, stop. Tell the user to back up Anki, remove the legacy `TRVS-Lab` notes/note type, and rerun the import. Search by normalized word across the note type so legacy deck placement cannot create duplicates. Never bypass the model gate with `--no-ensure-model`.

Use `python3 scripts/sync_trvs_lab_model.py --check` for a read-only model plan. Run the command without `--check` for a complete local create/update and strict verification. It does not trigger cloud sync unless `--sync` is explicit. Partial template-only or CSS-only synchronization is unsupported.

## Safety

- Never write the Eudic token into tracked files.
- Prefer `EUDIC_TOKEN` from the environment.
- Stop with setup guidance if AnkiConnect is unavailable.
- Do not sync after validation, audio, model, or import failure.
