# Phrase Chunk Anki Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `eudic-to-anki` so every `TRVS-Lab` note is anchored on a phrase chunk and produces separate anchor and recall review cards routed to separate decks.

**Architecture:** This is a fresh-start upgrade of the existing `TRVS-Lab` model. The coach JSON gains phrase chunk fields, the validator enforces them, the bundled model gains two card templates, and the import script maps card templates to action-based decks after note creation or update.

**Tech Stack:** Python 3 standard library, AnkiConnect HTTP API, Anki HTML/CSS templates, JSON model specs, `unittest`.

---

## Scope Check

The spec is one implementation unit: a breaking upgrade to the existing `TRVS-Lab` note model and import pipeline. It touches data generation rules, validation, templates, import routing, and docs because these must ship together for a working fresh-start model. It does not include historical card migration or chunk audio.

## File Structure

- `skills/eudic-to-anki/scripts/coach_fields.py`
  Shared phrase chunk key aliases and priority helpers.
- `skills/eudic-to-anki/scripts/merge_coach_with_partial.py`
  Preserve agent-authored phrase chunk fields when merging coach batches with Eudic metadata.
- `skills/eudic-to-anki/scripts/merge_minimal_week_import.py`
  Preserve phrase chunk fields in the minimal week helper.
- `skills/eudic-to-anki/scripts/validate_trvs_coach_json.py`
  Enforce phrase chunk fields before import.
- `skills/eudic-to-anki/scripts/ankiconnect_import.py`
  Map phrase chunk JSON keys to Anki fields, sync the fresh-start model, ensure chunk decks, add/update notes, route generated cards by template, and verify card routing.
- `skills/eudic-to-anki/assets/trvs_lab_model.json`
  Add phrase chunk fields and two card templates.
- `skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_front.html`
  Front template for phrase chunk recognition.
- `skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_back.html`
  Back template for phrase chunk recognition.
- `skills/eudic-to-anki/assets/trvs_lab_chunk_recall_front.html`
  Front template for focus-only cloze recall.
- `skills/eudic-to-anki/assets/trvs_lab_chunk_recall_back.html`
  Back template for focus-only cloze recall.
- `skills/eudic-to-anki/assets/trvs_lab_styling.css`
  Add small phrase chunk layout classes while preserving existing visual language.
- `tests/eudic_to_anki/`
  New `unittest` coverage for merge behavior, validator rules, model spec, field mapping, and card routing.
- Documentation files under `skills/eudic-to-anki/`
  Update prompt, workflows, module docs, and Anki docs to describe fresh-start phrase chunk cards.

## Test Command

Use this command throughout:

```bash
python3 -m unittest discover tests
```

Expected after each completed task: `OK`.

### Task 1: Preserve Phrase Chunk Fields Through Merge Helpers

**Files:**
- Modify: `skills/eudic-to-anki/scripts/coach_fields.py`
- Modify: `skills/eudic-to-anki/scripts/merge_coach_with_partial.py`
- Modify: `skills/eudic-to-anki/scripts/merge_minimal_week_import.py`
- Create: `tests/eudic_to_anki/test_merge_phrase_chunks.py`

- [ ] **Step 1: Write failing merge tests**

Create `tests/eudic_to_anki/test_merge_phrase_chunks.py`:

```python
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "eudic-to-anki"


class MergePhraseChunkTests(unittest.TestCase):
    def test_merge_coach_with_partial_preserves_phrase_chunk_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            partial = tmp_path / "partial.json"
            coach = tmp_path / "coach.json"
            output = tmp_path / "import.json"
            partial.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "word": "inflict",
                                "source": "eudic cloud",
                                "source_context": "The storm inflicted serious damage on the town.",
                                "tags": ["sample"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            coach.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "word": "inflict",
                                "pronunciation": "/ɪnˈflɪkt/",
                                "part_of_speech": "vt.",
                                "meaning": ["vt. 造成；使承受"],
                                "english_definition": "to make someone suffer harm or damage",
                                "root": "in-（进入）+ flict（打击）",
                                "example": "The storm inflicted serious damage on the town.",
                                "collocations": ["inflict pain on", "inflict punishment on"],
                                "audio_html": "",
                                "learning_priority": "focus",
                                "target_chunk": "inflict damage on",
                                "target_chunk_meaning": "造成严重伤害",
                                "target_chunk_cloze": "The storm ____ serious damage on the town.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "merge_coach_with_partial.py"),
                    "--partial",
                    str(partial),
                    "--coach",
                    str(coach),
                    "-o",
                    str(output),
                ],
                cwd=SKILL,
                check=True,
            )

            note = json.loads(output.read_text(encoding="utf-8"))["notes"][0]
            self.assertEqual(note["target_chunk"], "inflict damage on")
            self.assertEqual(note["target_chunk_meaning"], "造成严重伤害")
            self.assertEqual(
                note["target_chunk_cloze"],
                "The storm ____ serious damage on the town.",
            )

    def test_merge_minimal_week_import_preserves_phrase_chunk_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "export.csv"
            coach = tmp_path / "minimal.json"
            output = tmp_path / "week.json"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["word", "phon", "context_line"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "word": "distort",
                        "phon": "/dɪˈstɔrt/",
                        "context_line": "Fear can distort your judgment.",
                    }
                )
            coach.write_text(
                json.dumps(
                    {
                        "distort": {
                            "part_of_speech": "vt.",
                            "meaning": ["vt. 扭曲；曲解"],
                            "english_definition": "to change something so it is no longer accurate",
                            "root": "dis-（分开）+ tort（扭）",
                            "example": "Fear can distort your judgment.",
                            "collocations": ["distort the truth", "distort your judgment"],
                            "learning_priority": "focus",
                            "target_chunk": "distort your judgment",
                            "target_chunk_meaning": "扭曲判断",
                            "target_chunk_cloze": "Fear can ____ your judgment.",
                        }
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "merge_minimal_week_import.py"),
                    "--csv",
                    str(csv_path),
                    "--coach-json",
                    str(coach),
                    "--output",
                    str(output),
                ],
                cwd=SKILL,
                check=True,
            )

            note = json.loads(output.read_text(encoding="utf-8"))["notes"][0]
            self.assertEqual(note["target_chunk"], "distort your judgment")
            self.assertEqual(note["target_chunk_meaning"], "扭曲判断")
            self.assertEqual(note["target_chunk_cloze"], "Fear can ____ your judgment.")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the merge tests and verify they fail**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_merge_phrase_chunks -v
```

Expected: failures showing missing `target_chunk`, `target_chunk_meaning`, or `target_chunk_cloze`.

- [ ] **Step 3: Add shared phrase chunk key helpers**

