# Anki + AnkiConnect

- 在 [Anki 官网](https://apps.ankiweb.net/#downloads)下载并安装并启动 Anki 客户端。
- 在客户端登录 Anki 账号，如果没有账号则在 [Anki Web](https://ankiweb.net/account/signup) 注册一个
- 安装 AnkiConnect 插件: 在 Anki 客户端依次点击「工具」->「插件」->「获取插件」，输入插件代码`2055492159` 安装。
- 连通性检查：

```bash
python3 scripts/ankiconnect_import.py --ping
```

- 同步内置 `TRVS-Lab` 模板和样式到 Anki：

```bash
python3 scripts/sync_trvs_lab_model.py
```

- 只同步正反面模板，不改样式：

```bash
python3 scripts/sync_trvs_lab_model.py --templates-only
```

- 如果 Anki 里还没有 `TRVS-Lab` 笔记类型，可用内置 spec 创建：

```bash
python3 scripts/sync_trvs_lab_model.py --create-if-missing
```

- `TRVS-Lab` 模型会自动补齐 `学习标记` 和短语块字段并更新模板/CSS；`学习标记` 保留为复习元数据，并仅在背面右上角以轻量纯符号提示显示。

- `--deck words` 是 base deck。`TRVS-Lab` 会按卡片类型分流：
  - `words::chunk-anchor::focus`
  - `words::chunk-anchor::passive`
  - `words::chunk-anchor::ignore`
  - `words::chunk-recall::focus`

- 这是 fresh-start breaking upgrade；旧 `TRVS-Lab` note 不保证显示正确。升级前清空旧 note 或相关 deck。

- `ignore` 只生成 `words::chunk-anchor::ignore` 锚点卡，不会默认挂起、跳过或排除。

- Anchor 卡和 recall 卡是分开的模板与 deck，用于学习短语块，而不是孤立单词。Anchor 正面显示 `目标短语块` 和 `短语块例句`；Anchor 背面先轻量显示 `短语块锚点`，再按需显示来源 `例句`，然后用紧凑词头合并显示 `单词`、`音标` 和词级中文 `meaning`。Recall 正面先显示 `短语块挖空`，再显示 `短语块锚点`。

- 不生成短语块专用音频；两类卡片都使用主单词音频。Recall 卡背面左对齐显示 `目标短语块`，只在 `例句` 非空时显示来源例句，并用同一套紧凑词头显示 `单词`、`音标` 和词级中文 `meaning`；不重复短语块锚点，也不重复完整 `短语块例句`。

- 导入前预演：

```bash
python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run
```

- 导入示例（成功后默认会 `sync`；若不想同步加 `--no-sync`）：

```bash
python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}"'
```

- `--require-audio` 会要求最终 `发音` 字段为 `[sound:...]`；`--verify-required-fields` 会导入后回读 Anki，检查 `音标/释义/英英/词根/常用搭配/短语块例句/发音/学习标记` 等必填字段。`例句` 是来源例句，可为空。

- `--dia-upsert` 会在 base deck 和短语块卡片 deck 里按 `单词` 查找旧 note；更新字段和标签后，按生成卡片类型路由到 chunk anchor / chunk recall deck，避免重复建卡。

- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`
