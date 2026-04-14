# eudic-to-anki

[English](README.md) | **中文**

面向 Agent 的开源 Skill：将欧路词典的生词导出做成背单词卡片自动导入 Anki：

- 通过欧路词典的 OpenAPI 导出单词
- 由 Agent 生成 Anki 背单词卡片
- 用 Edge-TTS 生成单词发音
- 经 AnkiConnect 导入 Anki

本仓库遵循 [Agent Skills](https://agentskills.io/) 规范，可与 Vercel skills CLI 配合使用。

## 安装

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

## 快速开始

1. 用 `npx skills add ...` 安装本 skill。
2. 打开 `skills/eudic-to-anki/SKILL.md`。
3. 在 Agent 中以 skill 目录（`skills/eudic-to-anki/`）为工作目录执行文档中的命令。
4. 可先运行：
   - `bash scripts/check_env.sh`

## 能做什么

- **统一流程**：导出 → 生成卡片 → 校验 → 导入 → 清理
- **质量门槛**：自动校验生成的卡片是否符合规范
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
  import_scratch/     # 中间产物（目录内容通常 gitignore）
```

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
