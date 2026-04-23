# eudic-to-anki

## 安装（Vercel skills CLI）

```bash
npx skills add trvs-lab/eudic-to-anki-skills --skill eudic-to-anki -g -y
```

安装完成后，如果你使用的是 Codex 客户端，再打开 [RULES_README.md](RULES_README.md)，按其中模板生成 `~/.codex/rules/eudic-to-anki.rules`，并把所有 `<HOME>` 替换成当前机器上的真实 home 绝对路径；这一步只针对 Codex。随后在 agent 里以 **本目录为 cwd**（包含 `SKILL.md` 的目录）运行文档中的命令。详见仓库根目录 [README.md](../../README.md)。`EUDIC_TOKEN` 的配置步骤只写在 [references/openapi.md](references/openapi.md)，避免多处重复。

## 目录结构

- `SKILL.md`：唯一主入口（agent-first）
- `modules/export/README.md`：欧路导出模块
- `modules/coach/README.md`：TRVS-Lab 内容与校验模块
- `modules/import/README.md`：Anki 导入模块
- `modules/audio/README.md`：发音模块
- `workflows/`：按场景的执行清单
- `scripts/`：统一命令入口（已内聚实现）
- 中间文件默认写到专用 Documents 工件目录；执行时请使用展开后的绝对路径，例如 `<ABS_TEMP_DIR>` / `/Users/alice/Documents/eudic-to-anki-temp/`

## 常用命令

- 导入成功后 `ankiconnect_import.py` **默认**会调用 Anki 同步（AnkiConnect `sync`）；不需要同步时加 `--no-sync`。
- 最终导入前必须通过内容质量校验：完整 IPA、简洁中文释义、通俗解释型英英释义、来源句优先例句、词根词缀拆解、常用搭配。
- 环境检查：`bash scripts/check_env.sh`
- 列分类：`python3 scripts/eudic_export.py --list-categories`
- Anki 连通性：`python3 scripts/ankiconnect_import.py --ping`
- 同步内置 TRVS-Lab 模板到 Anki：`python3 scripts/sync_trvs_lab_model.py`
- 导入预演：`python3 scripts/ankiconnect_import.py --input <ABS_TEMP_DIR>/import.json --deck words --create-deck --dia-upsert --verify-required-fields --dry-run`
- 真实导入：加 `--require-audio --verify-required-fields`，并用 audio provider 生成/保留 `发音` 字段。
- 音频试跑：`python3 scripts/edge_tts_runner.py --text "semantic" --output /tmp/semantic.mp3`
- 大批量 base64 解码：`python3 scripts/decode_subagent_transcript_b64.py <subagent.jsonl> -o <ABS_TEMP_DIR>/coach_batch_01.json`
