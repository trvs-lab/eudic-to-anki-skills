# Anki + AnkiConnect

安装并启动 Anki Desktop，再安装 AnkiConnect 插件 `2055492159`。

- 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 只读检查模型：`python3 scripts/sync_trvs_lab_model.py --check`
- 完整同步模型：`python3 scripts/sync_trvs_lab_model.py`
- 完整同步模型并触发云同步：`python3 scripts/sync_trvs_lab_model.py --sync`
- 预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dry-run`

`TRVS-Lab` 只有一个 `Context Anchor` 模板。正面只显示单词和卡片例句，点击单词播放 `发音`；单词按钮显式覆盖不同 Anki 平台的原生字体、阴影、边框、背景和触控高亮，只在键盘导航的 `:focus-visible` 状态保留焦点提示。例句文本块整体居中且内部左对齐。背面按重要性顺序直接显示语境释义、音标、英英、可选来源词块及释义、可选构词线索、由近到远的历史语境、遇见次数和本地日期，不显示分类。构词线索直接显示「拆解：」和「联想：」两行，不显示独立的「词族构词」标题。

AnkiMobile 底部的信息栏、设置按钮和复习按钮属于卡片 WebView 外的原生界面，模板 CSS 不能可靠覆盖。保留其与卡片纸面之间的轻微层级差异，不为追随某个 AnkiMobile 版本的原生颜色而覆盖移动端卡片背景。

导入器与独立模型同步命令共用严格模型合同和本机非阻塞锁。Front、Back、CSS 只规范化 CRLF／LF 和文件末尾换行，再按完整 SHA-256 比较；其他空格、HTML、JavaScript 与 CSS 差异均会触发更新。模型不存在时真实执行会自动创建；兼容模型会补充缺失字段并只更新变化组件，然后重新读取验证。未知额外字段保留并警告。`--check` 与导入预演只报告 `create`、`update`、`none` 或 `blocked`，不修改 Anki。

独立模型同步默认执行完整本地同步，不触发云同步。仅显式 `--sync` 才会在严格验证成功后触发云同步；不提供模板或 CSS 局部同步模式。真实导入不允许使用 `--no-ensure-model` 绕过模型合同。

受管 deck 为 `words::learn`、`words::defer`、`words::skip`。Anki 中当前受管 deck 是下次导入的人工决定来源。新的独立遇见会更新同一 note 并重置单卡；相同遇见 ID 幂等。

检测到旧 `Chunk Anchor` / `Chunk Recall` 模型、错误模板名或已知遗留字段时，脚本会停止并报告现有 note 数量。先完整备份 Anki，再删除旧 `TRVS-Lab` notes 和 note type，最后重新导入。直接删除旧召回模板可能破坏调度数据，因此不自动迁移或回滚。
