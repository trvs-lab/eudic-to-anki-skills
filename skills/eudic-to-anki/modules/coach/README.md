# Coach Module

负责 TRVS-Lab 的 8 字段内容质量、批处理合并、编码安全与校验门禁。

## 关键规则

- 由 agent 生成 `pronunciation/meaning/english_definition/root/example/collocations` 等字段。
- 大批量走分批（25-40 词）+ 每批校验 + merge。
- 出现子 agent 信道噪声时，可让子 agent 输出单行 base64，再用解码脚本恢复。
- 导入前必须通过 `validate_trvs_coach_json.py`。

## 脚本

- `python3 scripts/build_dia_json_from_csv.py --csv ~/Documents/eudic-to-anki-temp/export.csv --output ~/Documents/eudic-to-anki-temp/partial.json --eudic-words-only`
- `python3 scripts/merge_coach_with_partial.py --partial ~/Documents/eudic-to-anki-temp/partial.json --coach ~/Documents/eudic-to-anki-temp/coach_batch_01.json -o ~/Documents/eudic-to-anki-temp/import.json`
- `python3 scripts/validate_trvs_coach_json.py ~/Documents/eudic-to-anki-temp/import.json`
- `python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o ~/Documents/eudic-to-anki-temp/coach_batch_01.json`

## 参考

- `references/word-coach-json-prompt.md`
