import unittest

from livecap_subtitle_agent import build_prompt, lines_to_srt, parse_timed_subtitles


class SubtitleAgentTests(unittest.TestCase):
    def test_build_prompt_contains_source_text(self):
        text = "你好，今天我们测试字幕。"
        prompt = build_prompt(text, video_duration=12.5)
        self.assertIn("原文", prompt)
        self.assertIn(text, prompt)
        self.assertIn("12.500", prompt)
        self.assertIn('"subtitles"', prompt)

    def test_parse_timed_subtitles_accepts_json(self):
        items = parse_timed_subtitles(
            """
            {
              "subtitles": [
                {"start": "00:00:00,000", "end": "00:00:01,500", "text": "第一句"},
                {"start": 1.5, "end": 3, "text": "第二句"}
              ]
            }
            """
        )
        self.assertEqual(2, len(items))
        self.assertEqual(0.0, items[0]["start"])
        self.assertEqual(1.5, items[0]["end"])
        self.assertEqual("第二句", items[1]["text"])

    def test_lines_to_srt_generates_timestamps(self):
        srt = lines_to_srt(["第一句", "第二句"], sec_per_line=1.5)
        self.assertTrue(srt.startswith("1\n"))
        self.assertIn("\n\n2\n", srt)
        self.assertIn("00:00:00,000 --> 00:00:01,500", srt)
        self.assertIn("00:00:01,500 --> 00:00:03,000", srt)
        self.assertIn("第一句", srt)
        self.assertIn("第二句", srt)
        self.assertIn("第一句\n\n2", srt)


if __name__ == "__main__":
    unittest.main()
