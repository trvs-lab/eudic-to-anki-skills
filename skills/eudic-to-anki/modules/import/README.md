# Import Module

通过 AnkiConnect 导入单卡 Context Anchor 笔记。

## 受管分组

- `words::learn`
- `words::defer`
- `words::skip`

`reject` 不进入 Anki。已有卡片当前所在的受管 deck 优先于本次分类：`learn` 保持不变，`skip` 保持不变，`defer` 在出现新的独立遇见记录时转入 `learn`。

同一规范词形只保留一条 note。新的独立遇见会更新字段、累加次数、保存最近 2–3 条真实历史语境，并对单张卡执行 `forgetCards`。相同 encounter ID 的重复导入不更新、不移动、不重置；若 Anki 中的对应音频缺失或无效，只修复音频，不重置卡片。

## 命令

- 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dry-run`
- 只读模型检查：`python3 scripts/sync_trvs_lab_model.py --check`
- 完整模型同步：`python3 scripts/sync_trvs_lab_model.py`
- 真实导入：见 `SKILL.md` 中带 Edge-TTS 的完整命令。

预演先以完整 SHA-256 严格比较 Front、Back、CSS，输出 `create`、`update`、`none` 或 `blocked`、组件状态、短哈希、缺失字段和额外字段，再输出原始输入条数、按规范词形聚合后的词条数、四种分类数量、新建、更新、`defer → learn`、幂等和重置。预演只读；`blocked` 返回非零。

真实导入先取得共享非阻塞锁，自动创建缺失模型或安全覆盖兼容模型，并重新读取验证。只有模型严格一致后才准备 Edge-TTS、创建 deck、上传媒体和写入 note。模型更新失败或二次验证失败时立即停止，不生成音频、不写卡片、不触发同步，也不自动回滚已经完成的安全模型修改。真实导入全部成功后默认同步；仅在明确需要时使用 `--no-sync`。

## 迁移

检测到旧 `Chunk Anchor` / `Chunk Recall` 双模板、错误模板名或已知遗留字段时必须停止。诊断会报告现有 note 数量。先完整备份 Anki，删除旧 `TRVS-Lab` notes 和 note type，再重新导入。不得在原模型上直接删除召回模板或自动删除字段。
