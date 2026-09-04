# eudic-to-anki

[中文](README.md) · **English**

**Bring the words you encounter into Anki, with their context.**

An open-source [Agent Skill](https://agentskills.io/) for English learners. It exports vocabulary and reading context from Eudic, lets an Agent prepare meanings, examples, and pronunciation, and creates one Context Anchor card per term.

[Quick start](#quick-start) · [Card design](#one-card-connected-to-its-context) · [Import behavior](#import-and-review-rules) · [Documentation](#documentation-and-guides)

## One card, connected to its context

<p align="center">
  <img src="docs/images/context-anchor-preview.png" width="820" alt="Anki card for innovator: a reading sentence, contextual Chinese meaning, IPA, English definition, source chunk, and morphology clues.">
</p>

- **Start with the context.** The front shows only the word and its sentence. Tap the word to hear it. Clean source sentences are preferred; long sources are shortened, and missing sources get practical generated examples.
- **Then understand the usage.** The back shows the contextual Chinese meaning, IPA, English definition, and useful chunks and morphology clues without collapsed sections.
- **Connect each new encounter.** Each normalized term has one note and one card. New reading encounters update that note and retain recent genuine source contexts.

## Quick start

### 1. Prepare the environment

- An Agent runtime that supports Agent Skills.
- Node.js and `npx` to install the skill; Python 3 and the `edge-tts` package to run scripts and generate audio.
- An Eudic account and `EUDIC_TOKEN`. See the [token setup guide](skills/eudic-to-anki/references/openapi.md).
- Anki Desktop with the AnkiConnect add-on `2055492159`. See the [Anki setup guide](skills/eudic-to-anki/references/anki.md).

### 2. Install the skill

<a id="install"></a>

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

Codex users must also ask the Agent to follow the [local rules guide](skills/eudic-to-anki/RULES_README.md) and generate `~/.codex/rules/eudic-to-anki.rules`.

### 3. Open Anki and start an import

Keep Anki Desktop open and send the Agent:

> Check the eudic-to-anki environment and import yesterday's Eudic words into Anki.

Other inputs include “the past week,” “August 1–7, 2026,” or a manually supplied word list. All Eudic study lists are queried unless one is specified.

> **Importing also removes the source words from Eudic.** Cleanup starts after every local note, encounter, card, and audio file verifies; it does not wait for cloud sync. Completed cleanup retains no backup or deletion history. Manual word lists do not trigger Eudic cleanup.

## Import and review rules

**From reading to review, in order.** Eudic export → Agent-authored content → content and template validation → Edge-TTS audio → Anki import and read-back verification → Eudic cleanup.

**Study groups set the priority.** Imported terms go into three decks under `words`. Classification labels stay off the cards.

| Group | Behavior |
| --- | --- |
| `learn` | High-transfer vocabulary for daily review |
| `defer` | Useful but lower priority; a distinct later encounter promotes it to `learn` |
| `skip` | Complete but low-value terms, kept in Anki for manual movement or deletion |
| `reject` | Invalid fragments or garbage; neither imported into Anki nor removed from Eudic |

**Reimporting differs from encountering a word again.** An identical encounter does not reset progress. A distinct encounter updates the existing note and resets its single card to new. Existing `learn` and `skip` placements are preserved.

**Failures leave work resumable.** If import or read-back verification fails, no source words in the batch are deleted. If local import succeeds but Eudic cleanup fails, the next run resumes cleanup first. Both outcomes are reported separately.

<details>
<summary>Export, audio, and legacy template limits</summary>

- **Date ranges:** a continuous range uses one protected export process, without splitting it into daily or parallel requests. See [export limits](skills/eudic-to-anki/references/openapi.md#日期范围与访问限制).
- **Audio:** Edge-TTS retries once with the same arguments. A second failure stops the import; there is no system TTS fallback.
- **Templates:** the TRVS-Lab model is strictly verified before import. Legacy two-card models stop the process and require a full backup before following the [migration guide](skills/eudic-to-anki/modules/import/README.md#迁移).

</details>

## Documentation and guides

The linked setup guides and reference documents are primarily in Chinese.

- **First use:** [installation walkthrough](https://trvs.dev/blog/20260419-eudic-to-anki-skill/) · [token setup](skills/eudic-to-anki/references/openapi.md) · [Anki setup](skills/eudic-to-anki/references/anki.md)
- **Cards and review:** [card design and study workflow](https://trvs.dev/blog/20260812-eudic-anki-skill-redesign/) · [groups, updates, and cleanup](skills/eudic-to-anki/modules/import/README.md)
- **Agent execution:** [complete workflow](skills/eudic-to-anki/SKILL.md) · [Codex local rules](skills/eudic-to-anki/RULES_README.md)
- **Implementation:** [skill directory](skills/eudic-to-anki/) · [card templates](skills/eudic-to-anki/assets/) · [tests](tests/eudic_to_anki/)

## License

[MIT](LICENSE)
