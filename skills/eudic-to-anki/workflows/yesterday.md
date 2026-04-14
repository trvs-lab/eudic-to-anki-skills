# Workflow: Yesterday

1. 解析昨天日期（本地时区）为 `<D>`。
2. 导出：`python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output import_scratch/_day_<D>_export.csv`
3. 占位：`python3 scripts/build_dia_json_from_csv.py --csv import_scratch/_day_<D>_export.csv --output import_scratch/_day_<D>_partial.json --batch-date <D> --eudic-words-only`
4. agent 写入精修 coach；必要时分批并 merge。
5. 校验：`python3 scripts/validate_trvs_coach_json.py import_scratch/_day_<D>_import.json`
6. 导入（成功后默认同步 Anki；跳过同步加 `--no-sync`）：`python3 scripts/ankiconnect_import.py --input import_scratch/_day_<D>_import.json --deck words --create-deck --dia-upsert --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text \"{word}\" --output \"{output}\"'`
7. 成功后清理：`bash scripts/cleanup_import_artifacts.sh`