import argparse
import base64
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import ffmpeg as _ffmpeg_module
except ImportError:  # pragma: no cover - exercised in runtime environments without the dependency.
    _ffmpeg_module = None

try:
    from openai import OpenAI as _OpenAIClient
except ImportError:  # pragma: no cover - exercised in runtime environments without the dependency.
    _OpenAIClient = None


POSITION_TO_ALIGNMENT = {
    "bottom_left": 1,
    "bottom": 2,
    "bottom_right": 3,
    "middle_left": 4,
    "center": 5,
    "middle_right": 6,
    "top_left": 7,
    "top": 8,
    "top_right": 9,
}


@dataclass
class SubtitleSegment:
    start: str
    end: str
    text: str
    position: str = "bottom"


class SubtitlePromptBuilder:
    def build(self) -> str:
        return (
            "请直接阅读视频并输出字幕规划结果。"
            "你必须只返回 JSON，格式为 "
            '{"segments":[{"start":"00:00:01.00","end":"00:00:03.00","text":"字幕","position":"bottom"}]}。'
            "position 只能是 top、center、bottom、top_left、top_right、middle_left、middle_right、bottom_left、bottom_right。"
            "只在有必要时添加字幕，时间连续且不重叠，text 为最终字幕内容。"
        )


class SubtitleAgent:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        client=None,
        prompt_builder: SubtitlePromptBuilder | None = None,
    ) -> None:
        self.api_key = api_key or os.environ["LIVECAP_API_KEY"]
        self.model = model or os.environ.get("LIVECAP_MODEL", "gpt-4.1")
        self.base_url = base_url or os.environ.get(
            "LIVECAP_BASE_URL",
            "https://api.openai.com/v1",
        )
        self.prompt_builder = prompt_builder or SubtitlePromptBuilder()
        self.client = client or self._build_client()

    def build_prompt(self) -> str:
        return self.prompt_builder.build()

    def generate(self, video_path: str, output_path: str) -> str:
        segments = self.analyze_video(video_path)
        with tempfile.TemporaryDirectory() as temp_dir:
            ass_path = Path(temp_dir) / "subtitles.ass"
            self.write_ass(ass_path, segments)
            self.render_video(video_path, ass_path, output_path)
        return output_path

    def analyze_video(self, video_path: str) -> list[SubtitleSegment]:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": self.build_prompt()},
                        {
                            "type": "input_file",
                            "filename": Path(video_path).name,
                            "file_data": self._to_data_url(video_path),
                        },
                    ],
                }
            ],
            text={"format": self._response_format()},
        )
        return self.parse_segments(self._extract_output_text(response))

    def write_ass(self, ass_path: str | Path, segments: Iterable[SubtitleSegment]) -> None:
        body = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding",
            "Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
            "0,0,0,0,100,100,0,0,1,2,0,2,40,40,40,1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        for segment in segments:
            alignment = POSITION_TO_ALIGNMENT.get(segment.position, POSITION_TO_ALIGNMENT["bottom"])
            text = self._escape_ass_text(segment.text)
            body.append(
                f"Dialogue: 0,{segment.start},{segment.end},Default,,0,0,0,,{{\\an{alignment}}}{text}"
            )
        Path(ass_path).write_text("\n".join(body) + "\n", encoding="utf-8")

    def render_video(self, video_path: str, ass_path: str | Path, output_path: str) -> None:
        if _ffmpeg_module is None:
            raise RuntimeError("ffmpeg-python is required. Install ffmpeg-python first.")
        filter_path = self._escape_filter_path(str(ass_path))
        (
            _ffmpeg_module.input(video_path)
            .output(output_path, vf=f"ass={filter_path}", acodec="copy")
            .overwrite_output()
            .run()
        )

    def parse_segments(self, raw_text: str) -> list[SubtitleSegment]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(cleaned)
        return [
            SubtitleSegment(
                start=item["start"],
                end=item["end"],
                text=item["text"],
                position=item.get("position", "bottom"),
            )
            for item in data["segments"]
        ]

    def _to_data_url(self, video_path: str) -> str:
        video_bytes = Path(video_path).read_bytes()
        return "data:video/mp4;base64," + base64.b64encode(video_bytes).decode("ascii")

    def _build_client(self):
        if _OpenAIClient is None:
            raise RuntimeError("openai is required. Install openai first.")
        return _OpenAIClient(api_key=self.api_key, base_url=self.base_url)

    def _response_format(self) -> dict:
        return {
            "type": "json_schema",
            "name": "subtitle_segments",
            "schema": {
                "type": "object",
                "properties": {
                    "segments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "string"},
                                "end": {"type": "string"},
                                "text": {"type": "string"},
                                "position": {"type": "string"},
                            },
                            "required": ["start", "end", "text", "position"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["segments"],
                "additionalProperties": False,
            },
        }

    def _extract_output_text(self, response) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text
        for item in getattr(response, "output", []):
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    return content.text
        raise RuntimeError("LLM response does not contain output_text.")

    def _escape_ass_text(self, text: str) -> str:
        return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")

    def _escape_filter_path(self, path: str) -> str:
        return (
            path.replace("\\", r"\\")
            .replace(":", r"\:")
            .replace("'", r"\'")
            .replace("[", r"\[")
            .replace("]", r"\]")
            .replace(",", r"\,")
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("output_path")
    args = parser.parse_args()
    SubtitleAgent().generate(args.video_path, args.output_path)


if __name__ == "__main__":
    main()
