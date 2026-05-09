# TRVS-Lab Coach JSON Prompt (Unified)

生成 JSON 顶层对象：`{"notes":[...]}`，每个 note 必须包含：

- `word`
- `pronunciation` (完整美式 IPA，形如 `/spraɪts/`)
- `part_of_speech` (string, 例如 `n.` / `vt.` / `vi.` / `adj.` / `adv.`)
- `meaning` (non-empty array)
- `english_definition` (non-empty, 简洁解释型英英释义)
- `root`
- `example`
- `collocations` (non-empty array)
- `audio_html` (string, 可以为空)
- `learning_priority` (string, 只能是 `focus` / `passive` / `ignore`)

输入的 partial note 可能还带有 `source_context`，这是欧路导出的真实生词来源句。它不是 Anki 必填字段，但必须用于判断 `example`。

## 输出规则

- 不要输出 markdown fence 或说明文字，只输出 JSON。
- 大批量建议 25-40 词一批。
- 仅当信道噪声明显时，允许子 agent 输出一行 base64（父 agent 解码）。
- 导入前必须通过 `scripts/validate_trvs_coach_json.py`。
- 不要直接复制欧路 `exp` 到 `meaning`，也不要批量复制欧路 `phon` 作为最终音标。

## 字段规则

`pronunciation`

- 必须填写完整美式 IPA，并用 `/.../` 包裹。
- 不能空；不确定时查清楚再输出，不能用占位符。

`part_of_speech` 和 `meaning`

- `part_of_speech` 不能为空，必须是简短词性缩写，例如 `n.`、`vt.`、`vi.`、`adj.`、`adv.`、`phr.`。
- `meaning` 数组中的每一条中文释义都必须以词性缩写开头，例如 `n. 顿悟`、`vt. 推迟`、`adj. 明显的`。
- 中文释义必须由你重新生成，写成简洁、通俗、一眼懂的词典式中文标签。
- 不要把概念解释、成分说明、百科定义写进 `meaning`；这类内容放进 `english_definition`。
- 避免生硬术语或不自然直译；优先选学习者看到就懂的中文。

中文释义正例：

- `carbon dioxide` -> `"meaning": ["n. 二氧化碳"]`
- `sprites` -> `"meaning": ["n. 游戏里的小图；角色图"]`
- `interconnect` -> `"meaning": ["v. 连在一起；互相关联"]`
- `generic` -> `"meaning": ["adj. 普通的；没特色的"]`
- `imagery` -> `"meaning": ["n. 画面感；图像"]`
- `primitives` -> `"meaning": ["n. 基础元素；基本构件"]`

中文释义反例（禁止）：

- `"meaning": ["由一个碳原子和两个氧原子组成的气体"]`
- `"meaning": ["n. 由一个碳原子和两个氧原子组成的气体"]`
- `"meaning": ["精灵图"]`
- `"meaning": ["互相连接"]`
- `"meaning": ["n. 顿悟", "突然明白的时刻"]`

`english_definition`

- 必须生成，不能空。
- 风格接近 vocabulary.com：简洁、通俗、解释型，像在给学习者讲清楚这个词。
- 用日常英文解释词义，不要只给同义词，也不要写成硬邦邦的词典片段。
- 通常写 1 个短句或短语，约 6-25 个英文词；可以点出常见使用场景。
- 不要混入中文，不要复制机器翻译，不要写长篇百科定义。

英英释义正例：

- `carbon dioxide` -> `"english_definition": "a gas that people breathe out and plants use to grow"`
- `sprites` -> `"english_definition": "small images or characters used in a game or animation"`
- `interconnect` -> `"english_definition": "to connect things so they work together as one system"`

英英释义反例（禁止）：

- `"english_definition": ""`
- `"english_definition": "connect; link"`
- `"english_definition": "互相连接"`
- `"english_definition": "a thing"`

`learning_priority`

总目标：分级服务于外语学习者的真实听说读写流畅度，同时兼顾 20000 词汇量和 IELTS 8+。判断时不要只问“这个词难不难”，先问它是否帮助用户更流畅地理解或表达真实内容。

判断漏斗：

