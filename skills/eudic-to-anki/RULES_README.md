# eudic-to-anki Rules README

本文件面向 agent，直接使用下方内嵌模板生成规则文件。

## 目标

只生成一个文件：

- `~/.codex/rules/eudic-to-anki.rules`

## 强制生成步骤

1. 复制下方 `RULE_TEMPLATE` 的完整内容，逐字保持规则结构、顺序、注释和字段。
2. 在写入前，把模板中的所有 `<HOME>` 替换为当前用户电脑上的真实 home 绝对路径（例如 `/Users/alice`）。
3. 写入 `~/.codex/rules/eudic-to-anki.rules`。

## 约束

- 不允许保留 `<HOME>` 占位符到最终 rules 文件。
- 不允许改动规则语义（包括 `pattern`/`decision`/`justification`/`match`）。
- 不允许增删重排任意规则。

## RULE_TEMPLATE

```rules
# Eudic-to-Anki rules (single file, local machine usable)
#
# IMPORTANT:
# 1) These rules are command-prefix based.
# 2) To match reliably, run direct commands (no `FOO=bar ...`, no `zsh -lc ...` wrappers).
# 3) Cover both relative skill-root execution and absolute installed-skill execution.

prefix_rule(
    pattern = ["python3", "scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow Eudic export when running from skill root.",
    match = [
        "python3 scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv",
        "python3 scripts/eudic_export.py --list-categories",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow Eudic export when automation invokes absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv",
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py --list-categories",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/run_with_login_zsh.py", "python3", "scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow wrapped export under login zsh from skill root.",
    match = [
        "python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/run_with_login_zsh.py", "python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py"],
    decision = "allow",
    justification = "Allow wrapped export under login zsh with absolute installed-skill paths.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/run_with_login_zsh.py python3 <HOME>/.agents/skills/eudic-to-anki/scripts/eudic_export.py --all-categories --start-date 2026-05-01 --end-date 2026-05-01 --format csv --output /tmp/eudic-export.csv",
    ],
)

prefix_rule(
    pattern = ["python3", "scripts/ankiconnect_import.py"],
    decision = "allow",
    justification = "Allow AnkiConnect import/ping when running from skill root.",
    match = [
        "python3 scripts/ankiconnect_import.py --ping",
        "python3 scripts/ankiconnect_import.py --input /tmp/day_import.json --deck words --create-deck --dia-upsert",
    ],
)

prefix_rule(
    pattern = ["python3", "<HOME>/.agents/skills/eudic-to-anki/scripts/ankiconnect_import.py"],
    decision = "allow",
    justification = "Allow AnkiConnect import/ping with absolute installed-skill path.",
    match = [
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/ankiconnect_import.py --ping",
        "python3 <HOME>/.agents/skills/eudic-to-anki/scripts/ankiconnect_import.py --input /tmp/day_import.json --deck words --create-deck --dia-upsert",
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
