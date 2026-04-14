# eudic-to-anki

**English** | [中文](README.zh-CN.md)

An open Agent Skill that exports words from the Eudic dictionary and turns them into study cards, then imports them into Anki automatically:

- Export words via the Eudic OpenAPI
- Have an Agent build Anki flashcard content
- Generate pronunciation with Edge-TTS
- Import into Anki through AnkiConnect

This repository follows the [Agent Skills](https://agentskills.io/) format and works with the Vercel skills CLI.

## Install

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

## Quick Start

1. Install the skill with `npx skills add ...`.
2. Open `skills/eudic-to-anki/SKILL.md`.
3. In your agent, run the documented commands with the skill directory (`skills/eudic-to-anki/`) as the working directory.
4. Start with:
   - `bash scripts/check_env.sh`

## What You Get

- **Unified workflow**: export → build cards → validate → import → cleanup
- **Quality gate**: generated cards are checked automatically against the expected format
- **Post-import sync**: after a successful import into Anki, changes sync to the cloud by default
- **Templates included**: TRVS-Lab note type and related assets ship with the skill

## What You Need to Configure

- **Eudic `EUDIC_TOKEN`**: follow [skills/eudic-to-anki/references/openapi.md](skills/eudic-to-anki/references/openapi.md)
- **Anki Desktop + AnkiConnect**: follow [skills/eudic-to-anki/references/anki.md](skills/eudic-to-anki/references/anki.md)

## Repository Layout

```
skills/eudic-to-anki/
  SKILL.md            # agent instructions (entrypoint)
  README.md           # skill overview
  scripts/            # export, validate, merge, import, TTS
  references/         # token / Anki / Edge-TTS / coach prompt
  assets/             # TRVS-Lab note-type templates
  workflows/          # yesterday / date-range / word-list playbooks
```

Runtime artifacts are written outside the installed skill directory by default:

- `~/Documents/eudic-to-anki-temp/`

## Typical Commands

```bash
# environment check
bash scripts/check_env.sh

# Eudic categories
python3 scripts/eudic_export.py --list-categories

# Anki connectivity
python3 scripts/ankiconnect_import.py --ping
```

## License

MIT. See [LICENSE](LICENSE).
