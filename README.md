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

### 简单裁剪

```python
from agent import clip_video

clip_video("src.mp4", "clip_out.mp4", start="00:00:05", end="00:00:15")
```

### 多段剪辑 + 拼接 + 变速

```python
from agent import VideoEditor

(VideoEditor("src.mp4")
    .add_segment("00:00:05", "00:00:15")   # 取第5-15秒
    .add_segment("00:01:00", "00:01:30")   # 取第60-90秒
    .set_speed(1.5)                         # 1.5倍速
    .export("final.mp4"))
```

### 拼接多个视频

```python
from agent import concat_videos

concat_videos(["part1.mp4", "part2.mp4", "part3.mp4"], "merged.mp4")
```

### 调整速度

```python
from agent import change_speed

change_speed("src.mp4", "fast.mp4", factor=2.0)  # 2倍速
```

## 运行测试

```bash
python -m unittest -v
```

测试依赖：

- 已安装 `ffmpeg`
- 已安装 `openai`

## Web 前端

启动剪辑服务：

```bash
pip install -r requirements.txt
python server.py
```

浏览器打开 http://localhost:5000 即可使用可视化剪辑界面：

1. 上传视频文件
2. 在播放器中预览，点击"当前为起点/终点"快捷设置时间
3. 添加多个剪辑片段
4. 可选调整速度倍率
5. 点击"导出视频"，完成后可直接下载
