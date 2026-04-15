# Anki + AnkiConnect

- 在 [Anki 官网](https://apps.ankiweb.net/#downloads)下载并安装并启动 Anki 客户端。
- 在客户端登录 Anki 账号，如果没有账号则在 [Anki Web](https://ankiweb.net/account/signup) 注册一个
- 安装 AnkiConnect 插件: 在 Anki 客户端依次点击「工具」->「插件」->「获取插件」，输入插件代`2055492159` 安装。
- 连通性检查：

```bash
python3 scripts/ankiconnect_import.py --ping
```

- 导入示例（成功后默认会 `sync`；若不想同步加 `--no-sync`）：

```bash
python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck
```

- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`