Modify `skills/eudic-to-anki/scripts/coach_fields.py`:

```python
TARGET_CHUNK_KEYS = ("target_chunk", "目标短语块")
TARGET_CHUNK_MEANING_KEYS = ("target_chunk_meaning", "短语块锚点")
TARGET_CHUNK_CLOZE_KEYS = ("target_chunk_cloze", "短语块挖空")


def first_text_field(note: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = note.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""
```

- [ ] **Step 4: Preserve phrase chunk fields in `merge_coach_with_partial.py`**

Update imports:

```python
from coach_fields import (
    TARGET_CHUNK_CLOZE_KEYS,
    TARGET_CHUNK_KEYS,
    TARGET_CHUNK_MEANING_KEYS,
    first_text_field,
    fuse_pos_into_meaning,
    normalize_learning_priority,
)
```

Add these keys inside the output note dictionary:

```python
"target_chunk": first_text_field(c, TARGET_CHUNK_KEYS),
"target_chunk_meaning": first_text_field(c, TARGET_CHUNK_MEANING_KEYS),
"target_chunk_cloze": first_text_field(c, TARGET_CHUNK_CLOZE_KEYS),
```

- [ ] **Step 5: Preserve phrase chunk fields in `merge_minimal_week_import.py`**

Update imports:

```python
from coach_fields import (
    TARGET_CHUNK_CLOZE_KEYS,
    TARGET_CHUNK_KEYS,
    TARGET_CHUNK_MEANING_KEYS,
    first_text_field,
    fuse_pos_into_meaning,
    normalize_learning_priority,
)
```

Add these keys inside the output note dictionary:

```python
"target_chunk": first_text_field(c, TARGET_CHUNK_KEYS),
"target_chunk_meaning": first_text_field(c, TARGET_CHUNK_MEANING_KEYS),
"target_chunk_cloze": first_text_field(c, TARGET_CHUNK_CLOZE_KEYS),
```

- [ ] **Step 6: Run merge tests and full tests**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_merge_phrase_chunks -v
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 7: Commit merge field preservation**

```bash
git add skills/eudic-to-anki/scripts/coach_fields.py \
  skills/eudic-to-anki/scripts/merge_coach_with_partial.py \
  skills/eudic-to-anki/scripts/merge_minimal_week_import.py \
  tests/eudic_to_anki/test_merge_phrase_chunks.py
git commit -m "feat: preserve phrase chunk coach fields"
```

### Task 2: Validate Phrase Chunk Fields

**Files:**
- Modify: `skills/eudic-to-anki/scripts/validate_trvs_coach_json.py`
- Create: `tests/eudic_to_anki/test_validate_phrase_chunks.py`

- [ ] **Step 1: Write failing validator tests**

Create `tests/eudic_to_anki/test_validate_phrase_chunks.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "eudic-to-anki"
VALIDATOR = SKILL / "scripts" / "validate_trvs_coach_json.py"


def valid_note(**overrides: object) -> dict[str, object]:
    note: dict[str, object] = {
        "word": "inflict",
        "pronunciation": "/ɪnˈflɪkt/",
        "part_of_speech": "vt.",
        "meaning": ["vt. 造成；使承受"],
        "english_definition": "to make someone suffer harm, pain, or damage",
        "root": "in-（进入）+ flict（打击）",
        "example": "The storm inflicted serious damage on the town.",
        "collocations": ["inflict pain on", "inflict punishment on"],
        "audio_html": "",
        "learning_priority": "focus",
        "target_chunk": "inflict damage on",
        "target_chunk_meaning": "造成严重伤害",
        "target_chunk_cloze": "The storm ____ serious damage on the town.",
    }
    note.update(overrides)
    return note


class ValidatePhraseChunkTests(unittest.TestCase):
    def run_validator(self, note: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.json"
            path.write_text(json.dumps({"notes": [note]}, ensure_ascii=False), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                cwd=SKILL,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_valid_focus_phrase_chunk_note(self) -> None:
        result = self.run_validator(valid_note())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_requires_target_chunk(self) -> None:
        result = self.run_validator(valid_note(target_chunk=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk must not be empty", result.stderr)

    def test_requires_target_chunk_meaning(self) -> None:
        result = self.run_validator(valid_note(target_chunk_meaning=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk_meaning must not be empty", result.stderr)

    def test_requires_focus_cloze(self) -> None:
        result = self.run_validator(valid_note(target_chunk_cloze=""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("focus notes need target_chunk_cloze", result.stderr)

    def test_rejects_passive_cloze(self) -> None:
        result = self.run_validator(
            valid_note(learning_priority="passive", target_chunk_cloze="Fear can ____ judgment.")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("passive notes must leave target_chunk_cloze empty", result.stderr)

    def test_rejects_cloze_without_blank(self) -> None:
        result = self.run_validator(valid_note(target_chunk_cloze="The storm inflicted damage."))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk_cloze must contain a blank", result.stderr)

    def test_rejects_word_level_chunk_meaning(self) -> None:
        result = self.run_validator(valid_note(target_chunk_meaning="vt. 造成；使承受"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("target_chunk_meaning should be a phrase-level Chinese anchor", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run validator tests and verify they fail**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_validate_phrase_chunks -v
```

Expected: failures for missing validation messages.

- [ ] **Step 3: Add phrase chunk validation helpers**

Modify `skills/eudic-to-anki/scripts/validate_trvs_coach_json.py`.

Add imports:

```python
from coach_fields import (
    LEARNING_PRIORITY_VALUES,
    TARGET_CHUNK_CLOZE_KEYS,
    TARGET_CHUNK_KEYS,
    TARGET_CHUNK_MEANING_KEYS,
    first_text_field,
    meaning_line_has_pos_prefix,
)
```

Add constants near the regex constants:

```python
_CLOZE_BLANK_RE = re.compile(r"_{2,}|\[[^\]]*blank[^\]]*\]|\bblank\b", re.I)
_CHINESE_POS_PREFIX_RE = re.compile(r"^[a-z]{1,12}\.\s*", re.I)
```

Add helper:

