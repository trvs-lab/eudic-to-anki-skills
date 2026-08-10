# Edge-TTS Reference

- 服务：Microsoft Edge online TTS
- Python 包：`edge-tts`
- 默认声线：`en-US-GuyNeural`
- 试跑：`python3 scripts/edge_tts_runner.py --text "semantic" --output /tmp/semantic.mp3 --voice "en-US-GuyNeural"`

导入器先使用相同 provider 和 voice 做在线探测。暂时性失败只重试一次；第二次失败、零字节文件或无效 MP3 都会中止整次导入。不得切换到 macOS `say`、系统／浏览器 TTS、其他 provider 或其他 voice。
