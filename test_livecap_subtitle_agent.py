import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest import mock

import livecap_subtitle_agent
from livecap_subtitle_agent import (
    POSITION_TO_ALIGNMENT,
    SubtitleAgent,
    SubtitlePromptBuilder,
    SubtitleSegment,
)


class SubtitleAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = mock.Mock()
        self.agent = SubtitleAgent(
            api_key="token",
            model="model",
            base_url="https://example.com/v1",
            client=self.client,
        )

    def test_prompt_builder_mentions_json_and_positions(self) -> None:
        prompt = SubtitlePromptBuilder().build()
        self.assertIn('"segments"', prompt)
        self.assertIn("position", prompt)
        self.assertIn("bottom_right", prompt)

    def test_agent_build_prompt_comes_from_prompt_builder(self) -> None:
        prompt_builder = mock.Mock(build=mock.Mock(return_value="PROMPT"))
        agent = SubtitleAgent(api_key="token", model="model", client=self.client, prompt_builder=prompt_builder)
        self.assertEqual(agent.build_prompt(), "PROMPT")
        prompt_builder.build.assert_called_once_with()

    def test_parse_segments_accepts_code_fence(self) -> None:
        segments = self.agent.parse_segments(
            """```json
{"segments":[{"start":"00:00:01.00","end":"00:00:02.00","text":"你好","position":"top"}]}
```"""
        )
        self.assertEqual(
            segments,
            [SubtitleSegment(start="00:00:01.00", end="00:00:02.00", text="你好", position="top")],
        )

    def test_write_ass_contains_alignment_and_escaped_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ass_path = Path(temp_dir) / "subtitles.ass"
            self.agent.write_ass(
                ass_path,
                [SubtitleSegment("00:00:01.00", "00:00:02.00", "a{b}\nline", "top_right")],
            )
            content = ass_path.read_text(encoding="utf-8")

        self.assertIn(r"{\an9}a\{b\}\Nline", content)
        self.assertEqual(POSITION_TO_ALIGNMENT["top_right"], 9)

    def test_analyze_video_uses_openai_client_with_prompt_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "clip.mp4"
            video_path.write_bytes(b"video")

            self.client.responses.create.return_value = SimpleNamespace(
                output_text=json.dumps(
                    {
                        "segments": [
                            {
                                "start": "00:00:01.00",
                                "end": "00:00:02.00",
                                "text": "字幕",
                                "position": "bottom",
                            }
                        ]
                    }
                )
            )
            segments = self.agent.analyze_video(str(video_path))
            payload = self.client.responses.create.call_args.kwargs

        self.assertEqual(segments[0].text, "字幕")
        self.assertEqual(payload["model"], "model")
        self.assertEqual(payload["input"][0]["content"][0]["text"], self.agent.build_prompt())
        self.assertTrue(payload["input"][0]["content"][1]["file_data"].startswith("data:video/mp4;base64,"))
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")

    def test_render_video_uses_ffmpeg_python_chain(self) -> None:
        fake_stream = mock.Mock()
        fake_output = mock.Mock(return_value=fake_stream)
        fake_input_stream = mock.Mock(output=fake_output)
        fake_ffmpeg = mock.Mock(input=mock.Mock(return_value=fake_input_stream))
        fake_stream.overwrite_output.return_value = fake_stream

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = str(Path(temp_dir) / "in.mp4")
            ass_path = str(Path(temp_dir) / "subtitles.ass")
            output_path = str(Path(temp_dir) / "out.mp4")

            with mock.patch.object(livecap_subtitle_agent, "_ffmpeg_module", fake_ffmpeg):
                self.agent.render_video(video_path, ass_path, output_path)

        fake_ffmpeg.input.assert_called_once_with(video_path)
        fake_input_stream.output.assert_called_once_with(
            output_path,
            vf=f"ass={self.agent._escape_filter_path(ass_path)}",
            acodec="copy",
        )
        fake_stream.overwrite_output.assert_called_once_with()
        fake_stream.run.assert_called_once_with()

    def test_build_client_uses_openai_sdk(self) -> None:
        fake_client = object()
        with mock.patch.object(livecap_subtitle_agent, "_OpenAIClient", return_value=fake_client) as openai_class:
            agent = SubtitleAgent(api_key="token", model="model", base_url="https://example.com/v1", client=None)

        self.assertIs(agent.client, fake_client)
        openai_class.assert_called_once_with(api_key="token", base_url="https://example.com/v1")


if __name__ == "__main__":
    unittest.main()
