# eudic-to-anki

[English](README.md) | **中文**

面向 Agent 的开源 Skill：将欧路词典的生词导出做成背单词卡片自动导入 Anki：

- 通过欧路词典的 OpenAPI 导出单词
- 由 Agent 生成 Anki 背单词卡片
- 用 Edge-TTS 生成单词发音
- 经 AnkiConnect 导入 Anki

本仓库遵循 [Agent Skills](https://agentskills.io/) 规范，可与 Vercel skills CLI 配合使用。

## 官方教程

完整安装与使用说明请看这篇博客：
[https://trvs.dev/blog/20260420-eudic-to-anki-skill/](https://trvs.dev/blog/20260420-eudic-to-anki-skill/)

## 安装

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

## GitHub Pages

仓库已新增一个 Apple 风格的介绍页，放在 `docs/` 目录：

- 页面入口：`docs/index.html`
- 自动发布工作流：`.github/workflows/deploy-pages.yml`

发布步骤：

1. 将改动推送到 `main`
2. 打开仓库设置里的 **Pages**
3. 将 Source 设为 **GitHub Actions**（如果尚未设置）
4. 等待 **Deploy GitHub Pages** 工作流执行完成

## Codex 安装补充步骤

如果用户是专门为 Codex 客户端安装这个 skill，还需要额外完成下面这一步：

1. 打开 `skills/eudic-to-anki/RULES_README.md`
2. 按其中内嵌的 `RULE_TEMPLATE` 生成 `~/.codex/rules/eudic-to-anki.rules`
3. 在写入前，把所有 `<HOME>` 占位符替换成当前机器上的真实 home 绝对路径
4. 把生成 rules 文件视为 Codex 环境配置的一部分，而不是可选提示

这一步只针对 Codex。其他 agent/runtime 并不需要生成 Codex 的 rules 文件，除非它们刻意复用 Codex 的 execpolicy 模型。

## 快速开始

1. 用 `npx skills add ...` 安装本 skill。
2. 如果你使用的是 Codex，再打开 `skills/eudic-to-anki/RULES_README.md`，生成 `~/.codex/rules/eudic-to-anki.rules`。
3. 打开 `skills/eudic-to-anki/SKILL.md`。
4. 在 Agent 中以 skill 目录（`skills/eudic-to-anki/`）为工作目录执行文档中的命令。
5. 可先运行：
   - `bash scripts/check_env.sh`

## 能做什么

- **统一流程**：导出 → 生成卡片 → 校验 → 导入 → 清理
- **质量门槛**：自动校验完整音标、简洁重写的中文释义、通俗解释型英英释义、来源句优先例句、词根词缀拆解、音频和常用搭配
- **导入后同步**：在成功导入 Anki 后自动同步到云端
- **模板内置**：附带 TRVS-Lab 笔记类型等资源

## 用户要做的配置

- 配置欧路词典的 `EUDIC_TOKEN`：参考 [skills/eudic-to-anki/references/openapi.md](skills/eudic-to-anki/references/openapi.md)
- 安装 Anki 桌面版 + AnkiConnect 插件：参考 [skills/eudic-to-anki/references/anki.md](skills/eudic-to-anki/references/anki.md)


## 仓库结构

```
skills/eudic-to-anki/
  SKILL.md            # Agent 说明（主入口）
  README.md           # skill 概览
  scripts/            # 导出、校验、合并、导入、TTS
  references/         # token / Anki / Edge-TTS / coach 提示
  assets/             # TRVS-Lab 笔记类型模板
  workflows/          # 按场景的执行清单（昨天 / 日期区间 / 词表）
```

运行时中间产物默认写在 skill 安装目录之外：

- 专用的 Documents 工件目录；执行时请使用展开后的绝对路径，例如 `<ABS_TEMP_DIR>` / `/Users/alice/Documents/eudic-to-anki-temp/`

## 常用命令

```bash
# 环境检查
bash scripts/check_env.sh

# 欧路分类列表
python3 scripts/eudic_export.py --list-categories

# Anki 连通性
python3 scripts/ankiconnect_import.py --ping
```

## 许可证

MIT。见 [LICENSE](LICENSE)。
