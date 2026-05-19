# LiveCap

最简视频字幕 Agent。

## 安装

```bash
pip install -r requirements.txt
```

需要本机可执行 `ffmpeg`，并设置：

- `LIVECAP_API_KEY`
- `LIVECAP_MODEL`（可选）
- `LIVECAP_BASE_URL`（可选，默认 `https://api.openai.com/v1`）

## 使用

```bash
python livecap_subtitle_agent.py input.mp4 output.mp4
```
