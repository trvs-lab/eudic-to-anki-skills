# Export Module

负责欧路云端导出，不处理卡片生成或 Anki 导入。

## 输入

- 日期范围（支持由 workflow 先解析“昨天”等相对时间）
- 分类参数（`--all-categories` / `--category-id` / `--category-name`）

## 输出

- `<ABS_TEMP_DIR>/*_export.csv`（推荐；例如 `/Users/alice/Documents/eudic-to-anki-temp/*_export.csv`）
- 每行保留 `category_id`、`category_name`、`add_time_utc`、`add_time_local` 和 `context_line`。同一单词的多次遇见不得在导出或占位阶段去重。

## 执行约束

- 单日请求使用 `workflows/yesterday.md`；「过去一周」「最近 N 天」或明确起止日期使用 `workflows/date-range.md`；手工词表不调用欧路导出。
- 一个连续日期范围只允许一次 `eudic_export.py` 调用。不得按天拆分，也不得并行启动多个导出进程。
- `--start-date` 与 `--end-date` 用于下载后的本地过滤，不是服务端日期参数。一次调用会先执行一次分类查询，再为每个选中分类发出一次或多次分页请求；范围天数不是拆分导出的理由。
- 将文档中的 `~/Documents/eudic-to-anki-temp/...` 先展开成真实绝对路径，例如 `/Users/alice/Documents/eudic-to-anki-temp/...`。
- 规则敏感命令必须直连执行；不要再包 `/bin/zsh -lc ...`、`zsh -lc ...`、`bash -lc ...`。
- 不要把 `mkdir`、`cd`、`export` 等准备动作和导出命令用 `&&`、`||`、`;`、管道或子 shell 串在一起；拆成两条命令执行。
- 若 temp dir 不存在，先单独执行 `mkdir -p /Users/alice/Documents/eudic-to-anki-temp`。

## 命令

- 列分类：`python3 scripts/eudic_export.py --list-categories`
- 单日导出：`python3 scripts/eudic_export.py --all-categories --start-date <D> --end-date <D> --format csv --output <ABS_TEMP_DIR>/_day_<D>_export.csv`
- 连续日期范围：`python3 scripts/eudic_export.py --all-categories --start-date <START> --end-date <END> --format csv --output <ABS_TEMP_DIR>/_range_<START>_<END>_export.csv`
- 当 shell 未加载 token：`python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py ...`
- 其中 `<ABS_TEMP_DIR>` 代表展开后的真实绝对目录，例如 `/Users/alice/Documents/eudic-to-anki-temp`

## 运行时保护

- 导出器使用所有项目副本与全局安装共同识别的本机单实例锁。已有导出运行时，新进程会在任何欧路 HTTP 请求前失败，不排队，也不自动改成逐日重试。
- 分类查询、分页请求和唯一一次限频重试共用节流入口：最多 25 次／分钟，相邻请求开始时间至少间隔 2.4 秒。
- `429` 一律视为限频；`403` 只有响应正文明确表示访问频率过高时才视为限频。只有合法的 `Retry-After`（0～120 秒或等价 HTTP 日期）允许对当前请求重试一次。
- 任意并发、限频、认证、网络或解析失败都会停止后续分类与分页；agent 同时停止占位、coach、音频和 Anki 流程。
- CSV／JSON 先写入目标目录的临时文件，成功关闭并同步后再原子替换目标。失败不生成部分文件，也不覆盖已有完整导出。
- 成功与失败都会输出请求统计：分类查询、单词分页、重试和总请求数。统计不包含 token 或认证头。

## 参考

- `references/openapi.md`
