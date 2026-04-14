# eudic-to-anki

An open Agent Skill for turning Eudic cloud words into Anki cards end-to-end:
- export words from Eudic OpenAPI
- generate TRVS-Lab coach fields by agent
- attach pronunciation audio (Edge-TTS)
- import into Anki via AnkiConnect

This repository follows the [Agent Skills](https://agentskills.io/) format and works with the Vercel skills CLI.

## Install

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

## Quick Start

1. Install the skill via `npx skills add ...`.
2. Open `skills/eudic-to-anki/SKILL.md`.
3. In your agent, run commands from the skill folder (`skills/eudic-to-anki/`).
4. Start with:
   - `bash scripts/check_env.sh`

## What You Get

- **Unified workflow**: export -> coach -> validate -> import -> cleanup
- **Quality gate**: `validate_trvs_coach_json.py` blocks malformed/garbled JSON
- **Post-import sync**: `ankiconnect_import.py` runs AnkiConnect `sync` after a successful import by default (`--no-sync` to skip)
- **Large batch support**: split/merge and optional subagent base64 decode helper
- **Model assets bundled**: TRVS-Lab model/templates included

## Requirements

- Python 3
- `EUDIC_TOKEN` (Eudic OpenAPI token)
- Anki Desktop + AnkiConnect add-on
- Optional audio dependency: `pip install edge-tts`

See:
- `skills/eudic-to-anki/references/openapi.md`
- `skills/eudic-to-anki/references/anki.md`
- `skills/eudic-to-anki/references/edge-tts.md`

## Repository Layout

```
skills/eudic-to-anki/
  SKILL.md            # agent instructions (entrypoint)
  README.md           # skill overview
  scripts/            # export, validate, merge, import, TTS
  references/         # token / Anki / Edge-TTS / coach prompt
  assets/             # TRVS-Lab note-type templates
  workflows/          # yesterday / date-range / word-list playbooks
  import_scratch/     # intermediate artifacts (gitignored contents)
```

## Typical Commands

```bash
# env check
bash scripts/check_env.sh

# eudic categories
python3 scripts/eudic_export.py --list-categories

# anki connectivity
python3 scripts/ankiconnect_import.py --ping
```

## License

MIT. See [LICENSE](LICENSE).
