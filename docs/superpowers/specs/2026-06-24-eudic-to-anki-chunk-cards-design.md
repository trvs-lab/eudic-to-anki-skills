# Eudic-to-Anki Phrase Chunk Card Design

Date: 2026-06-24

## Context

The current `eudic-to-anki` skill builds `TRVS-Lab` Anki notes around a headword, with examples and collocations shown as supporting material. Recent learning sessions showed that isolated word study is less useful than learning the phrase chunk that carries the word in real usage, such as `inflict damage on`, `go berserk`, or `a look of revulsion`.

This design upgrades the skill so the main memory anchor is a phrase chunk, not an isolated word.

## Goals

- Make every imported note carry one explicit phrase chunk anchor.
- Keep first contact easy: the learner sees the full phrase chunk before being asked to recall it.
- Separate recognition practice from recall practice by deck.
- Keep audio simple: use the existing main word audio, not separate chunk audio.
- Treat this as a fresh-start breaking upgrade; old `TRVS-Lab` notes do not need compatibility.

## Non-Goals

- Do not migrate old notes or old cards.
- Do not preserve old `TRVS-Lab` template fallback behavior.
- Do not add chunk audio in this version.
- Do not build a full learning-stage system beyond anchor and recall cards.

## Fresh-Start Upgrade

This is a breaking model/template upgrade.

Before using the new version, the user is expected to clear old `TRVS-Lab` notes or relevant decks. The new templates assume the new phrase chunk fields exist. The skill should document this clearly and fail loudly if the Anki model shape is incompatible.

## Data Model

Existing coach JSON fields remain:

- `word`
- `pronunciation`
- `part_of_speech`
- `meaning`
- `english_definition`
- `root`
- `example`
- `collocations`
- `audio_html`
- `learning_priority`

Add three phrase chunk fields:

- `target_chunk`: required for every note. The primary phrase chunk anchor, for example `inflict damage on`.
- `target_chunk_meaning`: required for every note. A short phrase-level Chinese anchor, for example `造成严重伤害`.
- `target_chunk_cloze`: required for `focus` notes and empty or absent for `passive` and `ignore` notes. A natural cloze sentence, for example `The storm ____ serious damage on the town.`

Suggested Anki field names:

- `目标短语块`
- `短语块锚点`
- `短语块挖空`

`target_chunk` should prefer natural collocations or phrase chunks. It may use a minimal context frame for concrete or low-output words. It may fall back to the headword only when no natural chunk exists, but this should be allowed as a last resort, not encouraged.

## Card Templates

The upgraded `TRVS-Lab` note type has two card templates.

### Chunk Anchor

Generated for every note.

Front:

- `target_chunk`
- `example`
- main word audio from the existing `发音` field

Back:

- `{{FrontSide}}`
- `pronunciation`
- word-level `meaning`
- `english_definition`
- `root`
- `collocations`
- subtle learning marker if desired

Purpose: low-pressure phrase chunk recognition and anchoring.

### Chunk Recall

Generated only for `focus` notes.

Front:

- `target_chunk_cloze`
- `target_chunk_meaning`

Back:

- `{{FrontSide}}`
- `target_chunk`
- `pronunciation`
- main word audio from the existing `发音` field
- word-level `meaning`
- 1-2 extension collocations

The back should not repeat `target_chunk_meaning`, because Anki back sides include the front side above the answer.

Purpose: light recall using a cloze sentence and Chinese phrase anchor.

## Deck Routing

Decks are organized by review action first, then priority:

- `words::chunk-anchor::focus`
- `words::chunk-anchor::passive`
- `words::chunk-anchor::ignore`
- `words::chunk-recall::focus`

The import script should create or update the note first, query the generated cards, identify cards by template name, and move each card to its target deck.

`passive` and `ignore` notes should not generate recall cards because `target_chunk_cloze` is empty or absent.

## Generation Flow

1. `build_dia_json_from_csv.py` continues to emit partial notes with `word`, source metadata, and `source_context`.
2. The agent authors full coach JSON using the updated prompt.
3. The updated prompt requires `target_chunk`, `target_chunk_meaning`, and, for focus notes, `target_chunk_cloze`.
4. `validate_trvs_coach_json.py` blocks invalid or incomplete phrase chunk fields.
5. `ankiconnect_import.py` maps JSON fields to Anki fields, creates or updates notes, and routes generated cards to the chunk decks.

## Validation Rules

Block import when:

- `target_chunk` is missing or empty.
- `target_chunk_meaning` is missing or empty.
- `learning_priority = focus` and `target_chunk_cloze` is missing or empty.
- `learning_priority` is `passive` or `ignore` and `target_chunk_cloze` is non-empty.
- `target_chunk_cloze` is not a natural sentence.
- `target_chunk_cloze` has no blank marker.
- `target_chunk_meaning` looks like a long word-level dictionary definition rather than a short phrase-level anchor.

Existing validation rules for IPA, examples, collocations, English definitions, POS, roots, and learning priority remain in force.

## Error Handling

- If the local Anki `TRVS-Lab` model does not match the fresh-start model spec, show a breaking-upgrade message and tell the user to clear old notes or recreate/sync the model.
- If a focus note does not generate a `Chunk Recall` card, fail the import verification.
- If a passive or ignore note generates a recall card, fail the import verification.
- If card routing cannot identify a card template, fail with the note id, word, and card id.

## Testing

Add or update tests for:

- Validator checks for `target_chunk`, `target_chunk_meaning`, and `target_chunk_cloze`.
- Focus/passive/ignore behavior around recall card generation.
- JSON-to-Anki field mapping for the new phrase chunk fields.
- Model spec includes the new fields and two card templates.
- Card routing maps `Chunk Anchor` and `Chunk Recall` to the correct decks.
- Template smoke tests for anchor and recall card HTML.

## Documentation Updates

Update:

- `SKILL.md`
- `modules/coach/README.md`
- `modules/import/README.md`
- `references/word-coach-json-prompt.md`
- `references/anki.md`
- workflow docs that mention dry-run/import checks

The documentation must state that this version is a fresh-start breaking upgrade.
