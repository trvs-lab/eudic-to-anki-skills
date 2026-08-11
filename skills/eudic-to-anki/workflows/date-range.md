# Workflow: Date Range

「过去一周」「最近 N 天」和明确起止日期都属于一个连续日期范围。先在系统本地时区解析闭区间 `<START>` 至 `<END>`，再执行一次 `eudic_export.py` 调用。不得按天拆分；不得并行运行多个导出命令、工具调用或子 agent。

1. 解析闭区间 `<START>` 至 `<END>`，并使用真实绝对 `<ABS_TEMP_DIR>`。
2. 导出：`python3 scripts/eudic_export.py --all-categories --start-date <START> --end-date <END> --format csv --output <ABS_TEMP_DIR>/_range_<START>_<END>_export.csv`
3. 生成占位：`python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/_range_<START>_<END>_export.csv --output <ABS_TEMP_DIR>/_range_<START>_<END>_partial.json --eudic-words-only`
4. 按规范分批生成 coach，保留同词的每一条欧路遇见元数据；合并后校验。
5. 执行 dry-run，检查 `learn/defer/skip/reject`、新增、更新、`defer → learn`、幂等和重置统计。
6. 使用 `SKILL.md` 的音频导入命令。音频全部成功前不得写入 Anki note/card。
7. 导入后抽查同词多次遇见的计数、最近时间和真实历史语境。

导出因并发保护、限频、网络或解析错误失败时，立即停止本次流程。不得继续生成占位、coach、音频或 Anki 导入，也不得改为逐日重试。
