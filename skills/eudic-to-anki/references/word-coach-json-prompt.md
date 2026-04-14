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

## `root` 字段硬性格式（高优先级）

`root` 只能是以下两种之一：

1. `-`（不可合理拆解，或拆解不具学习价值）
2. 形如：`形式（中文义）+ 形式（中文义）+ ...`

约束：

- 必须使用全角中文括号 `（ ）`，不要用英文括号 `()`
- 每个分段都必须带中文义，不允许只写英文解释
- 不要写词源故事，不要写语法说明句
- 不要写 `past participle / suffix / prefix / form with -ed` 这类英文说明句

正例：

- `de-（离开）+ part（分开）`
- `trans-（跨越）+ port（运送）`
- `-`

反例（禁止）：

- `Past-participle form with -ed.`
- `prefix de- + part`
- `de- (away) + part (part)`

## 输出前自检（必须）

在输出该批 JSON 前，逐词检查：

- `root` 是否满足上面的两种合法格式之一
- 若不合法，立即改写后再输出
