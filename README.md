# LiveCap

基于 OpenAI 接口生成 SRT 字幕，并通过 FFmpeg 将字幕封装到视频中。同时提供视频剪辑后端（FastAPI）和 Web 前端（React + Timeline Editor）。

## 项目结构

```
LiveCap/
├── agent.py            # 字幕生成 Agent（OpenAI + FFmpeg）
├── server.py           # FastAPI 视频剪辑服务
├── editor/             # FFmpeg 操作封装（probe / trim / concat）
├── web/                # React 前端（Vite + TypeScript）
├── tests/              # 单元测试
│   ├── test_agent.py
│   ├── test_ffmpeg_ops.py
│   └── test_server.py
├── requirements.txt    # Python 依赖
└── .github/workflows/  # CI 配置
```

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

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 安装前端依赖（可选）

```bash
cd web
npm install
```

## 快速使用

### 字幕生成 Agent

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

### 视频剪辑服务

启动后端：

```bash
python server.py
# 或
uvicorn server:app --reload --port 8000
```

启动前端开发服务器：

```bash
cd web
npm run dev
```

API 端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 上传视频 |
| GET | `/api/video/{video_id}/info` | 获取视频信息 |
| GET | `/api/video/{video_id}/stream` | 串流视频 |
| POST | `/api/edit` | 剪辑视频（trim / concat） |
| GET | `/api/download/{output_id}` | 下载输出 |

## 运行测试

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

测试依赖：

- 已安装 `ffmpeg`
- 已安装 Python 依赖：`pip install -r requirements.txt`
- 服务器测试还需要：`pip install httpx`

## CI

项目使用 GitHub Actions 进行持续集成，配置位于 `.github/workflows/ci.yml`。每次推送到 `main`/`master` 或创建 Pull Request 时自动运行测试。
