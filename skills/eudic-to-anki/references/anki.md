# Anki + AnkiConnect

安装并启动 Anki Desktop，再安装 AnkiConnect 插件 `2055492159`。

- 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 新建模型：`python3 scripts/sync_trvs_lab_model.py --create-if-missing`
- 预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`

`TRVS-Lab` 只有一个 `Context Anchor` 模板。正面只显示单词和卡片例句，点击单词播放 `发音`；背面按重要性顺序直接显示语境释义、音标、英英、可选来源词块、可选词族构词、历史语境、遇见次数和最近遇见，不显示分类。

受管 deck 为 `words::learn`、`words::defer`、`words::skip`。Anki 中当前受管 deck 是下次导入的人工决定来源。新的独立遇见会更新同一 note 并重置单卡；相同遇见 ID 幂等。

检测到旧 `Chunk Anchor` / `Chunk Recall` 模型时，脚本会停止。先备份，再删除旧 `TRVS-Lab` notes 和 note type，最后重新导入。直接删除旧召回模板可能破坏调度数据，因此不自动迁移。