1. 这个词是否能提升听、说、读、写任一能力的真实表现？
2. 用户是否需要在未来 6-12 个月主动说出/写出它，还是只需要读到/听到时认得？
3. 它是否是噪声、专名、一次性虚构词、误导出片段，或学习成本明显高于收益？

- `focus`：主动掌握词。能提升口语/写作表达精度，或显著提升阅读/听力理解；B2-C2 高迁移词、IELTS 学术/议论文/观点表达词、抽象概念词、常用动词/形容词/副词、地道搭配、用户工作和长期兴趣中会反复用到的词。
- 多义词按最高迁移价值的常见义项判断：如果一个词既有具体物件义，也有常见抽象义、动词义、评论/修辞义或高价值搭配，并且这些义项能提升表达精度或阅读理解，就应按高价值义项标为 `focus`。例如 `foil` 有“箔”的物件义，但也有 `vt. 挫败`、`n. 衬托人物/事物`，应标为 `focus`；`carbon dioxide` 这类稳定具体概念词通常仍为 `passive`。
- 不要按词性直接分级。名词、动词、形容词、副词都可能是 `focus` 或 `passive`；最终只看它是否提升真实听说读写流畅度，以及是否值得主动输出。
- 核心常用词优先：如果一个词虽然不高级，但高频、多义、搭配丰富、容易误用，或能构成常见短语/表达，应标为 `focus`，因为它对真实流畅度的贡献高于许多低频难词。
- `passive`：识别掌握词。读到/听到时有价值，但不值得强求主动输出；偏文学描写、具体物件/工具/形状/材料、低频专业词、派生/变形词、领域词但不是用户长期表达核心的词。
- `ignore`：不纳入复习负担。对听说读写流畅度几乎没有实际增益；专名、乱码/截断/误导出片段、一次性虚构术语、极冷门术语、低价值缩写、明显不值得做词汇卡的内容。

拿不准时默认 `passive`，不要默认 `focus`。只有明确无助于真实语言能力或明显是噪声时才用 `ignore`。

`example`

- 优先使用 `source_context`，因为它来自真实阅读场景，记忆钩子更强。
- 如果 `source_context` 完整、自然、不太长，直接清理 HTML 后用作 `example`。
- 如果 `source_context` 太长、噪音多、只截了半句或语法不完整，就改写成更短的句子，但保留原来的真实语境。
- 如果没有 `source_context`，再造一个简洁自然的例句。
- 例句必须是完整英文句子，不能空。

`collocations`

- 至少 2 条常见搭配，通常 2-4 条。
- 选择真实、常见、有助于记忆和使用的搭配；不要空数组。

`root`

`root` 只能是以下两种之一：

1. `-`（不可合理拆解，或拆解不具学习价值）
2. 形如：`形式（中文义）+ 形式（中文义）+ ...`

约束：

- 必须使用全角中文括号 `（ ）`，不要用英文括号 `()`
- 每个分段都必须带中文义，不允许只写英文解释
- 不要写词源故事，不要写语法说明句
- 不要写 `past participle / suffix / prefix / form with -ed` 这类英文说明句
- 不要整批都写 `-`；只有确实不适合拆解的词才写 `-`

正例：

- `de-（离开）+ part（分开）`
- `trans-（跨越）+ port（运送）`
- `inter-（相互）+ connect（连接）`
- `-`

反例（禁止）：

- `Past-participle form with -ed.`
- `prefix de- + part`
- `de- (away) + part (part)`

## 输出前自检（必须）

在输出该批 JSON 前，逐词检查：

- `word` 是否像真实单词/短语；单字母误选（如 `p`）必须剔除或交回父 agent 复核
- `pronunciation` 是否完整且非空
- `part_of_speech` 是否存在且非空
- `meaning` 是否为非空数组，每一条是否带词性缩写，且中文是否简洁自然
- `english_definition` 是否非空
- `root` 是否满足上面的两种合法格式之一，且没有整批偷懒写 `-`
- `example` 是否遵守来源句优先原则
- `collocations` 是否至少 2 条常见搭配
- `audio_html` 可以在导入前为空，但最终 Anki 的 `发音` 字段必须由导入脚本生成 `[sound:...]`
- `learning_priority` 是否存在，且只使用 `focus` / `passive` / `ignore`
- 若不合法，立即改写后再输出
