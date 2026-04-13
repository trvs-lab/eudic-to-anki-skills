# Audio Module

负责发音音频生成，不负责词条内容生成。

## 默认方案

- Edge-TTS 命令模式（在线）
- 运行器：`scripts/edge_tts_runner.py`

## 命令

- 安装：`pip install edge-tts`
- 试跑：`python3 scripts/edge_tts_runner.py --text \"semantic\" --output /tmp/semantic.mp3`
- 可选声线：`export EDGE_TTS_VOICE=\"en-US-GuyNeural\"`

## 在导入命令中的挂载方式

- `--audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text \"{word}\" --output \"{output}\"'`

## 参考

- `references/edge-tts.md`