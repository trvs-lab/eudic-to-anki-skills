# Eudic OpenAPI Token

1. 打开 [https://my.eudic.net/OpenAPI/Authorization](https://my.eudic.net/OpenAPI/Authorization)
2. 登录并复制 token
3. 在本地 shell 配置环境变量：

```bash
export EUDIC_TOKEN="NIS your-token-here"
```

如果 agent 子进程拿不到 token，可通过：

```bash
python3 scripts/run_with_login_zsh.py python3 scripts/eudic_export.py --list-categories
```

