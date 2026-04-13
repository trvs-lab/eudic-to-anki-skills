# eudic-to-anki (Agent Skill)

Export Eudic cloud study-list words, author **TRVS-Lab** coach JSON (by the agent), generate pronunciation audio (Edge-TTS), and import into Anki via AnkiConnect.

Format follows the open [Agent Skills](https://agentskills.io/) layout used by Vercel and others.

## Install (Vercel / skills CLI)

From [Vercel Agent Skills](https://vercel.com/docs/agent-resources/skills) and [skills.sh](https://skills.sh/docs/cli):

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki
```

If this repository ever contains only this one skill, you can omit `--skill`:

```bash
npx skills add trvs-lab/eudic-to-anki-skills
```

The CLI wires the skill into supported agents (Cursor, Claude Code, Copilot, etc.). After install, open the skill’s `**SKILL.md**` from the path the CLI reports, and run shell/Python commands with **current working directory = that skill folder** (the directory that contains `SKILL.md`).

## Layout

```
skills/eudic-to-anki/
  SKILL.md          # agent instructions (start here)
  README.md         # human-oriented overview
  scripts/          # export, validate, merge, import, TTS
  references/       # token, Anki, Edge-TTS, coach prompt
  assets/           # TRVS-Lab note type templates
  workflows/        # playbooks (yesterday / range / word list)
  import_scratch/     # intermediates (gitignored contents)
```

## Open source checklist

1. Push this repo to GitHub: `trvs-lab/eudic-to-anki-skills`.
2. Choose a license (this repo includes `LICENSE` as MIT; change if you prefer another).
3. Optionally list the skill on the community directory: [skills.sh](https://skills.sh/) (see their submission process).

## Requirements (runtime)

- Python 3, `EUDIC_TOKEN` (Eudic OpenAPI), Anki + AnkiConnect, optional `pip install edge-tts` for default audio.

See `skills/eudic-to-anki/SKILL.md` and `skills/eudic-to-anki/references/` for details.