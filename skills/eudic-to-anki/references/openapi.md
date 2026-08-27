# Eudic OpenAPI Token

## 获取 token 步骤

1. 打开 [https://my.eudic.net/OpenAPI/Authorization](https://my.eudic.net/OpenAPI/Authorization)
2. 登录并复制 token
   <img width="3268" height="1952" alt="CleanShot 2026-04-14 at 14 33 39@2x" src="https://github.com/user-attachments/assets/67efb633-a856-4008-aa6d-0bbe9e35e83a" />
3. 打开你的终端，复制下面这条命令并按回车执行，看看输出的是什么
   ```
   echo $SHELL
   ```
4. 如果你的终端输出的是 `/bin/zsh` 则复制下面的命令到终端，并把命令中的「your-token-here」换成你的 token 后按回车执行：
   ```zsh
   echo 'export EUDIC_TOKEN="your-token-here"' >> ~/.zshrc
   source ~/.zshrc
   ```
5. 如果你的终端输出的是 `/bin/bash` 则复制下面的命令到终端，并把命令中的「your-token-here」换成你的 token 后按回车执行：
   ```bash
   echo 'export EUDIC_TOKEN="your-token-here"' >> ~/.bashrc
   source ~/.bashrc
   ```

如果 agent 子进程拿不到 token，可直接调用包装脚本（不要再包 `zsh -lc`，也不要和其它准备动作用 `&&` 串接）：

```bash
python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py --list-categories
```

对于受 rules 约束的导出命令：

- 先把 `~/Documents/...` 展开成绝对路径，例如 `/Users/alice/Documents/eudic-to-anki-temp/...`
- 若需要创建目录，先单独执行 `mkdir -p /Users/alice/Documents/eudic-to-anki-temp`

## 日期范围与访问限制

- 「过去一周」「最近 N 天」或明确的连续日期范围必须解析为一个闭区间，并通过一条同时包含 `--start-date` 与 `--end-date` 的命令导出。不得按天拆分或并行执行。
- 日期过滤发生在本地。一次导出仍会查询一次分类，并逐分类分页读取生词，因此一条命令可能对应多次 HTTP 请求。
- 导出器使用本机单实例锁，并将所有请求限制为最多 25 次／分钟。已有导出运行、限频重试失败或认证／网络／解析失败时，应停止完整制卡流程。
- 限频响应只有在提供合法 `Retry-After` 时才重试当前请求一次；不要人工并发重试，也不要改成多条单日命令。

## 导入后删除

[官方生词本 API 文档 §1.7](https://my.eudic.net/OpenAPI/doc_api_study) 定义 `DELETE /api/open/v1/studylist/words`，JSON body 为 `language`、`category_id` 和原始 `words` 数组；成功返回 `204`。清理由导入器的 `--cleanup-eudic` 调用，不能直接拿导出文件或命令退出码代替整批本地核验。失败和续办策略见 `modules/import/README.md`。
