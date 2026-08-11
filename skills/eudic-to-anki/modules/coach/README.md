# Coach Module

生成 Context Anchor 内容并执行导入前校验。具体字段合同见 `references/word-coach-json-prompt.md`。

## 规则

- 每条可导入记录包含 `pronunciation`、`part_of_speech`、`meaning`、`english_definition`、`card_sentence`、`sentence_origin` 和 `learning_group`。
- `learning_group` 只使用 `learn`、`defer`、`skip`、`reject`。
- `skip` 用于完整但低价值的单词或短语，仍导入 Anki；`reject` 仅用于误截片段、乱码等无效条目，不导入。
- 有干净来源句时使用 `source`。来源句过长、含噪或被截断时使用 `adapted`，只做必要删改并保留原义、事实和语气。
- 没有来源句时使用 `generated`，生成一条包含目标词或有效词形的实用例句，默认 8–16 个英文词。
- `source_context` 始终保存欧路原始语境。不得把生成例句写成真实历史语境。
- `source_chunk` 最多一条，只能从 `source` 或 `adapted` 句中提取；没有明显收益时留空。
- `word_family` 只写真正有帮助的构词线索。非空时使用两行纯文本：第一行以 `拆解：` 开头，第二行以 `联想：` 开头；完整单词带当前相关词性和简短中文义，词根词缀只写中文构词义，联想词保留 1～3 个并逐个标注词性和中文义。不得写入 HTML、`-`、`无` 等占位内容。
- 中文语境释义保持简洁并带词性；英英释义使用简短、自然的解释型英文。
- IPA 必须完整并以 `/.../` 包裹。

## 命令

- 占位：`python3 scripts/build_dia_json_from_csv.py --csv <ABS_TEMP_DIR>/export.csv --output <ABS_TEMP_DIR>/partial.json --eudic-words-only`
- 合并：`python3 scripts/merge_coach_with_partial.py --partial <ABS_TEMP_DIR>/partial.json --coach <ABS_TEMP_DIR>/coach.json -o <ABS_TEMP_DIR>/import.json`
- 校验：`python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/import.json`

校验失败时只重写失败词条，再次校验后才可导入。
