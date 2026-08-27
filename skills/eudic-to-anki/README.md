# eudic-to-anki

将欧路词典的每次生词遇见转换为 Anki 单卡 Context Anchor 笔记。

## 安装

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

Codex 用户还需按 [RULES_README.md](RULES_README.md) 生成本机 rules。完整执行入口见 [SKILL.md](SKILL.md)。

## 设计

- 同一规范词形只保留一条 Anki note 和一张卡。
- 正面只显示单词与来源／改写／生成例句，点击单词发音；跨端固定目标词字号，例句文本块整体居中且内部左对齐。
- 背面不折叠，直接显示语境释义、IPA、英英、可选词块、两行构词线索、历史语境和遇见统计；构词线索不显示独立模块标题。
- 使用 `words::learn`、`words::defer`、`words::skip`；无效 `reject` 不导入。
- 新遇见会更新并重置单卡；相同遇见 ID 重复导入完全幂等。
- 欧路流程在整批本地导入及回读核验通过后自动清理对应来源原词；不要求云同步。清理失败保留待处理清单，成功后不保留备份或删除记录。
- 无来源时生成实用例句；过长或含噪来源句只做必要删改。
- 音频使用 Edge-TTS，同参数最多尝试两次，失败后停止，不回退到系统 TTS。
- 每次导入先按完整 SHA-256 严格检查并安全同步 Front、Back、CSS；模型二次验证成功后才调用 Edge-TTS 或写入卡片。
- 导入器与独立模型同步命令共用非阻塞锁；独立命令默认只做完整本地同步，显式 `--sync` 才触发云同步。
- 连续日期范围只执行一次导出；分类、分页与限频重试共享本机单实例锁和每分钟 25 次节流，输出采用原子替换并打印请求统计。

## 目录

- `modules/`：导出、内容、音频、导入规则
- `references/`：JSON 合同和环境说明
- `workflows/`：昨天、日期区间、手工词表流程
- `scripts/`：导出、合并、校验、音频和 AnkiConnect 实现
- `assets/`：TRVS-Lab 模型、模板与样式
