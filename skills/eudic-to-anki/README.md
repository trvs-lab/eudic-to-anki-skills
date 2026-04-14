# eudic-to-anki

## 安装（Vercel skills CLI）

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

安装完成后，在 agent 里以 **本目录为 cwd**（包含 `SKILL.md` 的目录）运行文档中的命令。详见仓库根目录 [README.md](../../README.md)。`EUDIC_TOKEN` 的配置步骤只写在 [references/openapi.md](references/openapi.md)，避免多处重复。

## 目录结构

- `SKILL.md`：唯一主入口（agent-first）
- `modules/export/README.md`：欧路导出模块
- `modules/coach/README.md`：TRVS-Lab 内容与校验模块
- `modules/import/README.md`：Anki 导入模块
- `modules/audio/README.md`：发音模块
- `workflows/`：按场景的执行清单
- `scripts/`：统一命令入口（已内聚实现）
- 中间文件默认写到 `~/Documents/eudic-to-anki-temp/`

## 常用命令

- 导入成功后 `ankiconnect_import.py` **默认**会调用 Anki 同步（AnkiConnect `sync`）；不需要同步时加 `--no-sync`。
- 环境检查：`bash scripts/check_env.sh`
- 列分类：`python3 scripts/eudic_export.py --list-categories`
- Anki 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 音频试跑：`python3 scripts/edge_tts_runner.py --text "semantic" --output /tmp/semantic.mp3`
- 大批量 base64 解码：`python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o ~/Documents/eudic-to-anki-temp/coach_batch_01.json`
