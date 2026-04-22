# eudic-to-anki Rules README

本文件面向 agent，直接使用下方内嵌模板生成规则文件。

## 目标

只生成一个文件：

- `~/.codex/rules/eudic-to-anki.rules`

## 强制生成步骤

1. 复制下方 `RULE_TEMPLATE` 的完整内容，逐字保持规则结构、顺序、注释和字段。
2. 在写入前，把模板中的所有 `<HOME>` 替换为当前用户电脑上的真实 home 绝对路径（例如 `/Users/alice`）。
3. 写入 `~/.codex/rules/eudic-to-anki.rules`。

## 执行要求

- 这些 rules 是 command-prefix based。
- 命中这些 rules 的命令必须直连执行；不要加 `FOO=bar ...`、`env ...`、`/bin/zsh -lc ...`、`zsh -lc ...`、`bash -lc ...`。
- 不要把 `mkdir`、`cd`、`export` 等准备动作和 rule-covered command 用 `&&`、`||`、`;`、管道或子 shell 串在一起。准备动作请单独执行。
- 绝对路径仍是首选；但模板额外覆盖了字面量 `~/Documents/eudic-to-anki-temp` 的直连 `mkdir -p` 作为 fallback，避免 agent 因此误判“Documents 不可写”。
- `$HOME` 仍然不在规则覆盖范围内；规则敏感命令里不要用 `$HOME`。
- 模板里允许的 `mkdir -p` 只用于 dedicated artifact dir：`<HOME>/Documents/eudic-to-anki-temp`，以及它的字面量 `~/Documents/eudic-to-anki-temp` fallback。

## 约束

- 不允许保留 `<HOME>` 占位符到最终 rules 文件。
- 允许补充本模板中的 match 示例，但不要删除或放宽既有 pattern 的边界。

## RULE_TEMPLATE

