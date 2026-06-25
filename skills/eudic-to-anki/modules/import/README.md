# Import Module

负责 AnkiConnect 导入、deck/model 选择、可选 upsert 刷新策略。

## 前置

- Anki Desktop 已启动
- AnkiConnect 可访问（`http://127.0.0.1:8765`）

## 执行约束

- 将文档中的 `~/Documents/eudic-to-anki-temp/...` 先展开成真实绝对路径，例如 `/Users/alice/Documents/eudic-to-anki-temp/...`。
- 规则敏感命令必须直连执行；不要再包 `/bin/zsh -lc ...`、`zsh -lc ...`、`bash -lc ...`。
- 不要把 `mkdir`、`cd`、`export` 等准备动作和导入命令用 `&&`、`||`、`;`、管道或子 shell 串在一起；拆成两条命令执行。

## 命令

- 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`
- 基础导入：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck`
- 导入成功后默认会调用 AnkiConnect `sync`（与手动点同步一致）；若需跳过，加 `--no-sync`。
- 刷新已存在卡片：在导入命令加 `--dia-upsert`
- `--deck words` 是 base deck。`TRVS-Lab` 会按卡片类型分流：
  - `words::chunk-anchor::focus`
  - `words::chunk-anchor::passive`
  - `words::chunk-anchor::ignore`
  - `words::chunk-recall::focus`
- 这是 fresh-start breaking upgrade；旧 `TRVS-Lab` note 不保证显示正确。升级前清空旧 note 或相关 deck。
- `ignore` 只生成 `words::chunk-anchor::ignore` 锚点卡，不会默认挂起、跳过或排除；复习方式交给用户在 Anki 里决定。
- Anchor 卡和 recall 卡是分开的模板与 deck，用于学习短语块，而不是孤立单词。
- 不生成短语块专用音频；两类卡片都使用主单词音频。Recall 卡背面显示词级中文 `meaning`，不重复短语块锚点。
- `TRVS-Lab` 导入会确保模型包含 `学习标记` 字段，并把 `learning_priority` 写入纯符号字段和稳定 tag：`priority::focus/passive/ignore`；卡片仅在背面以轻量提示显示该符号，不会再添加 `english`、`vocab`、`eudic`。
- 音频为必填：真实导入必须带 `--require-audio`，并使用 `--audio-provider command` 或 `--audio-provider existing` 生成/保留 `[sound:...]`。
- 导入后字段校验：真实导入加 `--verify-required-fields`，会回读 Anki note 并检查 `音标/释义/英英/词根/例句/常用搭配/发音`。
- `--dia-upsert` 默认会在 base deck 和短语块卡片 deck 里按 `单词` 查旧 note，更新字段/标签，并按生成卡片类型路由到 chunk anchor / chunk recall deck；更新时默认重置为新卡。只有用户明确要求「不要重置学习进度」时，才加 `--preserve-progress-on-update` 保留学习进度。
- 执行前先 dry-run，执行后抽查 Anki 实际字段。
- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`

## 输出

- 导入/更新/跳过统计
- deck / model 使用情况

## 参考

- `references/anki.md`
