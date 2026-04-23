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

- 导入前预演：

```bash
python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run
```

- 导入示例（成功后默认会 `sync`；若不想同步加 `--no-sync`）：

```bash
python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --require-audio --verify-required-fields --audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}"'
```

- `--require-audio` 会要求最终 `发音` 字段为 `[sound:...]`；`--verify-required-fields` 会导入后回读 Anki，检查 `音标/释义/英英/词根/例句/常用搭配/发音`。

- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`
