# Export Module

负责欧路云端导出，不处理卡片生成或 Anki 导入。

## 输入

- 日期范围（支持由 workflow 先解析“昨天”等相对时间）
- 分类参数（`--all-categories` / `--category-id` / `--category-name`）

## 输出

- `~/Documents/eudic-to-anki-temp/*_export.csv`（推荐）

## 执行约束

- 将文档中的 `~/Documents/eudic-to-anki-temp/...` 先展开成真实绝对路径，例如 `/Users/alice/Documents/eudic-to-anki-temp/...`。
- 规则敏感命令必须直连执行；不要再包 `/bin/zsh -lc ...`、`zsh -lc ...`、`bash -lc ...`。
- 不要把 `mkdir`、`cd`、`export` 等准备动作和导出命令用 `&&`、`||`、`;`、管道或子 shell 串在一起；拆成两条命令执行。
- 若 temp dir 不存在，先单独执行 `mkdir -p /Users/alice/Documents/eudic-to-anki-temp`。

## 命令

- 列分类：`python3 scripts/eudic_export.py --list-categories`
- 按日期导出：`python3 scripts/eudic_export.py --all-categories --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> --format csv --output <ABS_TEMP_DIR>/_day_<YYYY-MM-DD>_export.csv`
- 当 shell 未加载 token：`python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py ...`
- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`

## 参考

- `references/openapi.md`
