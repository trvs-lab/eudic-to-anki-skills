# Anki + AnkiConnect

- 安装并启动 Anki Desktop。
- 安装 AnkiConnect（代码 `2055492159`）。
- 连通性检查：

```bash
python3 scripts/ankiconnect_import.py --ping
```

- 导入示例（成功后默认会 `sync`；若不想同步加 `--no-sync`）：

```bash
python3 scripts/ankiconnect_import.py --input import_scratch/import.json --deck words --create-deck
```
