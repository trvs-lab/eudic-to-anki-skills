# Workflow: Yesterday

执行前先把 `<ABS_TEMP_DIR>` 替换成真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`。规则敏感命令必须直连执行；不要再包 `zsh -lc`，也不要和 `mkdir`、`cd`、`export` 用 `&&` 串接。

1. 解析昨天日期（本地时区）为 `<D>`。
2. 若目录不存在，先执行：`mkdir -p <ABS_TEMP_DIR>`
3. 导出：`python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output <ABS_TEMP_DIR>/_day_<D>_export.csv`
4. 占位：`python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_day_<D>_export.csv --output <ABS_TEMP_DIR>/_day_<D>_partial.json --eudic-words-only`
5. agent 按 `references/word-coach-json-prompt.md` 写入精修 coach；使用 partial 中的 `source_context` 处理来源 `example`，学习句写入 `target_chunk_sentence`；必要时分批并 merge。
6. 内容自查：确认没有空音标、空英英释义、空 `target_chunk`、空 `target_chunk_meaning`、空 `target_chunk_sentence`、空搭配、整批 `root: "-"`/`"无"`、整词伪词根（如 `crimson（深红）`）、欧路 `exp` 直拷贝、过长/解释式中文释义、弱英英释义或单字母误选词；`target_chunk_sentence` 必须包含 `target_chunk`，`focus` 的 `target_chunk_cloze` 必须由该学习句挖掉目标短语块得到，`passive` / `ignore` 的 `target_chunk_cloze` 必须为空。
7. 校验：`python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/_day_<D>_import.json`
8. dry-run：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`。确认输出里的 Planned phrase chunk card decks 包含 `words::chunk-anchor::focus/passive/ignore` 和 `words::chunk-recall::focus`。
9. 导入（成功后默认同步 Anki；跳过同步加 `--no-sync`）：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text \"{word}\" --output \"{output}\"'`
10. 导入后抽查 Anki 实际字段：`音标/释义/英英/词根/目标短语块/短语块锚点/短语块例句/短语块挖空/常用搭配/发音`；`例句` 只在有真实来源时出现。
11. 成功后清理：`bash scripts/cleanup_import_artifacts.sh`