```rules
# Eudic-to-Anki rules (single file, local machine usable)
#
# IMPORTANT:
# 1) These rules are command-prefix based.
# 2) To match reliably, run direct commands only:
#    - no `FOO=bar ...`
#    - no `env ...`
#    - no `/bin/zsh -lc ...`, `zsh -lc ...`, or `bash -lc ...`
#    - no `&&` / `||` / `;` wrappers around a rule-covered command
# 3) Absolute paths are preferred. As a fallback, the template also covers direct
#    `mkdir -p ~/Documents/eudic-to-anki-temp` to avoid false "Documents not writable"
#    conclusions. `$HOME` is still not covered.
# 4) Cover both relative skill-root execution and absolute installed-skill execution.
# 5) Temp-dir creation is intentionally limited to the dedicated artifact directory.

prefix_rule(
    pattern = ["mkdir", "-p", "<HOME>/Documents/eudic-to-anki-temp"],
    decision = "allow",
    justification = "Allow preparing the dedicated local artifact directory in a separate direct command.",
    match = [
        "mkdir -p <HOME>/Documents/eudic-to-anki-temp",
    ],
)

prefix_rule(
    pattern = ["mkdir", "-p", "~/Documents/eudic-to-anki-temp"],
    decision = "allow",
    justification = "Allow the same dedicated artifact directory when the direct command uses a literal '~/Documents/...' token.",
    match = [
        "mkdir -p ~/Documents/eudic-to-anki-temp",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow Eudic export when running from skill root.",
    match = [
        "python3 scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_export.csv",
        "python3 scripts/eudic_export.py --list-categories",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow Eudic export when automation invokes absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_export.csv",
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py --list-categories",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/run_with_login_zsh.py", "python3", "scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow wrapped export under login zsh from skill root.",
    match = [
        "python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_export.csv",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/run_with_login_zsh.py", "python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow wrapped export under login zsh with absolute installed-skill paths.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/run_with_login_zsh.py python3 <HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_export.csv",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/build_dia_json_from_csv.py"],
    decision = "allow",
    justification = "Allow placeholder note generation from exported CSV when running from skill root.",
    match = [
        "python3 scripts/build_dia_json_from_csv.py --csv <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_export.csv --output <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_partial.json --batch-date 2026-05-01 --eudic-words-only",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/build_dia_json_from_csv.py"],
    decision = "allow",
    justification = "Allow placeholder note generation from exported CSV with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/build_dia_json_from_csv.py --csv <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_export.csv --output <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_partial.json --batch-date 2026-05-01 --eudic-words-only",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/merge_coach_with_partial.py"],
    decision = "allow",
    justification = "Allow merging authored coach fields into placeholder notes from skill root.",
    match = [
        "python3 scripts/merge_coach_with_partial.py --partial <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_partial.json --coach <HOME>/Documents/eudic-to-anki-temp/coach_batch_01.json -o <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_import.json",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/merge_coach_with_partial.py"],
    decision = "allow",
    justification = "Allow merging authored coach fields into placeholder notes with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/merge_coach_with_partial.py --partial <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_partial.json --coach <HOME>/Documents/eudic-to-anki-temp/coach_batch_01.json -o <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_import.json",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/validate_trvs_coach_json.py"],
    decision = "allow",
    justification = "Allow validating final import JSON from skill root.",
    match = [
        "python3 scripts/validate_trvs_coach_json.py <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_import.json",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/validate_trvs_coach_json.py"],
    decision = "allow",
    justification = "Allow validating final import JSON with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/validate_trvs_coach_json.py <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_import.json",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/merge_minimal_week_import.py"],
    decision = "allow",
    justification = "Allow building minimal week import JSON from skill root.",
    match = [
        "python3 scripts/merge_minimal_week_import.py --csv <HOME>/Documents/eudic-to-anki-temp/_week_2026-05-01_2026-05-07_export.csv --coach-json <HOME>/Documents/eudic-to-anki-temp/minimal_coach_week.json --output <HOME>/Documents/eudic-to-anki-temp/_week_2026-05-01_2026-05-07_import.json",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/merge_minimal_week_import.py"],
    decision = "allow",
    justification = "Allow building minimal week import JSON with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/merge_minimal_week_import.py --csv <HOME>/Documents/eudic-to-anki-temp/_week_2026-05-01_2026-05-07_export.csv --coach-json <HOME>/Documents/eudic-to-anki-temp/minimal_coach_week.json --output <HOME>/Documents/eudic-to-anki-temp/_week_2026-05-01_2026-05-07_import.json",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/decode_subagent_transcript_b64.py"],
    decision = "allow",
    justification = "Allow decoding base64-wrapped subagent output from skill root.",
    match = [
        "python3 scripts/decode_subagent_transcript_b64.py /tmp/subagent.jsonl -o <HOME>/Documents/eudic-to-anki-temp/coach_batch_01.json",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/decode_subagent_transcript_b64.py"],
    decision = "allow",
    justification = "Allow decoding base64-wrapped subagent output with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/decode_subagent_transcript_b64.py /tmp/subagent.jsonl -o <HOME>/Documents/eudic-to-anki-temp/coach_batch_01.json",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/ankiconnect_import.py"],
    decision = "allow",
    justification = "Allow AnkiConnect import/ping when running from skill root.",
    match = [
        "python3 scripts/ankiconnect_import.py --ping",
        "python3 scripts/ankiconnect_import.py --input <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text \"{word}\" --output \"{output}\"'",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/ankiconnect_import.py"],
    decision = "allow",
    justification = "Allow AnkiConnect import/ping with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/ankiconnect_import.py --ping",
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/ankiconnect_import.py --input <HOME>/Documents/eudic-to-anki-temp/_day_2026-05-01_import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 <HOME>/.agents/skills/eudic-to-anki/scripts/edge_tts_runner.py --text \"{word}\" --output \"{output}\"'",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/edge_tts_runner.py"],
    decision = "allow",
    justification = "Allow direct Edge-TTS probe/generation from skill root.",
    match = [
        "python3 scripts/edge_tts_runner.py --text test --output /tmp/test.mp3",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/edge_tts_runner.py"],
    decision = "allow",
    justification = "Allow direct Edge-TTS probe/generation with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/edge_tts_runner.py --text test --output /tmp/test.mp3",
    ],
)

prefix_rule(
    pattern = ["say"],
    decision = "allow",
    justification = "Allow local offline macOS TTS fallback checks when Edge-TTS is unavailable.",
    match = [
        "say test",
    ],
)

prefix_rule(
    pattern = ["bash", "scripts/check_env.sh"],
    decision = "allow",
    justification = "Allow preflight checks from skill root.",
    match = [
        "bash scripts/check_env.sh",
    ],
)

prefix_rule(
    pattern = ["bash", "<HOME>/.agents/skills/eudic-to-anki/scripts/check_env.sh"],
    decision = "allow",
    justification = "Allow preflight checks with absolute installed-skill path.",
    match = [
        "bash <HOME>/.agents/skills/eudic-to-anki/scripts/check_env.sh",
    ],
)

prefix_rule(
    pattern = ["bash", "scripts/cleanup_import_artifacts.sh"],
    decision = "allow",
    justification = "Allow cleanup from skill root.",
    match = [
        "bash scripts/cleanup_import_artifacts.sh",
    ],
)

prefix_rule(
    pattern = ["bash", "<HOME>/.agents/skills/eudic-to-anki/scripts/cleanup_import_artifacts.sh"],
    decision = "allow",
    justification = "Allow cleanup with absolute installed-skill path.",
    match = [
        "bash <HOME>/.agents/skills/eudic-to-anki/scripts/cleanup_import_artifacts.sh",
    ],
)

prefix_rule(
    pattern = ["open", "-a", "Anki"],
    decision = "allow",
    justification = "Allow opening Anki by app name.",
    match = [
        "open -a Anki",
    ],
)

prefix_rule(
    pattern = ["open", "-a", "/Applications/Anki.app"],
    decision = "allow",
    justification = "Allow opening Anki by absolute app path.",
    match = [
        "open -a /Applications/Anki.app",
    ],
)
```
