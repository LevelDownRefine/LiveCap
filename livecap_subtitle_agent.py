import argparse
import json
import os
import re
import tempfile
import urllib.error
import urllib.request

def build_prompt(script: str, video_duration: float) -> str:
    return (
        "请根据视频总时长和原文输出字幕时间轴，返回严格 JSON。"
        '输出格式: {"subtitles":[{"start":"00:00:00,000","end":"00:00:02,000","text":"字幕内容"}]}。'
        "不要输出 JSON 之外的任何内容。每条字幕简短，按时间顺序排列，且不要重叠。\n\n"
        f"视频总时长(秒): {video_duration:.3f}\n\n"
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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise RuntimeError(f"LLM API call failed: {exc}") from exc
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("Invalid LLM response: missing choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Invalid LLM response: missing message content")
    return content.strip()


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hh = ms // 3600000
    ms %= 3600000
    mm = ms // 60000
    ms %= 60000
    ss = ms // 1000
    ms %= 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _parse_ts(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        raise ValueError(f"Unsupported timestamp value: {value!r}")
    raw = value.strip()
    if not raw:
        raise ValueError("Empty timestamp")
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        return float(raw)
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", raw)
    if not match:
        raise ValueError(f"Invalid timestamp format: {value!r}")
    hh, mm, ss, ms = (int(part) for part in match.groups())
    return hh * 3600 + mm * 60 + ss + ms / 1000


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_timed_subtitles(llm_out: str) -> list[dict[str, float | str]]:
    payload = _strip_code_fences(llm_out)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid LLM response: expected JSON subtitles") from exc

    items = data.get("subtitles") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise ValueError("Invalid LLM response: missing subtitles list")

    parsed = []
    prev_end = 0.0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid LLM response: each subtitle must be an object")
        text = str(item.get("text", "")).strip()
        if not text:
            raise ValueError("Invalid LLM response: subtitle text is required")
        raw_start = item.get("start")
        if raw_start is None:
            raise ValueError("Invalid LLM response: subtitle start time is required")
        raw_end = item.get("end")
        if raw_end is None:
            raise ValueError("Invalid LLM response: subtitle end time is required")
        start = _parse_ts(raw_start)
        end = _parse_ts(raw_end)
        if start < 0:
            raise ValueError("Invalid LLM response: subtitle start time cannot be negative")
        if end <= start:
            raise ValueError("Invalid LLM response: subtitle end time must be after start time")
        if start < prev_end:
            raise ValueError("Invalid LLM response: subtitles must be ordered and must not overlap")
        parsed.append({"start": start, "end": end, "text": text})
        prev_end = end
    return parsed


def segments_to_srt(segments: list[dict[str, float | str]]) -> str:
    return "\n".join(
        f"{i}\n{_fmt_ts(float(segment['start']))} --> {_fmt_ts(float(segment['end']))}\n{segment['text']}\n"
        for i, segment in enumerate(segments, start=1)
    )


def lines_to_srt(lines: list[str], sec_per_line: float = 2.0) -> str:
    return segments_to_srt(
        [
            {"start": (i - 1) * sec_per_line, "end": i * sec_per_line, "text": line.strip()}
            for i, line in enumerate(lines, start=1)
            if line.strip()
        ]
    )


def get_video_duration(input_video: str) -> float:
    import ffmpeg

    probe = ffmpeg.probe(input_video)
    duration = (probe.get("format") or {}).get("duration")
    if duration is not None:
        return float(duration)
    for stream in probe.get("streams") or []:
        duration = stream.get("duration")
        if duration is not None:
            return float(duration)
    raise ValueError(f"Could not determine duration for video: {input_video}")


def render_with_ffmpeg(input_video: str, subtitle_srt: str, output_video: str) -> None:
    import ffmpeg

    safe_subtitle_path = (
        os.path.abspath(subtitle_srt)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )
    src = ffmpeg.input(input_video)
    video = src.video.filter("subtitles", safe_subtitle_path)
    audio = src.audio
    (
        ffmpeg.output(video, audio, output_video)
        .overwrite_output()
        .run(quiet=False)
    )


def run(input_video: str, output_video: str, script: str, model: str, base_url: str, api_key: str) -> None:
    duration = get_video_duration(input_video)
    prompt = build_prompt(script, video_duration=duration)
    llm_out = call_llm(prompt, model=model, api_key=api_key, base_url=base_url)
    srt_text = segments_to_srt(parse_timed_subtitles(llm_out))

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
        srt_path = tmp.name
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
