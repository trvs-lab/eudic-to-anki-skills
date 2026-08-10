# Import Module

通过 AnkiConnect 导入单卡 Context Anchor 笔记。

## 受管分组

- `words::learn`
- `words::defer`
- `words::skip`

`reject` 不进入 Anki。已有卡片当前所在的受管 deck 优先于本次分类：`learn` 保持不变，`skip` 保持不变，`defer` 在出现新的独立遇见记录时转入 `learn`。

同一规范词形只保留一条 note。新的独立遇见会更新字段、累加次数、保存最近 2–3 条真实历史语境，并对单张卡执行 `forgetCards`。相同 encounter ID 的重复导入不更新、不移动、不重置。

## 命令

- 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`
- 真实导入：见 `SKILL.md` 中带 Edge-TTS 的完整命令。

预演输出分类、新建、更新、`defer → learn`、幂等和重置数量。真实导入成功后默认同步；仅在明确需要时使用 `--no-sync`。

## 迁移

检测到旧 `Chunk Anchor` / `Chunk Recall` 双模板时必须停止。先备份 Anki，删除旧 `TRVS-Lab` notes 和 note type，再重新导入。不得在原模型上直接删除召回模板。
