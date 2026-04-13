# Workflow: Date Range

1. 解析 `<START>` 到 `<END>`（本地时区）。
2. 导出：`python3 scripts/eudic_export.py --all-categories --start-date <START> --end-date <END> --format csv --output import_scratch/_week_<START>_<END>_export.csv`
3. 占位：`python3 scripts/build_dia_json_from_csv.py --csv import_scratch/_week_<START>_<END>_export.csv --output import_scratch/_week_<START>_<END>_partial.json --batch-date <START>_<END> --eudic-words-only`
4. 分批生成 coach，逐批校验，再 merge。
5. 终检：`python3 scripts/validate_trvs_coach_json.py import_scratch/_week_<START>_<END>_import.json`
6. 导入与清理同 `workflows/yesterday.md`。