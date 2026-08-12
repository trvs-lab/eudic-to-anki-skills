# eudic-to-anki

[English](README.md) | **中文**

面向 Agent 的开源 [Skill](https://agentskills.io/)：从欧路词典导出生词及真实阅读语境，生成单卡 Context Anchor 笔记和发音，再通过 AnkiConnect 导入 Anki。

```text
欧路词典 → Agent 生成卡片 → 内容校验与 Edge-TTS 发音 → Anki
```

<p align="center">
  <img src="docs/images/context-anchor-preview.png" alt="TRVS-Lab Context Anchor 卡片效果图" width="820">
</p>

## 核心功能

- **以语境为核心的卡片**：正面只显示单词和来源例句、改写例句或生成例句；点击单词播放发音。
- **按理解顺序排列的背面**：依次显示语境释义、音标、英英释义、可选来源词块、有效的构词线索和历史语境，不折叠内容，也不显示分类标记。
- **受管学习分组**：
  - `learn`：适合每天复习的高迁移价值词汇
  - `defer`：有用但优先级较低；出现新的独立遇见记录后自动转入 `learn`
  - `skip`：完整有效但学习收益很低；保留在 Anki 中，由人工移动或删除
  - `reject`：误截片段、乱码等无效内容，不导入 Anki
- **每个词只保留一条笔记**：相同遇见记录重复导入时保持不变；新的独立遇见会更新笔记，并将单张卡片重置为新卡。
- **导入保护**：Edge-TTS 失败后只重试一次，不回退到系统 TTS；导入前严格校验 Anki 模板；连续日期范围只执行一次受保护的导出。

## 环境要求

- 支持 Agent Skills 的 Agent 运行环境
- 用于安装的 Node.js 和 `npx`
- Python 3 与 `edge-tts` Python 包
- 欧路词典账号与 OpenAPI Token
- Anki Desktop 与 AnkiConnect 插件 `2055492159`

导入时需要保持 Anki Desktop 处于打开状态。

## 安装

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

Codex 用户还需要让 Agent 读取 [`skills/eudic-to-anki/RULES_README.md`](skills/eudic-to-anki/RULES_README.md)，生成本机 `~/.codex/rules/eudic-to-anki.rules` 文件。

## 快速开始

1. 配置 `EUDIC_TOKEN`，安装 AnkiConnect。
2. 打开 Anki Desktop。
3. 让 Agent 检查环境并导入指定范围的生词。

自然语言示例：

```text
把昨天的欧路词典生词导入 Anki。
```

```text
把过去一周的欧路词典生词导入 Anki。
```

```text
把 2026 年 8 月 1 日的欧路词典生词导入 Anki。
```

「过去一周」等连续日期范围只执行一次导出，不会拆成多个单日导出任务。

## 项目文档

- [欧路词典 OpenAPI Token 与导出限制](skills/eudic-to-anki/references/openapi.md)
- [Anki、AnkiConnect 与 TRVS-Lab 模板配置](skills/eudic-to-anki/references/anki.md)
- [Agent 完整执行流程](skills/eudic-to-anki/SKILL.md)
- [Codex 本机 rules](skills/eudic-to-anki/RULES_README.md)

Skill 的模板、模块、参考资料、脚本和工作流位于 [`skills/eudic-to-anki/`](skills/eudic-to-anki/) 目录。

## 官方教程

- [安装与首次配置](https://trvs.dev/blog/20260419-eudic-to-anki-skill/)
- [新版卡片设计与复习方式](https://trvs.dev/blog/20260812-eudic-anki-skill-redesign/)

## License

MIT，见 [LICENSE](LICENSE)。