```python
def _validate_phrase_chunk_fields(note: dict[str, Any], index: int, word: str) -> list[str]:
    errs: list[str] = []
    priority = str(note.get("learning_priority") or "").strip()
    target_chunk = first_text_field(note, TARGET_CHUNK_KEYS)
    target_chunk_meaning = first_text_field(note, TARGET_CHUNK_MEANING_KEYS)
    target_chunk_cloze = first_text_field(note, TARGET_CHUNK_CLOZE_KEYS)

    if not target_chunk:
        errs.append(f"note[{index}] word={word!r}: target_chunk must not be empty")
    if not target_chunk_meaning:
        errs.append(f"note[{index}] word={word!r}: target_chunk_meaning must not be empty")
    elif _CHINESE_POS_PREFIX_RE.match(target_chunk_meaning) or len(target_chunk_meaning) > 24:
        errs.append(
            f"note[{index}] word={word!r}: target_chunk_meaning should be a phrase-level "
            f"Chinese anchor, not a word-level dictionary gloss (got {target_chunk_meaning!r})"
        )

    if priority == "focus":
        if not target_chunk_cloze:
            errs.append(f"note[{index}] word={word!r}: focus notes need target_chunk_cloze")
        elif not _CLOZE_BLANK_RE.search(target_chunk_cloze):
            errs.append(
                f"note[{index}] word={word!r}: target_chunk_cloze must contain a blank "
                "such as ____"
            )
        elif _english_word_count(target_chunk_cloze) < 4:
            errs.append(
                f"note[{index}] word={word!r}: target_chunk_cloze must be a natural "
                f"sentence, got {target_chunk_cloze!r}"
            )
    elif priority in {"passive", "ignore"} and target_chunk_cloze:
        errs.append(
            f"note[{index}] word={word!r}: {priority} notes must leave target_chunk_cloze empty"
        )

    return errs
```

- [ ] **Step 4: Call phrase chunk validation from `_check_note`**

At the end of `_check_note`, before `return errs`, add:

```python
    errs.extend(_validate_phrase_chunk_fields(note, index, w))
```

Do not add `target_chunk_cloze` to `REQUIRED_KEYS`; passive and ignore notes may omit it.

Add `target_chunk` and `target_chunk_meaning` to `REQUIRED_KEYS`:

```python
REQUIRED_KEYS = (
    "word",
    "pronunciation",
    "part_of_speech",
    "meaning",
    "english_definition",
    "root",
    "example",
    "collocations",
    "audio_html",
    "learning_priority",
    "target_chunk",
    "target_chunk_meaning",
)
```

- [ ] **Step 5: Run validator tests and full tests**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_validate_phrase_chunks -v
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 6: Commit validator rules**

```bash
git add skills/eudic-to-anki/scripts/validate_trvs_coach_json.py \
  tests/eudic_to_anki/test_validate_phrase_chunks.py
git commit -m "feat: validate phrase chunk fields"
```

### Task 3: Add Fresh-Start Chunk Model Spec And Templates

**Files:**
- Modify: `skills/eudic-to-anki/assets/trvs_lab_model.json`
- Create: `skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_front.html`
- Create: `skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_back.html`
- Create: `skills/eudic-to-anki/assets/trvs_lab_chunk_recall_front.html`
- Create: `skills/eudic-to-anki/assets/trvs_lab_chunk_recall_back.html`
- Modify: `skills/eudic-to-anki/assets/trvs_lab_styling.css`
- Create: `tests/eudic_to_anki/test_trvs_lab_model_spec.py`

- [ ] **Step 1: Write failing model spec tests**

Create `tests/eudic_to_anki/test_trvs_lab_model_spec.py`:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "skills" / "eudic-to-anki" / "assets"


class TrvsLabModelSpecTests(unittest.TestCase):
    def test_model_spec_has_phrase_chunk_fields(self) -> None:
        spec = json.loads((ASSETS / "trvs_lab_model.json").read_text(encoding="utf-8"))
        self.assertIn("目标短语块", spec["fields"])
        self.assertIn("短语块锚点", spec["fields"])
        self.assertIn("短语块挖空", spec["fields"])

    def test_model_spec_has_anchor_and_recall_templates(self) -> None:
        spec = json.loads((ASSETS / "trvs_lab_model.json").read_text(encoding="utf-8"))
        names = [template["Name"] for template in spec["card_templates"]]
        self.assertEqual(names, ["Chunk Anchor", "Chunk Recall"])

    def test_template_files_exist_and_reference_new_fields(self) -> None:
        anchor_front = (ASSETS / "trvs_lab_chunk_anchor_front.html").read_text(encoding="utf-8")
        anchor_back = (ASSETS / "trvs_lab_chunk_anchor_back.html").read_text(encoding="utf-8")
        recall_front = (ASSETS / "trvs_lab_chunk_recall_front.html").read_text(encoding="utf-8")
        recall_back = (ASSETS / "trvs_lab_chunk_recall_back.html").read_text(encoding="utf-8")
        self.assertIn("{{目标短语块}}", anchor_front)
        self.assertIn("{{FrontSide}}", anchor_back)
        self.assertIn("{{#短语块挖空}}", recall_front)
        self.assertIn("{{目标短语块}}", recall_back)
        self.assertNotIn("{{短语块锚点}}", recall_back)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run model tests and verify they fail**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_trvs_lab_model_spec -v
```

Expected: missing field/template failures.

- [ ] **Step 3: Replace model spec fields and templates**

Modify `skills/eudic-to-anki/assets/trvs_lab_model.json`:

```json
{
  "model_name": "TRVS-Lab",
  "fields": [
    "单词",
    "音标",
    "释义",
    "英英",
    "词根",
    "例句",
    "常用搭配",
    "目标短语块",
    "短语块锚点",
    "短语块挖空",
    "发音",
    "学习标记"
  ],
  "card_templates": [
    {
      "Name": "Chunk Anchor",
      "FrontPath": "trvs_lab_chunk_anchor_front.html",
      "BackPath": "trvs_lab_chunk_anchor_back.html"
    },
    {
      "Name": "Chunk Recall",
      "FrontPath": "trvs_lab_chunk_recall_front.html",
      "BackPath": "trvs_lab_chunk_recall_back.html"
    }
  ],
  "css_path": "trvs_lab_styling.css"
}
```

- [ ] **Step 4: Create anchor front template**

Create `skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_front.html`:

```html
<div class="section top chunk-card chunk-anchor-card">
  <div class="items chunk-head">
    <span class="chunk-main">{{目标短语块}}</span>
    <span class="audio block">{{发音}}</span>
  </div>
  <div id="instance" class="items chunk-example">{{例句}}</div>
</div>

