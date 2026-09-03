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

## 欧路原词清理

欧路导出流程的真实导入命令追加 `--cleanup-eudic`。整批可导入记录写入后，导入器回读笔记字段、本次遇见 ID、唯一卡片及所在 deck，并读取 Anki 中的 MP3 做格式校验。任一导入或核验失败，本批一个词也不删除；`--dry-run` 和 `--ping` 不生成删除清单，也不调用删除接口。

空导出或空导入数组表示无待处理词，正常结束，不调用 Anki 或欧路写接口。MP3 校验要求存在完整 MPEG Layer III 帧，拒绝仅有 ID3 元数据或被截断的文件；不依赖外部解码器。

- 成功保存或已完整存在的 `learn / defer / skip` 均可清理；`reject` 保留。同一删除目标中含有 `reject` 时也保留该目标。
- 删除目标只取导出器提供的 `eudic_source.language/category_id/word`，保留原始拼写，不从规范词形或来源词块推断。手工词表和缺少来源信息的旧文件不删词；旧文件需要重新导出才能自动清理。
- 按语言、生词本分组，每批至多 100 个词。使用相同参数依次调用两次 DELETE：第一次移出来源生词本，第二次从「全部生词」删除；两次都只接受 HTTP `204`。这两个请求是有顺序的删除阶段，不是失败重试。
- 第二次删除后查询首项、中间项和末项，批次不足 3 个词时全部查询。抽样词均返回 HTTP `404` 后才把整批标记为已清理；任一抽样词仍存在、响应无效或请求状态不确定时保留整批。50 个同语言、同生词本的词正常需要 2 次 DELETE 和 3 次抽样查询。
- 所有欧路请求共享单实例锁和请求节流。删除失败或响应不确定时立即停止，不在当前运行中自动重发。
- 以本次导出内容为准，不在首次删除前重新查询词条时间或语境。云同步不参与删除判定；默认仍在本地导入与清理步骤后触发同步，也可使用 `--no-sync`。

本地导入已成功、欧路清理失败时，命令返回 `2` 并分别报告两者状态，不回滚 Anki。成功同步也不能掩盖清理失败。未完成目标原子写入 `~/Documents/eudic-to-anki-temp/.eudic-pending/`；设置 `EUDIC_TO_ANKI_TEMP_DIR` 时，导入器与临时文件清理脚本都使用该目录下的 `.eudic-pending/`。文件不保存 token、来源快照或已完成删除历史。成功项及时移除，全部完成后删除清单文件。

下次欧路流程导出前执行：

```bash
python3 scripts/ankiconnect_import.py --resume-eudic-cleanup
```

续办只处理此前未完成的批次：先核验原 Anki 笔记、本次遇见、单卡与音频，再抽样查询批次状态。抽样词仍在来源生词本时执行两个删除阶段；已移出来源生词本但仍在「全部生词」时只执行第二阶段；均已不存在时视为整批已清理。抽样词状态不一致时，从其中最早的删除阶段继续，使整批到达相同状态；读取失败或核验不通过时保留清单并停止新一轮导出。不比较时间或语境变化，不重新导入、重置卡片或同步。使用非默认 Anki 地址时，续办需传入原 `--anki-url`。

普通临时文件清理会保留 `.eudic-pending/`，不得手工清空它来绕过失败。若持久化清单本身失败，则尚未发起删除；修复存储问题后重新运行原导入命令。

## 迁移

检测到旧 `Chunk Anchor` / `Chunk Recall` 双模板、错误模板名或已知遗留字段时必须停止。诊断会报告现有 note 数量。先完整备份 Anki，删除旧 `TRVS-Lab` notes 和 note type，再重新导入。不得在原模型上直接删除召回模板或自动删除字段。
