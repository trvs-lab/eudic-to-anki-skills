# eudic-to-anki

**English** | [中文](README.zh-CN.md)

An Agent Skill that exports vocabulary encounters from Eudic and imports one-card Context Anchor notes into Anki.

## Highlights

- Preserves Eudic category, timestamp, and raw reading context for every encounter.
- Keeps one Anki note and one card per normalized word or phrase.
- Uses a clean source sentence, minimally adapts a noisy one, or generates a practical sentence when no source exists.
- Shows only the word and sentence on the front; tapping the word plays pronunciation audio.
- Keeps the back unfolded and ordered by learning value, without classification markers.
- Manages `learn`, `defer`, and `skip` decks; invalid `reject` entries remain outside Anki.
- Resets the single card for a distinct new encounter and does nothing for an identical encounter ID.
- Uses Edge-TTS with one retry. A second failure aborts the import; system TTS is never used as a fallback.

## Install

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

Codex users must also generate local rules from `skills/eudic-to-anki/RULES_README.md`.

## Configure and run

- Eudic token: `skills/eudic-to-anki/references/openapi.md`
- Anki Desktop and AnkiConnect: `skills/eudic-to-anki/references/anki.md`
- Full agent workflow: `skills/eudic-to-anki/SKILL.md`

## License

MIT. See [LICENSE](LICENSE).
