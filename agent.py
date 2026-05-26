from openai import OpenAI
import os
import subprocess
import tempfile

# 外部独立工具函数
def get_prompt(texts: list[str]) -> str:
    '''通过提示词，使得大模型输出格式化'''
    return f"""请严格输出标准SRT字幕，只返回字幕内容，无多余文字：
1. 序号从1递增
2. 时间格式 00:00:00,000 --> 00:00:05,000
文案：{texts}"""

def llm_inference(client: OpenAI, model: str, prompt: str) -> str:
    '''调用大模型'''
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

def save_llm_result(srt_path: str, content: str):
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(content)

def gen_video(in_path: str, out_path: str, srt_path: str):
    '''生成视频字幕'''
    print(f"FFmpeg开始处理：{in_path}")
    srt_path = os.path.abspath(srt_path)
    in_path = os.path.abspath(in_path)
    out_path = os.path.abspath(out_path)
    _run_ffmpeg(['-i', in_path, '-i', srt_path, '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', out_path, '-y'])
    print(f"成功输出：{out_path}")


def clip_video(in_path: str, out_path: str, start: str, end: str):
    '''剪辑视频片段，start/end 格式如 "00:00:05" 或 "00:01:30.500"'''
    in_path = os.path.abspath(in_path)
    out_path = os.path.abspath(out_path)
    _run_ffmpeg(['-i', in_path, '-ss', start, '-to', end, '-c', 'copy', out_path, '-y'])
    print(f"剪辑完成：{out_path}")


def concat_videos(paths: list[str], out_path: str):
    '''将多个视频按顺序拼接为一个视频'''
    out_path = os.path.abspath(out_path)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
        list_file = f.name
    try:
        _run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', out_path, '-y'])
    finally:
        os.remove(list_file)
    print(f"拼接完成：{out_path}")


def change_speed(in_path: str, out_path: str, factor: float):
    '''调整视频速度，factor>1加速，<1减速（会重新编码）'''
    if factor <= 0:
        raise ValueError("速度倍率必须大于0")
    in_path = os.path.abspath(in_path)
    out_path = os.path.abspath(out_path)
    video_filter = f"setpts={1/factor}*PTS"
    audio_filter = f"atempo={factor}" if 0.5 <= factor <= 2.0 else f"atempo={max(0.5, min(2.0, factor))}"
    _run_ffmpeg(['-i', in_path, '-filter:v', video_filter, '-filter:a', audio_filter, out_path, '-y'])
    print(f"变速完成（{factor}x）：{out_path}")


def _run_ffmpeg(args: list[str]):
    '''执行 FFmpeg 命令，失败时抛出异常并附带 stderr'''
    result = subprocess.run(
        ['ffmpeg'] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg执行失败(码{result.returncode}): {result.stderr.decode(errors='replace')[-500:]}")


class VideoEditor:
    '''视频剪辑器：支持多段裁剪、拼接、变速，链式调用后 export 输出'''

    def __init__(self, src: str):
        if not os.path.exists(src):
            raise FileNotFoundError(f"源视频不存在: {src}")
        self._src = os.path.abspath(src)
        self._segments: list[tuple[str, str]] = []  # (start, end)
        self._speed: float | None = None

    def add_segment(self, start: str, end: str):
        '''添加一个剪辑片段（时间格式 HH:MM:SS 或 HH:MM:SS.mmm）'''
        self._segments.append((start, end))
        return self

    def set_speed(self, factor: float):
        '''设置输出速度倍率'''
        if factor <= 0:
            raise ValueError("速度倍率必须大于0")
        self._speed = factor
        return self

    def export(self, out_path: str) -> str:
        '''导出最终视频'''
        if not self._segments:
            raise ValueError("至少需要添加一个片段(add_segment)")

        tmp_dir = tempfile.mkdtemp(prefix="livecap_edit_")
        try:
            # 1. 逐段裁剪
            clip_paths = []
            for i, (start, end) in enumerate(self._segments):
                clip_path = os.path.join(tmp_dir, f"seg_{i}.mp4")
                clip_video(self._src, clip_path, start, end)
                clip_paths.append(clip_path)

            # 2. 拼接（单段则跳过）
            if len(clip_paths) == 1:
                merged = clip_paths[0]
            else:
                merged = os.path.join(tmp_dir, "merged.mp4")
                concat_videos(clip_paths, merged)

            # 3. 变速（可选）
            if self._speed and self._speed != 1.0:
                speed_out = os.path.join(tmp_dir, "speed.mp4")
                change_speed(merged, speed_out, self._speed)
                merged = speed_out

            # 4. 移动到最终输出
            out_path = os.path.abspath(out_path)
            _run_ffmpeg(['-i', merged, '-c', 'copy', out_path, '-y'])
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"导出完成：{out_path}")
        return out_path


class SubtitleAgent:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        self.model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def run_once(
        self,
        text_list: list[str],
        in_video: str,
        out_video: str,
        srt_path: str,
    ) -> str:
        prompt = get_prompt(text_list)
        llm_result = llm_inference(self._client, self.model, prompt)
        save_llm_result(srt_path, llm_result)
        gen_video(in_video, out_video, srt_path)
        return out_video
