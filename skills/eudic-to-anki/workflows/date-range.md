# Workflow: Date Range

执行前先把 `<ABS_TEMP_DIR>` 替换成真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`。规则敏感命令必须直连执行；不要再包 `zsh -lc`，也不要和 `mkdir`、`cd`、`export` 用 `&&` 串接。

1. 解析 `<START>` 到 `<END>`（本地时区）。
2. 若目录不存在，先执行：`mkdir -p <ABS_TEMP_DIR>`
3. 导出：`python3 scripts/eudic_export.py --all-categories --start-date <START> --end-date <END> --format csv --output <ABS_TEMP_DIR>/_week_<START>_<END>_export.csv`
4. 占位：`python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_week_<START>_<END>_export.csv --output <ABS_TEMP_DIR>/_week_<START>_<END>_partial.json --batch-date <START>_<END> --eudic-words-only`
5. 分批生成 coach，必须使用 partial 中的 `source_context` 处理例句，逐批自查后再 merge。
6. 内容自查：确认没有空音标、空英英释义、空例句、空搭配、整批 `root: "-"`、欧路 `exp` 直拷贝、过长/解释式中文释义、弱英英释义或单字母误选词。
7. 终检：`python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/_week_<START>_<END>_import.json`
8. dry-run：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_week_<START>_<END>_import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`
9. 导入必须使用 `--require-audio --verify-required-fields`；抽查 Anki 实际字段与清理同 `workflows/yesterday.md`。
