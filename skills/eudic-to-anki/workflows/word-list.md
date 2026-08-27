# Workflow: User Word List

手工词表不运行 `--cleanup-eudic` 或 `--resume-eudic-cleanup`，不构造 `eudic_source`，不删除欧路原词。

1. 为每个完整单词或短语建立 coach note，并附带可区分遇见的时间；需要覆盖自动身份时可额外提供显式 `encounter_id`。
2. 若没有真实来源句，生成包含目标词或有效词形的 8–16 词实用例句，并设置 `sentence_origin: "generated"`、`source_context: ""`。
3. 将低价值但完整的条目标为 `skip`；只有无效片段或垃圾才标为 `reject`。
4. 运行 `python3 scripts/validate_trvs_coach_json.py <ABS_TEMP_DIR>/word_list_import.json`。
5. 运行 dry-run 并检查分类、更新和幂等统计。
6. 使用 `SKILL.md` 的 Edge-TTS 命令导入；不得回退到系统 TTS。
7. 抽查正面仅有单词和例句、点击单词可发音、背面信息无折叠且不显示分类。
