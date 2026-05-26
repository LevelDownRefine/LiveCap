# LiveCap

基于 OpenAI 接口生成 SRT 字幕，并通过 FFmpeg 将字幕封装到视频中。

## 依赖安装

建议先创建并激活一个 conda 环境，再安装运行所需依赖。

### 1. 使用 conda 安装 FFmpeg

```bash
conda create -n livecap python=3.12 -y
conda activate livecap
conda install -c conda-forge ffmpeg -y
```

安装完成后可执行以下命令确认 FFmpeg 可用：

```bash
ffmpeg -version
```

### 2. 使用 pip 安装 openai

```bash
pip install openai
```

如果你需要运行仓库中的测试，也建议在同一环境中执行以上安装步骤。

## 快速使用

```python
from agent import SubtitleAgent

agent = SubtitleAgent(api_key="YOUR_OPENAI_API_KEY")
output_path = agent.run_once(
    ["第一句文案", "第二句文案"],
    in_video="src.mp4",
    out_video="sub_out.mp4",
    srt_path="sub.srt",
)
print(output_path)
```

## 视频剪辑

```python
from agent import clip_video

clip_video("src.mp4", "clip_out.mp4", start="00:00:05", end="00:00:15")
```

## 运行测试

```bash
python -m unittest -v
```

测试依赖：

- 已安装 `ffmpeg`
- 已安装 `openai`
