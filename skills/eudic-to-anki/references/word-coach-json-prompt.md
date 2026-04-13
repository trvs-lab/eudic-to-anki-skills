# TRVS-Lab Coach JSON Prompt (Unified)

生成 JSON 顶层对象：`{"notes":[...]}`，每个 note 必须包含：

- `word`
- `pronunciation` (AmE IPA)
- `meaning` (array)
- `english_definition`
- `root`
- `example`
- `collocations` (array)
- `audio_html` (string, 可以为空)

规则：
- 不要输出 markdown fence 或说明文字，只输出 JSON。
- 大批量建议 25-40 词一批。
- 仅当信道噪声明显时，允许子 agent 输出一行 base64（父 agent 解码）。
- 导入前必须通过 `scripts/validate_trvs_coach_json.py`。
