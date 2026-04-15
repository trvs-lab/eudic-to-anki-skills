# Workflow: Word List

适用于用户直接提供词表（不走 Eudic 导出）。

执行前先把 `<ABS_TEMP_DIR>` 替换成真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`。规则敏感命令必须直连执行；不要再包 `zsh -lc`，也不要和 `mkdir`、`cd`、`export` 用 `&&` 串接。

1. 若目录不存在，先执行：`mkdir -p <ABS_TEMP_DIR>`
2. agent 按 `TRVS-Lab` 八字段生成 `<ABS_TEMP_DIR>/word_list_import.json`。
3. 校验：`python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/word_list_import.json`
4. 导入（成功后默认同步；跳过加 `--no-sync`）：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/word_list_import.json --deck words --create-deck`
5. 若需要发音，添加 audio command（同 `workflows/yesterday.md`）。
