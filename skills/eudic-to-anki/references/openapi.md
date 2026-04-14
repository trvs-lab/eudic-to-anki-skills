# Eudic OpenAPI Token

## 获取 token 步骤

1. 打开 [https://my.eudic.net/OpenAPI/Authorization](https://my.eudic.net/OpenAPI/Authorization)
2. 登录并复制 token
3. 将下面命令中的「your-token-here」换成你的 token，并复制命令在终端执行：

```bash
echo 'export EUDIC_TOKEN="your-token-here"' >> ~/.bashrc
echo 'export EUDIC_TOKEN="your-token-here"' >> ~/.zshrc
source ~/.bashrc
source ~/.zshrc
```

如果 agent 子进程拿不到 token，可通过：

```bash
python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py --list-categories
```
