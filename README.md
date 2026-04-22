# eudic-to-anki

**English** | [中文](README.zh-CN.md)

An open Agent Skill that exports words from the Eudic dictionary and turns them into study cards, then imports them into Anki automatically:

- Export words via the Eudic OpenAPI
- Have an Agent build Anki flashcard content
- Generate pronunciation with Edge-TTS
- Import into Anki through AnkiConnect

This repository follows the [Agent Skills](https://agentskills.io/) format and works with the Vercel skills CLI.

## Official Guide

For a complete installation and usage walkthrough, read:
[https://trvs.dev/blog/20260420-eudic-to-anki-skill/](https://trvs.dev/blog/20260420-eudic-to-anki-skill/)

## Install

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

## GitHub Pages

This repository now includes a dedicated landing page under `docs/` with an Apple-inspired visual style:

- page entry: `docs/index.html`
- auto deploy workflow: `.github/workflows/deploy-pages.yml`

To publish it:

1. Push changes to `main`
2. In GitHub repository settings, open **Pages**
3. Set source to **GitHub Actions** (if not already set)
4. Wait for the **Deploy GitHub Pages** workflow to finish

## Codex Post-Install Step

If the user is installing this skill specifically for the Codex client, add one more required post-install step:

1. Open `skills/eudic-to-anki/RULES_README.md`.
2. Generate `~/.codex/rules/eudic-to-anki.rules` from the embedded `RULE_TEMPLATE`.
3. Replace every `<HOME>` placeholder with the real absolute home path before writing the file.
4. Treat rules generation as part of the Codex setup, not an optional hint.

This is Codex-specific. Other agent runtimes do not need a Codex rules file unless they intentionally emulate Codex's execpolicy model.

## Quick Start

1. Install the skill with `npx skills add ...`.
2. If you are using Codex, open `skills/eudic-to-anki/RULES_README.md` and create `~/.codex/rules/eudic-to-anki.rules`.
3. Open `skills/eudic-to-anki/SKILL.md`.
4. In your agent, run the documented commands with the skill directory (`skills/eudic-to-anki/`) as the working directory.
5. Start with:
   - `bash scripts/check_env.sh`

## What You Get

- **Unified workflow**: export → build cards → validate → import → cleanup
- **Quality gate**: generated cards are checked for complete IPA, concise regenerated Chinese meanings, friendly English definitions, source-first examples, root/affix breakdowns, audio, and common collocations
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

- the dedicated Documents artifact dir, using its canonical absolute form such as `<ABS_TEMP_DIR>` / `/Users/alice/Documents/eudic-to-anki-temp/`

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
