# LiveCap

最简视频字幕 Agent：`livecap_subtitle_agent.py`

当前流程：

1. 读取输入视频时长
2. 将“视频总时长 + 原文”发送给大模型
3. 要求大模型返回带 `start` / `end` / `text` 的字幕 JSON
4. 将返回结果写成 SRT，再烧录进视频

```bash
python livecap_subtitle_agent.py \
  --input input.mp4 \
  --output output.mp4 \
  --script "这里是视频文本" \
  --api-key "$LLM_API_KEY"
```
