# Context Anchor Coach JSON Prompt

只输出 `{"notes":[...]}` JSON，不输出 Markdown 或说明。

每个导出 encounter 对应一条 coach note。同一单词有多条不同来源时，应分别处理各自的 `source_context`；不得只写一条改写句再套用到所有来源。

## 可导入字段

每条 note 包含：

- `word`: 完整单词或短语
- `pronunciation`: 完整美式 IPA，使用 `/.../`
- `part_of_speech`: `n.`、`vt.`、`vi.`、`adj.`、`adv.`、`phr.` 等
- `meaning`: 非空数组；每项以词性开头，给出当前语境中的简短中文义
- `english_definition`: 4–32 词的自然、解释型英英释义
- `word_family`: 可选；只写真正有帮助的词族或构词提示，不使用 `-` 或 `无`
- `source_context`: 欧路原始来源句；原样保留，没有时为空
- `card_sentence`: 卡片正面例句
- `sentence_origin`: `source`、`adapted`、`generated` 之一
- `source_chunk`: 可选；最多一条，必须出现在 `card_sentence` 中
- `source_chunk_meaning`: 与 `source_chunk` 同时出现的简短中文义
- `learning_group`: `learn`、`defer`、`skip`、`reject` 之一
- `audio_html`: 可为空，由导入器生成
- 欧路元数据：`category_id`、`category_name`、`add_time_utc`、`add_time_local`、`source`、`tags`

## 例句决策

1. 来源句完整、自然、长度合适：轻度清理 HTML 或多余空白，使用 `source`。
2. 来源句过长、含噪、被截断或背景过重：做最小删减或改写，使用 `adapted`。保留原义、事实、目标词义和语气，不虚构新情节。
3. 没有来源句：生成实用例句，使用 `generated`。默认 8–16 个英文词，包含目标词或有效词形，使用常见、高迁移义项，避免专名和额外难词。

`source_context` 永远保存原始输入。生成句不得伪装为真实来源，也不得进入历史语境。

## 分类

- `learn`: 高频、多义、搭配丰富、容易误用、对听说读写有高迁移价值，或属于长期工作／兴趣核心词汇。
- `defer`: 有识别价值，但当前主动掌握收益较低。拿不准时使用此组。
- `skip`: 完整有效，但学习收益很低；仍导入 Anki，由用户人工删除或移动。
- `reject`: 单字母误截、乱码、残缺片段等无效输入；不导入。

不要按词性或“难不难”机械分类。多义词按最有迁移价值的常见义项判断。

## 内容标准

- 不复制欧路 `exp` 作为中文释义，也不批量复制欧路 `phon` 作为最终 IPA。
- 中文释义使用一眼能懂的词典式标签，不写百科解释。
- 英英释义使用日常英文讲清楚含义，不只列同义词，不混入中文。
- `source_chunk` 只从 `source` 或 `adapted` 例句提取；生成例句留空。
- `word_family` 没有明确帮助时留空，不强行拆词。
- 完整 `skip` 条目仍满足所有内容标准。
- `reject` 可以只保留用于诊断的原始内容，不需要补齐学习字段。

输出后必须运行 `scripts/validate_trvs_coach_json.py`。
