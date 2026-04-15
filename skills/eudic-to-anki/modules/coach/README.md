# Coach Module

负责 TRVS-Lab 的 8 字段内容质量、批处理合并、编码安全与校验门禁。

## 关键规则

- 由 agent 生成 `pronunciation/meaning/english_definition/root/example/collocations` 等字段。
- 大批量走分批（25-40 词）+ 每批校验 + merge。
- 出现子 agent 信道噪声时，可让子 agent 输出单行 base64，再用解码脚本恢复。
- 导入前必须通过 `validate_trvs_coach_json.py`。

## 执行约束

- 将文档中的 `~/Documents/eudic-to-anki-temp/...` 先展开成真实绝对路径，例如 `/Users/alice/Documents/eudic-to-anki-temp/...`。
- 规则敏感命令必须直连执行；不要再包 `/bin/zsh -lc ...`、`zsh -lc ...`、`bash -lc ...`。
- 不要把 `mkdir`、`cd`、`export` 等准备动作和脚本命令用 `&&`、`||`、`;`、管道或子 shell 串在一起；拆成两条命令执行。
- 若 temp dir 不存在，先单独执行 `mkdir -p /Users/alice/Documents/eudic-to-anki-temp`。

## 脚本

- `python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/export.csv --output <ABS_TEMP_DIR>/partial.json --eudic-words-only`
- `python3 scripts/merge_coach_with_partial.py --partial <ABS_TEMP_DIR>/partial.json --coach <ABS_TEMP_DIR>/coach_batch_01.json -o <ABS_TEMP_DIR>/import.json`
- `python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/import.json`
- `python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o <ABS_TEMP_DIR>/coach_batch_01.json`
- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`

## 参考

- `references/word-coach-json-prompt.md`
