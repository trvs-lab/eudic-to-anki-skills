# Audio Module

使用 Microsoft Edge online TTS（Python `edge-tts`）生成 MP3，默认声线为 `en-US-GuyNeural`。

## 硬失败策略

1. 导入前用同一 provider 和 voice 探测服务。
2. 暂时性失败以完全相同的参数重试一次，总尝试次数为 2。
3. 第二次仍失败，或输出文件缺失、为空、不是有效 MP3 时，停止整个导入。
4. 错误必须包含服务、单词、声线、尝试次数和失败原因。
5. 不得改用 macOS `say`、系统或浏览器 TTS、其他 provider 或其他 voice。
6. 所有音频在本地生成并通过校验后，才可改动 Anki note/card 或同步。

已有有效 `[sound:...]` 或显式提供的有效本地 MP3 可以复用；这属于输入复用，不是服务回退。

## 命令

- 安装：`pip install edge-tts`
- 试跑：`python3 scripts/edge_tts_runner.py --text "semantic" --output /tmp/semantic.mp3 --voice "en-US-GuyNeural"`
- 导入参数：`--audio-provider command --audio-format mp3 --audio-command 'python3 scripts/edge_tts_runner.py --text "{word}" --output "{output}" --voice "{voice}"'`

`--audio-command` 按 argv 执行，不经过 shell。
