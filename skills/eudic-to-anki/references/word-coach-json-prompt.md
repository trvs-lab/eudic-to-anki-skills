# Context Anchor Coach JSON Prompt

只输出 `{"notes":[...]}` JSON，不输出 Markdown 或说明。

每个导出 encounter 对应一条 coach note。同一单词有多条不同来源时，应分别处理各自的 `source_context`；不得只写一条改写句再套用到所有来源。

## 可导入字段

每条 note 包含：

- `word`: 完整单词或短语
- `pronunciation`: 完整美式 IPA，使用 `/.../`
- `part_of_speech`: `n.`、`vt.`、`vi.`、`adj.`、`adv.`、`phr.` 等
- `meaning`: 非空数组；每项以词性开头，给出当前语境中的简短中文义
- `english_definition`: 通常 6～18 词的自然、解释型英英释义
- `word_family`: 可选；真正有帮助时写成规定的两行纯文本，否则留空
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

## 构词线索

只有拆解可靠、能帮助理解目标词，并且存在有迁移价值的联想词时才填写 `word_family`。使用恰好两个非空逻辑行，不写 HTML：

```text
拆解：构词来源或组成部分 → 目标词
联想：相关词 1、相关词 2
```

- 基础词、目标词和联想词统一写成 `word「词性 中文义」`。只标注当前构词关系需要的词性和义项；动词默认使用 `v.`，只有及物性确实有帮助时才使用 `vt.` 或 `vi.`。
- 前缀、后缀和词根写成 `构词单位「中文构词义」`，不添加词性。
- 「拆解」必须包含目标词及其词性和中文义。可靠的词干变体或字面意义桥接可以在括号或句尾简短说明。
- 「联想」保留 1～3 个最有迁移价值的同根词、反向词缀词或常见派生词；每个词都带词性和中文义，使用 `、` 分隔。
- 优先使用透明派生、常见生产性词缀、能解释当前义项的可靠词根。低置信度词源、无帮助的相似拼写、整词翻译冒充拆解和固定短语强行拆分都应留空。

正例：

```text
拆解：ascend「v. 上升；晋升」→ ascension「n. 上升；晋升」（-ion「名词后缀」，词干变体为 ascens-；scend/scand「攀登、上升」）
联想：ascent「n. 上升；攀登」、descend「v. 下降；下去」
```

```text
拆解：ir-「不」+ reverse「v. 逆转；颠倒」+ -ible「能够……的」→ irreversible「adj. 不可逆转的」
联想：reversible「adj. 可逆的」、reversibility「n. 可逆性」
```

```text
拆解：circum-「环绕、四周」+ spect「看」→ circumspect「adj. 谨慎的；考虑周全的」，字面是「向四周看」
联想：inspect「v. 检查」、prospect「n. 前景」、retrospect「n. 回顾」
```

```text
拆解：bene-「好、善」+ vol/volent「意愿、希望」→ benevolent「adj. 仁慈的；乐善好施的」
联想：benevolence「n. 仁慈；善意」、malevolent「adj. 恶意的」
```

反例包括：只写 `ascend v. 上升；晋升`；只列 `ascent, descend` 而没有词性和中文义；为 `take a toll on` 等固定短语虚构词根词缀；写入 `<br>`、`<strong>` 等 HTML。遇到这些情况时重写为合格的两行内容，无法可靠重写则留空。

## 分类

- `learn`: 高频、多义、搭配丰富、容易误用、对听说读写有高迁移价值，或属于长期工作／兴趣核心词汇。
- `defer`: 有识别价值，但当前主动掌握收益较低。拿不准时使用此组。
- `skip`: 完整有效，但学习收益很低；仍导入 Anki，由用户人工删除或移动。
- `reject`: 单字母误截、乱码、残缺片段等无效输入；不导入。

不要按词性或「难不难」机械分类。多义词按最有迁移价值的常见义项判断。

## 内容标准

- 不复制欧路 `exp` 作为中文释义，也不批量复制欧路 `phon` 作为最终 IPA。
- 中文释义使用一眼能懂的词典式标签，不写百科解释。
- 英英释义使用日常英文讲清楚含义，不只列同义词，不混入中文。
- `source_chunk` 只从 `source` 或 `adapted` 例句提取；生成例句留空。
- `word_family` 没有明确帮助时留空；非空时遵守「构词线索」的两行合同。
- 完整 `skip` 条目仍满足所有内容标准。
- `reject` 可以只保留用于诊断的原始内容，不需要补齐学习字段。

输出后必须运行 `scripts/validate_trvs_coach_json.py`。
