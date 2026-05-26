"""FFmpeg video editing operations: trim and concat."""

import subprocess
import json
import os
import tempfile
from dataclasses import dataclass


@dataclass
class VideoInfo:
    duration: float
    width: int
    height: int
    fps: float


def probe(path: str) -> VideoInfo:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    video_stream = next(
        (s for s in data["streams"] if s["codec_type"] == "video"), None
    )
    if not video_stream:
        raise ValueError("No video stream found")
    duration = float(data["format"]["duration"])
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
    num, den = r_frame_rate.split("/")
    fps = round(int(num) / int(den), 2)
    return VideoInfo(duration=duration, width=width, height=height, fps=fps)


def trim(input_path: str, start: float, end: float, output_path: str) -> str:
    """Trim a video segment from start to end (seconds)."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ss", str(start), "-to", str(end),
        "-c", "copy", "-avoid_negative_ts", "make_zero",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _validate_path(path: str, allowed_dir: str | None = None) -> str:
    """Validate that a path does not escape the allowed directory."""
    resolved = os.path.realpath(path)
    if allowed_dir:
        allowed = os.path.realpath(allowed_dir)
        if not resolved.startswith(allowed + os.sep) and resolved != allowed:
            raise ValueError(f"Path escapes allowed directory: {path}")
    return resolved


def concat(segments: list[str], output_path: str) -> str:
    """Concatenate multiple video segments using concat demuxer."""
    # Validate all segment paths exist and are regular files
    validated_segments: list[str] = []
    for seg in segments:
        resolved = os.path.realpath(seg)
        if not os.path.isfile(resolved):
            raise ValueError(f"Segment is not a valid file: {seg}")
        validated_segments.append(resolved)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for seg in validated_segments:
            f.write(f"file '{seg}'\n")
        list_path = f.name
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    finally:
        os.unlink(list_path)
    return output_path
