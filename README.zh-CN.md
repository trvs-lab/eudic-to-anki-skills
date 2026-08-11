# eudic-to-anki

[English](README.md) | **中文**

面向 Agent 的开源 Skill：从欧路词典导出生词及真实阅读语境，生成单卡 Context Anchor 笔记，再通过 AnkiConnect 导入 Anki。

## 特点

- 保留每次欧路遇见的来源分类、时间和原始语境。
- 同一规范词形只保留一条 Anki note 和一张卡。
- 有来源时使用或适量改写来源句；无来源时生成简短实用例句。
- 正面只显示单词和例句，点击单词播放发音；背面信息直接展开，不显示分类标记。
- 使用 `learn`、`defer`、`skip` 三个 Anki deck；无效 `reject` 不导入。
- 新遇见更新并重置单卡，相同遇见记录重复导入保持幂等。
- Edge-TTS 失败后只重试一次，仍失败则停止，不使用系统 TTS 回退。
- 连续日期范围只启动一次导出；导出器通过本机单实例锁、每分钟 25 次节流、受限 `Retry-After` 重试、原子写入和请求统计避免并发放大与部分结果。

## 安装

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

Codex 用户需额外按 `skills/eudic-to-anki/RULES_README.md` 生成本机 rules。

## 配置

- 欧路词典 `EUDIC_TOKEN`：见 `skills/eudic-to-anki/references/openapi.md`
- Anki Desktop 与 AnkiConnect：见 `skills/eudic-to-anki/references/anki.md`
- 完整执行流程：见 `skills/eudic-to-anki/SKILL.md`

## 仓库结构

```text
skills/eudic-to-anki/
  SKILL.md
  assets/
  modules/
  references/
  scripts/
  workflows/
```

## 许可证

MIT，见 [LICENSE](LICENSE)。