<script>
(function() {
  var chunk = document.querySelector(".chunk-main");
  var instance = document.querySelector("#instance");
  if (!chunk || !instance || !instance.textContent.trim()) {
    return;
  }
  var words = chunk.textContent.trim().split(/\s+/).filter(Boolean);
  if (!words.length) {
    return;
  }
  var pattern = words
    .filter(function(word) { return word.length > 2; })
    .map(function(word) { return word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); })
    .join("|");
  if (!pattern) {
    return;
  }
  var regex = new RegExp("\\b(?:" + pattern + ")\\b", "gi");
  instance.innerHTML = instance.innerHTML.replace(regex, function(match) {
    return "<b><u>" + match + "</u></b>";
  });
})();
</script>
```

- [ ] **Step 5: Create anchor back template**

Create `skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_back.html`:

```html
{{FrontSide}}
<div class="section bounceInUp chunk-answer">
  <div class="items phenic">{{音标}}</div>
  <div class="items meaning-row"><span class="type">{{释义}}</span></div>
  <div class="items">{{英英}}</div>
  {{#词根}}
    <div class="items root-field">{{词根}}</div>
  {{/词根}}
  <div class="items collocations-field">{{常用搭配}}</div>
  {{#学习标记}}
  <div class="priority-row"><span class="priority-marker">{{学习标记}}</span></div>
  {{/学习标记}}
</div>

<script type="text/javascript">
(function() {
  var colorMap = {
    "n.":"#86c440",
    "a.":"#f8b002",
    "adj.":"#727272",
    "ad.":"#684b9d",
    "adv.":"#684b9d",
    "v.":"#479cdf",
    "vi.":"#3e480d",
    "vt.":"#3e480d",
    "prep.":"#04B7C9",
    "conj.":"#04B7C9",
    "pron.":"#04B7C9",
    "art.":"#04B7C9",
    "num.":"#04B7C9",
    "int.":"#04B7C9",
    "interj.":"#04B7C9",
    "modal.":"#04B7C9",
    "aux.":"#04B7C9",
    "pl.":"#D111D3",
    "abbr.":"#D111D3",
    "na.":"#04B7C9"
  };
  [].forEach.call(document.querySelectorAll(".type"), function(div) {
    div.innerHTML = div.innerHTML.replace(/\b[a-z]+\./g, function(symbol) {
      if (colorMap[symbol]) {
        return '<a style="font-family:Georgia;font-style:italic;font-weight:bold;color:' +
          colorMap[symbol] + ';border-radius:4px;padding:0 3px;margin-right:2px;">' +
          symbol + "</a>";
      }
      return symbol;
    });
  });

  var rootDiv = document.querySelector(".root-field");
  if (rootDiv) {
    var value = rootDiv.textContent.trim();
    if (value === "-" || value === "无") {
      rootDiv.style.display = "none";
    }
  }
})();
</script>
```

- [ ] **Step 6: Create recall front template**

Create `skills/eudic-to-anki/assets/trvs_lab_chunk_recall_front.html`:

```html
{{#短语块挖空}}
<div class="section top chunk-card chunk-recall-card">
  <div class="items recall-cloze">{{短语块挖空}}</div>
  <div class="items chunk-meaning">{{短语块锚点}}</div>
</div>
{{/短语块挖空}}
```

- [ ] **Step 7: Create recall back template**

Create `skills/eudic-to-anki/assets/trvs_lab_chunk_recall_back.html`:

```html
{{FrontSide}}
<div class="section bounceInUp chunk-answer chunk-recall-answer">
  <div class="items chunk-head">
    <span class="chunk-main">{{目标短语块}}</span>
    <span class="audio block">{{发音}}</span>
  </div>
  <div class="items phenic">{{音标}}</div>
  <div class="items meaning-row"><span class="type">{{释义}}</span></div>
  <div class="items collocations-field recall-collocations">{{常用搭配}}</div>
</div>

<script>
(function() {
  var field = document.querySelector(".recall-collocations");
  if (!field) {
    return;
  }
  var parts = field.innerHTML
    .split(/<br\s*\/?>/i)
    .map(function(part) { return part.trim(); })
    .filter(Boolean)
    .slice(0, 2);
  field.innerHTML = parts.join("<br>");
})();
</script>
```

- [ ] **Step 8: Add phrase chunk CSS**

Append to `skills/eudic-to-anki/assets/trvs_lab_styling.css`:

```css
.chunk-head {
  text-align: center;
}

.chunk-main {
  display: inline-block;
  font-family: courier, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 25px;
  font-weight: 800;
  line-height: 1.15;
}

.chunk-example,
.recall-cloze {
  white-space: pre-wrap;
  font-size: 20px;
  line-height: 1.45;
}

.chunk-meaning {
  border-left: 4px solid rgba(0, 128, 128, 0.7);
  color: rgba(0, 0, 0, 0.76);
  font-weight: 700;
  padding-left: 10px;
}

.chunk-answer .chunk-main {
  font-size: 23px;
}

.collocations-field {
  line-height: 1.45;
}
```

- [ ] **Step 9: Run model tests and full tests**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_trvs_lab_model_spec -v
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 10: Commit model and templates**

```bash
git add skills/eudic-to-anki/assets/trvs_lab_model.json \
  skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_front.html \
  skills/eudic-to-anki/assets/trvs_lab_chunk_anchor_back.html \
  skills/eudic-to-anki/assets/trvs_lab_chunk_recall_front.html \
  skills/eudic-to-anki/assets/trvs_lab_chunk_recall_back.html \
  skills/eudic-to-anki/assets/trvs_lab_styling.css \
  tests/eudic_to_anki/test_trvs_lab_model_spec.py
git commit -m "feat: add phrase chunk Anki templates"
```

### Task 4: Map Phrase Chunk Fields Into Anki Payloads

**Files:**
- Modify: `skills/eudic-to-anki/scripts/ankiconnect_import.py`
- Create: `tests/eudic_to_anki/test_ankiconnect_phrase_fields.py`

- [ ] **Step 1: Write failing field mapping tests**

Create `tests/eudic_to_anki/test_ankiconnect_phrase_fields.py`:

```python
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import",
    SCRIPTS / "ankiconnect_import.py",
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class AnkiconnectPhraseFieldTests(unittest.TestCase):
    def test_build_trvs_lab_fields_maps_phrase_chunk_fields(self) -> None:
        fields = ankiconnect_import.build_trvs_lab_fields(
            {
                "word": "inflict",
                "pronunciation": "/ɪnˈflɪkt/",
                "part_of_speech": "vt.",
                "meaning": ["造成；使承受"],
                "english_definition": "to make someone suffer harm, pain, or damage",
                "root": "in-（进入）+ flict（打击）",
                "example": "The storm inflicted serious damage on the town.",
                "collocations": ["inflict pain on", "inflict punishment on"],
                "target_chunk": "inflict damage on",
                "target_chunk_meaning": "造成严重伤害",
                "target_chunk_cloze": "The storm ____ serious damage on the town.",
                "learning_priority": "focus",
            },
            "[sound:inflict.mp3]",
        )
        self.assertEqual(fields["目标短语块"], "inflict damage on")
        self.assertEqual(fields["短语块锚点"], "造成严重伤害")
        self.assertEqual(fields["短语块挖空"], "The storm ____ serious damage on the town.")
        self.assertEqual(fields["发音"], "[sound:inflict.mp3]")

    def test_required_payload_fields_include_phrase_anchor_fields(self) -> None:
        fields = {
            "单词": "inflict",
            "音标": "/ɪnˈflɪkt/",
            "释义": "vt. 造成；使承受",
            "英英": "to make someone suffer harm, pain, or damage",
            "词根": "in-（进入）+ flict（打击）",
            "例句": "The storm inflicted serious damage on the town.",
            "常用搭配": "inflict pain on<br>inflict punishment on",
            "目标短语块": "",
            "短语块锚点": "造成严重伤害",
            "短语块挖空": "The storm ____ serious damage on the town.",
            "学习标记": "★",
        }
        missing = ankiconnect_import._missing_required_field_names(
            fields,
            require_audio=False,
        )
        self.assertIn("目标短语块", missing)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run field mapping tests and verify they fail**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_ankiconnect_phrase_fields -v
```

Expected: failures for missing fields.

- [ ] **Step 3: Update constants and field mapping**

Modify `skills/eudic-to-anki/scripts/ankiconnect_import.py`.

Update imports:

```python
from coach_fields import (
    LEARNING_PRIORITY_VALUES,
    TARGET_CHUNK_CLOZE_KEYS,
    TARGET_CHUNK_KEYS,
    TARGET_CHUNK_MEANING_KEYS,
    first_text_field,
    fuse_pos_into_meaning,
    learning_priority_marker,
    normalize_learning_priority,
)
```

Update required fields:

```python
TRVS_REQUIRED_FIELDS = (
    "音标",
    "释义",
    "英英",
    "词根",
    "例句",
    "常用搭配",
    "目标短语块",
    "短语块锚点",
    "学习标记",
)
```

Update `build_trvs_lab_fields`:

```python
def build_trvs_lab_fields(note: dict[str, Any], audio_html: str) -> dict[str, str]:
    """Map JSON / coach notes onto the fresh-start TRVS-Lab phrase chunk note type."""
    meaning_values = normalize_list(note.get("meaning") or note.get("释义"))
    pos = field_value(note, "词性", "part_of_speech", "pos")
    meaning_values = fuse_pos_into_meaning(meaning_values, pos)
    collocation_values = normalize_list(note.get("collocations") or note.get("常用搭配"))
    return {
        "单词": field_value(note, "单词", "word"),
        "音标": field_value(note, "音标", "pronunciation"),
        "释义": list_to_text(meaning_values, "；"),
        "英英": field_value(note, "英英", "english_definition", "definition_en"),
        "词根": root_field_value(note, "词根", "root", "root_affix"),
        "例句": field_value(note, "例句", "example"),
        "常用搭配": list_to_text(collocation_values, "<br>"),
        "目标短语块": first_text_field(note, TARGET_CHUNK_KEYS),
        "短语块锚点": first_text_field(note, TARGET_CHUNK_MEANING_KEYS),
        "短语块挖空": first_text_field(note, TARGET_CHUNK_CLOZE_KEYS),
        "发音": audio_html or field_value(note, "发音", "audio_html"),
        "学习标记": note_learning_marker(note),
    }
```

- [ ] **Step 4: Run field mapping tests and full tests**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_ankiconnect_phrase_fields -v
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 5: Commit field mapping**

```bash
git add skills/eudic-to-anki/scripts/ankiconnect_import.py \
  tests/eudic_to_anki/test_ankiconnect_phrase_fields.py
git commit -m "feat: map phrase chunk fields to TRVS-Lab"
```

### Task 5: Route Generated Cards To Chunk Decks

**Files:**
- Modify: `skills/eudic-to-anki/scripts/ankiconnect_import.py`
- Create: `tests/eudic_to_anki/test_ankiconnect_card_routing.py`

- [ ] **Step 1: Write failing card routing tests**

Create `tests/eudic_to_anki/test_ankiconnect_card_routing.py`:

```python
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import",
    SCRIPTS / "ankiconnect_import.py",
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.cards = {
            101: {"cardId": 101, "note": 1, "ord": 0, "deckName": "words"},
            102: {"cardId": 102, "note": 1, "ord": 1, "deckName": "words"},
            201: {"cardId": 201, "note": 2, "ord": 0, "deckName": "words"},
        }

    def invoke(self, action: str, **params: Any) -> Any:
        self.calls.append((action, params))
        if action == "notesInfo":
            notes = params["notes"]
            result = []
            for note_id in notes:
                if note_id == 1:
                    result.append(
                        {
                            "noteId": 1,
                            "fields": {
                                "单词": {"value": "inflict"},
                                "学习标记": {"value": "★"},
                            },
                            "cards": [101, 102],
                        }
                    )
                if note_id == 2:
                    result.append(
                        {
                            "noteId": 2,
                            "fields": {
                                "单词": {"value": "sphinx"},
                                "学习标记": {"value": "◇"},
                            },
                            "cards": [201],
                        }
                    )
            return result
        if action == "cardsInfo":
            return [self.cards[card_id] for card_id in params["cards"]]
        if action == "changeDeck":
            return None
        return None


class CardRoutingTests(unittest.TestCase):
    def test_chunk_deck_names_are_action_first(self) -> None:
        self.assertEqual(
            ankiconnect_import.chunk_anchor_deck_name("words", "focus"),
            "words::chunk-anchor::focus",
        )
        self.assertEqual(
            ankiconnect_import.chunk_recall_deck_name("words"),
            "words::chunk-recall::focus",
        )

    def test_route_focus_note_cards_to_anchor_and_recall_decks(self) -> None:
        client = FakeClient()
        ankiconnect_import.route_trvs_chunk_cards(client, [1], base_deck="words")
        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertIn(
            ("changeDeck", {"cards": [101], "deck": "words::chunk-anchor::focus"}),
            change_calls,
        )
        self.assertIn(
            ("changeDeck", {"cards": [102], "deck": "words::chunk-recall::focus"}),
            change_calls,
        )

    def test_route_passive_note_only_to_anchor_deck(self) -> None:
        client = FakeClient()
        ankiconnect_import.route_trvs_chunk_cards(client, [2], base_deck="words")
        change_calls = [call for call in client.calls if call[0] == "changeDeck"]
        self.assertEqual(
            change_calls,
            [("changeDeck", {"cards": [201], "deck": "words::chunk-anchor::passive"})],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run routing tests and verify they fail**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_ankiconnect_card_routing -v
```

Expected: missing helper function failures.

- [ ] **Step 3: Add card template and deck routing constants**

Modify `skills/eudic-to-anki/scripts/ankiconnect_import.py` near constants:

```python
CHUNK_ANCHOR_TEMPLATE = "Chunk Anchor"
CHUNK_RECALL_TEMPLATE = "Chunk Recall"
CHUNK_TEMPLATE_BY_ORD = {
    0: CHUNK_ANCHOR_TEMPLATE,
    1: CHUNK_RECALL_TEMPLATE,
}
```

Add helpers near deck helpers:

```python
def chunk_anchor_deck_name(base_deck: str, priority: str) -> str:
    deck = base_deck.strip() or DEFAULT_DECK
    return f"{deck}::chunk-anchor::{priority}"


def chunk_recall_deck_name(base_deck: str) -> str:
    deck = base_deck.strip() or DEFAULT_DECK
    return f"{deck}::chunk-recall::focus"


def chunk_decks_for_priority(base_deck: str, priority: str) -> list[str]:
    decks = [chunk_anchor_deck_name(base_deck, priority)]
    if priority == "focus":
        decks.append(chunk_recall_deck_name(base_deck))
    return decks


def all_chunk_decks(base_deck: str) -> list[str]:
    return [
        chunk_anchor_deck_name(base_deck, priority)
        for priority in LEARNING_PRIORITY_VALUES
    ] + [chunk_recall_deck_name(base_deck)]
```

- [ ] **Step 4: Add card template identification and routing**

Add helpers before `upsert_dia_notes`:

```python
def _card_template_name(card_info: dict[str, Any]) -> str:
    explicit = str(card_info.get("template") or card_info.get("templateName") or "").strip()
    if explicit:
        return explicit
    if "ord" in card_info:
        try:
            return CHUNK_TEMPLATE_BY_ORD[int(card_info["ord"])]
        except (KeyError, TypeError, ValueError) as exc:
            raise AnkiImportError(
                f"Could not identify card template for card {card_info.get('cardId')}: "
                f"unexpected ord {card_info.get('ord')!r}"
            ) from exc
    raise AnkiImportError(
        f"Could not identify card template for card {card_info.get('cardId')}: "
        "cardsInfo response has no template/templateName/ord"
    )


def _priority_from_note_info(info: dict[str, Any]) -> str:
    fields = info.get("fields") or {}
    marker = _field_text_value(fields.get("学习标记"))
    if marker == "★":
        return "focus"
    if marker == "◇":
        return "passive"
    if marker == "×":
        return "ignore"
    word = _field_text_value(fields.get("单词")) or f"note:{info.get('noteId', '?')}"
    raise AnkiImportError(f"Cannot route cards for {word}: unknown 学习标记 {marker!r}")


def route_trvs_chunk_cards(
    client: AnkiConnectClient,
    note_ids: list[int],
    *,
    base_deck: str,
) -> None:
    if not note_ids:
        return
    note_infos = client.invoke("notesInfo", notes=note_ids)
    for info in note_infos or []:
        note_id = int(info.get("noteId") or info.get("note") or 0)
        word = _field_text_value((info.get("fields") or {}).get("单词")) or f"note:{note_id}"
        priority = _priority_from_note_info(info)
        card_ids = [int(card_id) for card_id in info.get("cards") or []]
        if not card_ids:
            raise AnkiImportError(f"{word}: no generated cards to route")
        card_infos = client.invoke("cardsInfo", cards=card_ids)
        grouped: dict[str, list[int]] = {}
        seen_templates: set[str] = set()
        for card in card_infos or []:
            card_id = int(card.get("cardId") or card.get("card") or 0)
            template = _card_template_name(card)
            seen_templates.add(template)
            if template == CHUNK_ANCHOR_TEMPLATE:
                deck = chunk_anchor_deck_name(base_deck, priority)
            elif template == CHUNK_RECALL_TEMPLATE and priority == "focus":
                deck = chunk_recall_deck_name(base_deck)
            elif template == CHUNK_RECALL_TEMPLATE:
                raise AnkiImportError(f"{word}: non-focus note generated a Chunk Recall card")
            else:
                raise AnkiImportError(
                    f"{word}: unexpected card template {template!r} for card {card_id}"
                )
            grouped.setdefault(deck, []).append(card_id)
        if CHUNK_ANCHOR_TEMPLATE not in seen_templates:
            raise AnkiImportError(f"{word}: missing Chunk Anchor card")
        if priority == "focus" and CHUNK_RECALL_TEMPLATE not in seen_templates:
            raise AnkiImportError(f"{word}: focus note did not generate a Chunk Recall card")
        for deck, cards in grouped.items():
            client.invoke("changeDeck", cards=cards, deck=deck)
```

- [ ] **Step 5: Ensure chunk decks instead of old priority decks**

In `main`, replace target deck calculation for `TRVS-Lab` with chunk decks:

```python
        if args.model == STRUCTURED_VOCAB_MODEL and not args.no_priority_decks:
            target_decks = {
                deck_name
                for note in raw_notes
                for deck_name in chunk_decks_for_priority(
                    args.deck,
                    note_learning_priority(note),
                )
            }
        else:
            target_decks = {
                note_target_deck(
                    note,
                    base_deck=args.deck,
                    model=args.model,
                    use_priority_decks=use_priority_decks,
                )
                for note in raw_notes
            }
```

Keep `args.deck` in `decks_to_ensure` so notes can be created before routing.

- [ ] **Step 6: Route cards after add or upsert**

After adding or updating notes, before required field verification, call:

```python
        if args.model == STRUCTURED_VOCAB_MODEL and use_priority_decks and not args.dry_run:
            route_trvs_chunk_cards(client, affected_note_ids, base_deck=args.deck)
            print(f"Routed generated cards into phrase chunk decks for {len(affected_note_ids)} note(s).")
```

In `upsert_dia_notes`, remove the current `changeDeck` call that moves all cards to `payload["deckName"]`. Keep `forgetCards` after card ids are collected:

```python
                if not preserve_progress_on_update:
                    if card_ids:
                        client.invoke("forgetCards", cards=card_ids)
```

- [ ] **Step 7: Search all chunk decks during dia-upsert**

Replace `priority_search_decks` use for structured model dry-run and upsert search with:

```python
search_decks = [args.deck, *all_chunk_decks(args.deck)]
```

Inside `upsert_dia_notes`, compute search decks once:

```python
        search_decks = [base_deck, *all_chunk_decks(base_deck)] if use_priority_decks else [payload["deckName"]]
        nids = find_dia_note_ids_in_decks(
            client,
            search_decks,
            payload["modelName"],
            word,
        )
```

- [ ] **Step 8: Run routing tests and full tests**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_ankiconnect_card_routing -v
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 9: Commit card routing**

```bash
git add skills/eudic-to-anki/scripts/ankiconnect_import.py \
  tests/eudic_to_anki/test_ankiconnect_card_routing.py
git commit -m "feat: route phrase chunk cards by template"
```

### Task 6: Update Fresh-Start Model Sync Behavior

**Files:**
- Modify: `skills/eudic-to-anki/scripts/ankiconnect_import.py`
- Modify: `skills/eudic-to-anki/scripts/sync_trvs_lab_model.py`
- Create: `tests/eudic_to_anki/test_trvs_model_sync.py`

- [ ] **Step 1: Write failing sync tests**

Create `tests/eudic_to_anki/test_trvs_model_sync.py`:

```python
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "eudic-to-anki" / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "ankiconnect_import",
    SCRIPTS / "ankiconnect_import.py",
)
assert spec is not None and spec.loader is not None
ankiconnect_import = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankiconnect_import)


class TrvsModelSyncTests(unittest.TestCase):
    def test_model_templates_need_update_when_chunk_templates_missing(self) -> None:
        templates = {"Card 1": {"Front": "{{单词}}", "Back": "{{释义}}"}}
        self.assertTrue(ankiconnect_import._model_templates_need_update(templates))

    def test_model_templates_do_not_need_update_when_chunk_templates_exist(self) -> None:
        templates = {
            "Chunk Anchor": {"Front": "{{目标短语块}}", "Back": "{{FrontSide}}"},
            "Chunk Recall": {"Front": "{{#短语块挖空}}{{短语块挖空}}{{/短语块挖空}}", "Back": "{{目标短语块}}"},
        }
        self.assertFalse(ankiconnect_import._model_templates_need_update(templates))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run sync tests and verify they fail**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_trvs_model_sync -v
```

Expected: current `_model_templates_need_update` does not recognize fresh-start chunk templates.

- [ ] **Step 3: Update template and CSS freshness checks**

Modify `_model_templates_need_update`:

```python
def _model_templates_need_update(templates: Any) -> bool:
    if not isinstance(templates, dict):
        return True
    required = {CHUNK_ANCHOR_TEMPLATE, CHUNK_RECALL_TEMPLATE}
    if not required.issubset(set(templates.keys())):
        return True
    anchor = str((templates.get(CHUNK_ANCHOR_TEMPLATE) or {}).get("Front") or "")
    recall = str((templates.get(CHUNK_RECALL_TEMPLATE) or {}).get("Front") or "")
    return "{{目标短语块}}" not in anchor or "{{短语块挖空}}" not in recall
```

Modify `_model_css_needs_update`:

```python
def _model_css_needs_update(styling: Any) -> bool:
    if isinstance(styling, dict):
        css = str(styling.get("css") or "")
    else:
        css = str(styling or "")
    return ".chunk-main" not in css or ".priority-marker" not in css
```

- [ ] **Step 4: Update sync script description**

In `skills/eudic-to-anki/scripts/sync_trvs_lab_model.py`, update the parser description:

```python
description=(
    "Update the fresh-start TRVS-Lab Anki note type with bundled phrase chunk "
    "fields, card templates, and styling. This version is not compatible with "
    "old TRVS-Lab notes that lack phrase chunk fields."
)
```

- [ ] **Step 5: Run sync tests and full tests**

Run:

```bash
python3 -m unittest tests.eudic_to_anki.test_trvs_model_sync -v
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 6: Commit fresh-start sync behavior**

```bash
git add skills/eudic-to-anki/scripts/ankiconnect_import.py \
  skills/eudic-to-anki/scripts/sync_trvs_lab_model.py \
  tests/eudic_to_anki/test_trvs_model_sync.py
git commit -m "feat: sync fresh-start phrase chunk model"
```

### Task 7: Update Coach Prompt And Skill Documentation

**Files:**
- Modify: `skills/eudic-to-anki/SKILL.md`
- Modify: `skills/eudic-to-anki/modules/coach/README.md`
- Modify: `skills/eudic-to-anki/modules/import/README.md`
- Modify: `skills/eudic-to-anki/references/word-coach-json-prompt.md`
- Modify: `skills/eudic-to-anki/references/anki.md`
- Modify: `skills/eudic-to-anki/workflows/yesterday.md`
- Modify: `skills/eudic-to-anki/workflows/date-range.md`
- Modify: `skills/eudic-to-anki/workflows/word-list.md`

- [ ] **Step 1: Update coach JSON prompt required fields**

In `skills/eudic-to-anki/references/word-coach-json-prompt.md`, add required fields after `learning_priority`:

```markdown
- `target_chunk` (string, 必填，主短语块锚点)
- `target_chunk_meaning` (string, 必填，短语块中文锚点)
- `target_chunk_cloze` (string, `focus` 必填；`passive` / `ignore` 必须为空字符串)
```

Add field rules:

```markdown
`target_chunk`

- 每个 note 必填。
- 优先写真实、自然、可复用的短语块或搭配，如 `inflict damage on`、`go berserk`、`a look of revulsion`。
- 对具体物件、专名、低输出词，允许写最小语境框架，如 `a sphinx`、`the crook of his arm`。
- 只有确实没有自然词块时才退回单词本身；不要默认把 `target_chunk` 写成 `word`。

`target_chunk_meaning`

- 每个 note 必填。
- 写短语块级中文锚点，不写单词级词典释义。
- 正例：`造成严重伤害`、`突然失控`、`厌恶的表情`。
- 反例：`vt. 造成；使承受`、`一种表示造成伤害的动词短语`。

`target_chunk_cloze`

- `focus` note 必填，`passive` 和 `ignore` 必须写空字符串。
- 必须是自然英文句子，并包含明显空格，如 `____`。
- 正例：`The storm ____ serious damage on the town.`
- 反例：`____ damage on`、`inflict damage on`。
```

- [ ] **Step 2: Update SKILL quality gates**

In `skills/eudic-to-anki/SKILL.md`, replace the deck routing bullet with:

```markdown
- `TRVS-Lab` is a fresh-start phrase chunk model. Before upgrading an existing Anki setup, the user should clear old `TRVS-Lab` notes or relevant decks; old notes without phrase chunk fields are not supported by the new templates.
- Every coach note must include `target_chunk` and `target_chunk_meaning`. `focus` notes must include `target_chunk_cloze`; `passive` and `ignore` notes must leave `target_chunk_cloze` empty so they do not generate recall cards.
- Anki import routes generated cards by review action: Chunk Anchor cards go to `words::chunk-anchor::<focus|passive|ignore>`, while Chunk Recall cards for focus notes go to `words::chunk-recall::focus`.
```

- [ ] **Step 3: Update coach module docs**

In `skills/eudic-to-anki/modules/coach/README.md`, add:

```markdown
- 短语块是新模型的主记忆锚点。每个 note 都必须有 `target_chunk` 和 `target_chunk_meaning`。
- `focus` note 必须有自然句子形式的 `target_chunk_cloze`，用于生成半遮挡召回卡。
- `passive` / `ignore` note 必须让 `target_chunk_cloze` 为空，避免生成召回卡。
```

- [ ] **Step 4: Update import and Anki docs**

In `skills/eudic-to-anki/modules/import/README.md` and `skills/eudic-to-anki/references/anki.md`, replace old `words::focus/passive/ignore` deck descriptions with:

```markdown
- `--deck words` 是 base deck。`TRVS-Lab` 会按卡片类型分流：
  - `words::chunk-anchor::focus`
  - `words::chunk-anchor::passive`
  - `words::chunk-anchor::ignore`
  - `words::chunk-recall::focus`
- 这是 fresh-start breaking upgrade；旧 `TRVS-Lab` note 不保证显示正确。升级前清空旧 note 或相关 deck。
```

- [ ] **Step 5: Update workflow dry-run expectations**

In `skills/eudic-to-anki/workflows/yesterday.md`, `date-range.md`, and `word-list.md`, replace old target deck expectation text:

```markdown
确认输出里的 target decks 包含 `words::chunk-anchor::focus/passive/ignore` 和 `words::chunk-recall::focus`。
```

- [ ] **Step 6: Run documentation grep checks**

Run:

```bash
rg -n "words::focus|words::passive|words::ignore|target_chunk|chunk-anchor|chunk-recall" skills/eudic-to-anki
```

Expected:

- No remaining docs describe `TRVS-Lab` as routing only to `words::focus/passive/ignore`.
- New prompt and docs mention `target_chunk`, `target_chunk_meaning`, and `target_chunk_cloze`.
- Workflow docs mention `chunk-anchor` and `chunk-recall`.

- [ ] **Step 7: Commit documentation updates**

```bash
git add skills/eudic-to-anki/SKILL.md \
  skills/eudic-to-anki/modules/coach/README.md \
  skills/eudic-to-anki/modules/import/README.md \
  skills/eudic-to-anki/references/word-coach-json-prompt.md \
  skills/eudic-to-anki/references/anki.md \
  skills/eudic-to-anki/workflows/yesterday.md \
  skills/eudic-to-anki/workflows/date-range.md \
  skills/eudic-to-anki/workflows/word-list.md
git commit -m "docs: document phrase chunk card workflow"
```

### Task 8: End-To-End Verification

**Files:**
- Create: `tests/eudic_to_anki/fixtures/chunk_focus_import.json`
- Create: `tests/eudic_to_anki/fixtures/chunk_passive_import.json`

- [ ] **Step 1: Add focus fixture**

Create `tests/eudic_to_anki/fixtures/chunk_focus_import.json`:

```json
{
  "notes": [
    {
      "word": "inflict",
      "pronunciation": "/ɪnˈflɪkt/",
      "part_of_speech": "vt.",
      "meaning": ["vt. 造成；使承受"],
      "english_definition": "to make someone suffer harm, pain, or damage",
      "root": "in-（进入）+ flict（打击）",
      "example": "The storm inflicted serious damage on the town.",
      "collocations": ["inflict pain on", "inflict punishment on"],
      "audio_html": "",
      "learning_priority": "focus",
      "target_chunk": "inflict damage on",
      "target_chunk_meaning": "造成严重伤害",
      "target_chunk_cloze": "The storm ____ serious damage on the town."
    }
  ]
}
```

- [ ] **Step 2: Add passive fixture**

Create `tests/eudic_to_anki/fixtures/chunk_passive_import.json`:

```json
{
  "notes": [
    {
      "word": "sphinx",
      "pronunciation": "/sfɪŋks/",
      "part_of_speech": "n.",
      "meaning": ["n. 狮身人面像；难懂的人"],
      "english_definition": "a mythical creature with a human head and a lion's body",
      "root": "-",
      "example": "It was a sphinx.",
      "collocations": ["a stone sphinx", "a sphinx-like expression"],
      "audio_html": "",
      "learning_priority": "passive",
      "target_chunk": "a sphinx",
      "target_chunk_meaning": "一尊狮身人面像",
      "target_chunk_cloze": ""
    }
  ]
}
```

- [ ] **Step 3: Run validator on fixtures**

Run:

```bash
python3 skills/eudic-to-anki/scripts/validate_trvs_coach_json.py tests/eudic_to_anki/fixtures/chunk_focus_import.json
python3 skills/eudic-to-anki/scripts/validate_trvs_coach_json.py tests/eudic_to_anki/fixtures/chunk_passive_import.json
```

Expected:

```text
OK: 1 notes in tests/eudic_to_anki/fixtures/chunk_focus_import.json
OK: 1 notes in tests/eudic_to_anki/fixtures/chunk_passive_import.json
```

- [ ] **Step 4: Run model sync dry-run**

Run:

```bash
python3 skills/eudic-to-anki/scripts/sync_trvs_lab_model.py --dry-run --no-sync
```

Expected output contains:

```text
Model: TRVS-Lab
Fields in bundled spec: 单词, 音标, 释义, 英英, 词根, 例句, 常用搭配, 目标短语块, 短语块锚点, 短语块挖空, 发音, 学习标记
Templates to sync: Chunk Anchor, Chunk Recall
```

- [ ] **Step 5: Run all unit tests**

Run:

```bash
python3 -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 6: Optional live Anki dry-run**

Only run this if Anki Desktop and AnkiConnect are open:

```bash
python3 skills/eudic-to-anki/scripts/ankiconnect_import.py \
  --input tests/eudic_to_anki/fixtures/chunk_focus_import.json \
  --deck words \
  --create-deck \
  --dia-upsert \
  --verify-required-fields \
  --dry-run
```

Expected output includes:

```text
Target decks:
words::chunk-anchor::focus
words::chunk-recall::focus
Verified required TRVS-Lab payload fields.
```

- [ ] **Step 7: Commit fixtures and final verification assets**

```bash
git add tests/eudic_to_anki/fixtures/chunk_focus_import.json \
  tests/eudic_to_anki/fixtures/chunk_passive_import.json
git commit -m "test: add phrase chunk import fixtures"
```

## Plan Self-Review

- Spec coverage: covered fresh-start upgrade, required phrase chunk fields, anchor and recall templates, action-first decks, no chunk audio, validation, docs, and tests.
- Placeholder scan: no implementation steps rely on deferred design decisions.
- Type consistency: JSON keys are `target_chunk`, `target_chunk_meaning`, `target_chunk_cloze`; Anki fields are `目标短语块`, `短语块锚点`, `短语块挖空`; template names are `Chunk Anchor` and `Chunk Recall`.
