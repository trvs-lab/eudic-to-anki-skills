# Workflow: Word List

适用于用户直接提供词表（不走 Eudic 导出）。

执行前先把 `<ABS_TEMP_DIR>` 替换成真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`。规则敏感命令必须直连执行；不要再包 `zsh -lc`，也不要和 `mkdir`、`cd`、`export` 用 `&&` 串接。

1. 若目录不存在，先执行：`mkdir -p <ABS_TEMP_DIR>`
2. agent 按 `references/word-coach-json-prompt.md` 生成 `<ABS_TEMP_DIR>/word_list_import.json`；没有来源句时才造简洁例句。
3. 内容自查：确认没有空音标、空英英释义、空例句、空搭配、整批 `root: "-"`、过长/解释式中文释义、弱英英释义或单字母误选词。
4. 校验：`python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/word_list_import.json`
5. dry-run：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/word_list_import.json --deck words --create-deck --verify-required-fields --dry-run`
6. 导入（成功后默认同步；跳过加 `--no-sync`）：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/word_list_import.json --deck words --create-deck --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text \"{word}\" --output \"{output}\"'`
7. 导入后抽查 Anki 实际字段：`音标/释义/英英/词根/例句/常用搭配/发音`。
