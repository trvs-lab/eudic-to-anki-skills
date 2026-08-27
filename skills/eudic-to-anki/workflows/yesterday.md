# Workflow: Yesterday

将 `<ABS_TEMP_DIR>` 替换为真实绝对目录。以下命令分开直连执行。

先完成 `SKILL.md` 的环境检查和 `--resume-eudic-cleanup`；续办失败时不开始新的导出。

1. 按本地时区计算昨天 `<D>`。
2. 创建工件目录：`mkdir -p <ABS_TEMP_DIR>`
3. 导出全部遇见：`python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output <ABS_TEMP_DIR>/_day_<D>_export.csv`
4. 生成逐条遇见占位：`python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_day_<D>_export.csv --output <ABS_TEMP_DIR>/_day_<D>_partial.json --eudic-words-only`
5. 按 `references/word-coach-json-prompt.md` 生成 coach JSON。无来源句时生成 8–16 词实用例句；过长或噪声来源句做最小删改。
6. 合并：`python3 scripts/merge_coach_with_partial.py --partial <ABS_TEMP_DIR>/_day_<D>_partial.json --coach <ABS_TEMP_DIR>/coach.json -o <ABS_TEMP_DIR>/_day_<D>_import.json`
7. 校验：`python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/_day_<D>_import.json`
8. 预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/_day_<D>_import.json --deck words --create-deck --dry-run`
9. 使用 `SKILL.md` 的 Edge-TTS 命令真实导入，并追加 `--cleanup-eudic`。音频第二次失败时停止，不得使用系统 TTS。
10. 抽查单卡正反面、三个 deck、遇见次数和历史语境；成功后清理工件。
