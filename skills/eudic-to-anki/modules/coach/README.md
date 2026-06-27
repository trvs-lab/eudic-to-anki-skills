# Coach Module

负责 TRVS-Lab 的 8 字段内容质量、词性保留、批处理合并、编码安全与校验门禁。

## 关键规则

- 由 agent 生成 `pronunciation/part_of_speech/meaning/english_definition/root/example/collocations` 和短语块字段。
- 每个 note 都必须带 `part_of_speech`，格式使用简短词性缩写，如 `n.`、`vt.`、`vi.`、`adj.`、`adv.`。
- `meaning` 数组中的每一条中文释义都必须以词性缩写开头；不要输出裸中文义。
- 每个 note 都必须带 `learning_priority`，只能是 `focus`、`passive`、`ignore`。分级的第一目标是服务用户听说读写的真实流畅度，并兼顾 20000 词汇量和 IELTS 8+：需要主动说/写或显著提升理解的词用 `focus`，只需读/听识别的词用 `passive`，对语言能力几乎无增益或明显噪声的词用 `ignore`；拿不准时默认 `passive`。
- 多义词不能只按最具体的物件义判断；若常见义项中包含高迁移的抽象义、动词义、评论/修辞义或高价值搭配，并能提升表达精度或阅读理解，则标 `focus`（如 `foil`）；稳定具体概念词通常标 `passive`（如 `carbon dioxide`）。
- 不要按词性直接分级。名词、动词、形容词、副词都可能是 `focus` 或 `passive`；最终只看它是否提升真实听说读写流畅度，以及是否值得主动输出。
- 核心常用词优先：如果一个词虽然不高级，但高频、多义、搭配丰富、容易误用，或能构成常见短语/表达，应标为 `focus`，因为它对真实流畅度的贡献高于许多低频难词。
- 短语块是新模型的主记忆锚点。每个 note 都必须有 `target_chunk`、`target_chunk_meaning` 和 `target_chunk_sentence`。
- `target_chunk_sentence` 是锚点卡正面的学习句，必须逐字包含 `target_chunk`。
- `focus` note 必须有由 `target_chunk_sentence` 挖掉 `target_chunk` 得到的 `target_chunk_cloze`，用于生成半遮挡召回卡。
- `passive` / `ignore` note 必须让 `target_chunk_cloze` 为空，避免生成召回卡。
- `pronunciation` 必须是完整美式 IPA，不能空；不要依赖欧路 `phon` 的批量拷贝。
- `meaning` 必须由 agent 重新生成，写成简洁、通俗、像词典标签的中文释义；不要直接复制欧路 `exp`，也不要把解释段落塞进中文释义。
- `english_definition` 必须生成，风格接近 vocabulary.com：简洁、通俗、解释型，用日常英文给学习者讲清楚词义；不要只写同义词、不要混中文、不要写长篇百科定义。
- `english_definition` 才放解释性英文定义；中文释义优先短而准确，例如 `carbon dioxide` 写 `n. 二氧化碳`。
- `root` 要尽量生成词根/词缀拆解，格式为 `形式（中文义）+ ...`；只有确实拆不动或没学习价值时才写 `-`（或 `无`）。不要把完整单词本身当作唯一分段，例如 `crimson（深红）` 应改成 `-`。
- `collocations` 至少 2 条常见搭配，不能空。
- `example` 只表示来源例句：有 partial JSON `source_context` 时保留或轻微完善；没有来源句时留空，不要伪造来源。学习用例句写入 `target_chunk_sentence`。
- 最终 Anki note 必须有音频；导入命令要生成或保留 `发音` 字段里的 `[sound:...]`。
- 疑似误选词或截断词（如单字母 `p`）必须停下来复核，不要直接导入。
- 大批量走分批（25-40 词）+ 每批校验 + merge。
- 出现子 agent 信道噪声时，可让子 agent 输出单行 base64，再用解码脚本恢复。
- 导入前必须通过 `validate_trvs_coach_json.py`。
- 真实导入前先跑 `ankiconnect_import.py --dry-run --verify-required-fields`；真实导入使用 `--require-audio --verify-required-fields`；导入后抽查 Anki 实际字段，确认 `音标/释义/英英/词根/短语块例句/常用搭配/发音` 没被清空或写错；`例句` 只在有真实来源时出现。

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
