# Export Module

负责欧路云端导出，不处理卡片生成或 Anki 导入。

## 输入

- 日期范围（支持由 workflow 先解析“昨天”等相对时间）
- 分类参数（`--all-categories` / `--category-id` / `--category-name`）

## 输出

- `import_scratch/*_export.csv`（推荐）

## 命令

- 列分类：`python3 scripts/eudic_export.py --list-categories`
- 按日期导出：`python3 scripts/eudic_export.py --all-categories --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> --format csv --output import_scratch/_day_<YYYY-MM-DD>_export.csv`
- 当 shell 未加载 token：`python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py ...`

## 参考

- `references/openapi.md`