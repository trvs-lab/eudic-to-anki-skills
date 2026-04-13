# Workflow: Word List

适用于用户直接提供词表（不走 Eudic 导出）。

1. agent 按 `TRVS-Lab` 八字段生成 `import_scratch/word_list_import.json`。
2. 校验：`python3 scripts/validate_trvs_coach_json.py import_scratch/word_list_import.json`
3. 导入：`python3 scripts/ankiconnect_import.py --input import_scratch/word_list_import.json --deck words --create-deck`
4. 若需要发音，添加 audio command（同 `workflows/yesterday.md`）。