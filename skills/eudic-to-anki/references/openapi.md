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
5. 如果你的终端输出的是 `/bin/zsh` 则复制下面的命令到终端，并把命令中的「your-token-here」换成你的 token 后按回车执行：
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
