# eudic-to-anki

统一后的单一 skill。用户和 agent 只需要从这里进入，不再跨多个 skill 来回跳读。

## 安装（Vercel skills CLI）

本仓库符合 [Agent Skills](https://agentskills.io/) 与 [Vercel Agent Skills](https://vercel.com/docs/agent-resources/skills) 约定的 `skills/<skill-name>/` 布局。发布到 GitHub 后，他人可执行：

```bash
npx skills add <owner>/<repo> --skill eudic-to-anki
```

安装完成后，在 agent 里以 **本目录为 cwd**（包含 `SKILL.md` 的目录）运行文档中的命令。详见仓库根目录 [README.md](../../README.md)。

## 目录结构

- `SKILL.md`：唯一主入口（agent-first）
- `modules/export/README.md`：欧路导出模块
- `modules/coach/README.md`：TRVS-Lab 内容与校验模块
- `modules/import/README.md`：Anki 导入模块
- `modules/audio/README.md`：发音模块
- `workflows/`：按场景的执行清单
- `scripts/`：统一命令入口（已内聚实现）
- `import_scratch/`：中间文件目录

## 常用命令

- 环境检查：`bash scripts/check_env.sh`
- 列分类：`python3 scripts/eudic_export.py --list-categories`
- Anki 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 音频试跑：`python3 scripts/edge_tts_runner.py --text "semantic" --output /tmp/semantic.mp3`
- 大批量 base64 解码：`python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o import_scratch/coach_batch_01.json`

## 现状说明

导出、导入、TTS、模型资产与参考文档都已迁入本 skill，旧目录已移除。