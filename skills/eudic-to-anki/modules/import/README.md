# Import Module

负责 AnkiConnect 导入、deck/model 选择、可选 upsert 刷新策略。

## 前置

- Anki Desktop 已启动
- AnkiConnect 可访问（`http://127.0.0.1:8765`）

## 命令

- 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 基础导入：`python3 scripts/ankiconnect_import.py --input ~/Documents/eudic-to-anki-temp/import.json --deck words --create-deck`
- 导入成功后默认会调用 AnkiConnect `sync`（与手动点同步一致）；若需跳过，加 `--no-sync`。
- 刷新已存在卡片：在导入命令加 `--dia-upsert`

## 输出

- 导入/更新/跳过统计
- deck / model 使用情况

## 参考

- `references/anki.md`
