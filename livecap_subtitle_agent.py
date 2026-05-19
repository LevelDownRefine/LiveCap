import argparse
import json
import os
import tempfile
import urllib.request


def build_prompt(script: str) -> str:
    return (
        "请将下面文本拆成适合视频字幕的短句，每行不超过16个汉字。"
        "仅输出字幕内容，每行一句，不要编号和解释。\n\n"
        f"原文:\n{script.strip()}"
    )


def call_llm(prompt: str, model: str, api_key: str, base_url: str) -> str:
    if not api_key:
        raise ValueError("Missing API key")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是字幕整理助手"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hh = ms // 3600000
    ms %= 3600000
    mm = ms // 60000
    ms %= 60000
    ss = ms // 1000
    ms %= 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def lines_to_srt(lines: list[str], sec_per_line: float = 2.0) -> str:
    blocks = []
    for i, line in enumerate([x.strip() for x in lines if x.strip()], start=1):
        start = (i - 1) * sec_per_line
        end = i * sec_per_line
        blocks.append(f"{i}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{line}\n")
    return "\n".join(blocks)


def render_with_ffmpeg(input_video: str, subtitle_srt: str, output_video: str) -> None:
    import ffmpeg

    src = ffmpeg.input(input_video)
    video = src.video.filter("subtitles", subtitle_srt)
    audio = src.audio
    (
        ffmpeg.output(video, audio, output_video)
        .overwrite_output()
        .run(quiet=False)
    )


def run(input_video: str, output_video: str, script: str, model: str, base_url: str, api_key: str) -> None:
    prompt = build_prompt(script)
    llm_out = call_llm(prompt, model=model, api_key=api_key, base_url=base_url)
    srt_text = lines_to_srt(llm_out.splitlines())

    fd, srt_path = tempfile.mkstemp(suffix=".srt")
    os.close(fd)
    try:
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)
        render_with_ffmpeg(input_video, srt_path, output_video)
    finally:
        if os.path.exists(srt_path):
            os.remove(srt_path)


def main() -> None:
    p = argparse.ArgumentParser(description="最简视频字幕 Agent")
    p.add_argument("--input", required=True, help="输入视频路径")
    p.add_argument("--output", required=True, help="输出视频路径")
    p.add_argument("--script", required=True, help="待整理为字幕的文本")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    p.add_argument("--api-key", default=os.getenv("LLM_API_KEY", ""))
    args = p.parse_args()

    run(
        input_video=args.input,
        output_video=args.output,
        script=args.script,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    main()
