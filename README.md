# eudic-to-anki

**中文** · [English](README.en.md)

**把阅读中遇见的词，带着语境放进 Anki。**

一个面向英语学习者的开源 [Agent Skill](https://agentskills.io/)：从欧路词典导出生词和阅读语境，由 Agent 整理释义、例句与发音，生成一词一卡的 Context Anchor 笔记。

[快速开始](#快速开始) · [卡片设计](#一张卡片保留一次阅读) · [使用说明](#导入与复习规则) · [文档与教程](#文档与教程)

## 一张卡片，保留一次阅读

<p align="center">
  <img src="docs/images/context-anchor-preview.png" width="820" alt="innovator 的 Anki 卡片：保留阅读例句，背面展示语境释义、音标、英英释义、词块和构词线索。">
</p>

- **先回到语境**：正面只显示单词与例句，点击单词播放发音。优先使用真实来源句；来源过长时精简，无来源时生成实用例句。
- **再理解用法**：翻面后直接展示语境释义、音标、英英释义，以及有学习价值的词块和构词线索。
- **把新遇见接在旧记忆上**：同一规范词形只保留一条笔记、一张卡片；新的阅读记录更新到原笔记，并保留最近的真实历史语境。

## 快速开始

### 1. 准备环境

- 支持 Agent Skills 的 Agent 运行环境。
- Node.js 与 `npx`，用于安装 Skill；Python 3 与 `edge-tts` 包，用于运行脚本和生成发音。
- 欧路词典账号与 `EUDIC_TOKEN`，配置方式见 [Token 指南](skills/eudic-to-anki/references/openapi.md)。
- Anki Desktop 与 AnkiConnect 插件 `2055492159`，配置方式见 [Anki 指南](skills/eudic-to-anki/references/anki.md)。

### 2. 安装 Skill

<a id="install"></a>

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

Codex 用户还需让 Agent 按 [本机 rules 指南](skills/eudic-to-anki/RULES_README.md) 生成 `~/.codex/rules/eudic-to-anki.rules`。

### 3. 打开 Anki，发起第一次导入

保持 Anki Desktop 打开，向 Agent 发送：

> 检查 eudic-to-anki 的运行环境，把昨天的欧路词典生词导入 Anki。

也可以指定「过去一周」「2026 年 8 月 1 日至 7 日」，或直接提供手工词表。未指定生词本时，默认查询全部生词本。

> **导入后会清理欧路原词。** 整批笔记、遇见记录、卡片和音频在本地核验通过后，自动清理对应来源原词，无需等待云同步。成功后不保留备份或删除记录。手工词表不触发欧路清理。

## 导入与复习规则

**从阅读到复习，按顺序完成。** 欧路导出 → Agent 整理内容 → 内容与模板校验 → Edge-TTS 发音 → Anki 导入与回读核验 → 欧路原词清理。

**复习优先级由分组管理。** 可导入词条进入 `words` 下的三个牌组；分类不显示在卡片上。

| 分组 | 处理方式 |
| --- | --- |
| `learn` | 适合日常复习的高迁移价值词汇 |
| `defer` | 有用但优先级较低；新的独立遇见会将其转入 `learn` |
| `skip` | 完整有效但学习收益低；保留在 Anki 中，由人工移动或删除 |
| `reject` | 误截片段、乱码等无效内容；不导入 Anki，也不清理对应欧路原词 |

**重复导入与再次遇见的处理不同。** 相同遇见记录重复导入不重置进度；新的独立遇见会更新原笔记，并将单张卡片重置为新卡。已有 `learn`、`skip` 分组保持不变。

**失败时保留可继续处理的状态。** 导入或回读核验失败，本批不删词；本地导入成功但欧路清理失败，下次运行先续办清理。两项结果分别报告。

<details>
<summary>导出、音频与旧模板的处理边界</summary>

- **日期范围**：连续日期范围只执行一次受保护的导出，不按天拆分或并行请求。详见 [导出限制](skills/eudic-to-anki/references/openapi.md#日期范围与访问限制)。
- **发音**：使用 Edge-TTS，失败后以相同参数重试一次；再次失败则停止，不回退到系统 TTS。
- **模板**：导入前严格校验 TRVS-Lab 模板。检测到旧版双卡模型时停止，需先完整备份，再按 [迁移说明](skills/eudic-to-anki/modules/import/README.md#迁移) 处理。

</details>

## 文档与教程

- **首次使用**：[安装与配置教程](https://trvs.dev/blog/20260419-eudic-to-anki-skill/) · [Token 配置](skills/eudic-to-anki/references/openapi.md) · [Anki 配置](skills/eudic-to-anki/references/anki.md)
- **卡片与复习**：[卡片设计与复习方式](https://trvs.dev/blog/20260812-eudic-anki-skill-redesign/) · [分组、更新与清理规则](skills/eudic-to-anki/modules/import/README.md)
- **Agent 执行**：[完整工作流](skills/eudic-to-anki/SKILL.md) · [Codex 本机 rules](skills/eudic-to-anki/RULES_README.md)
- **项目实现**：[Skill 目录](skills/eudic-to-anki/) · [卡片模板](skills/eudic-to-anki/assets/) · [测试](tests/eudic_to_anki/)

## License

[MIT](LICENSE)
