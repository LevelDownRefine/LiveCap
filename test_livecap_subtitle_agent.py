import unittest

from livecap_subtitle_agent import build_prompt, lines_to_srt


class SubtitleAgentTests(unittest.TestCase):
    def test_build_prompt_contains_source_text(self):
        text = "你好，今天我们测试字幕。"
        prompt = build_prompt(text)
        self.assertIn("原文", prompt)
        self.assertIn(text, prompt)

    def test_lines_to_srt_generates_timestamps(self):
        srt = lines_to_srt(["第一句", "第二句"], sec_per_line=1.5)
        self.assertIn("00:00:00,000 --> 00:00:01,500", srt)
        self.assertIn("00:00:01,500 --> 00:00:03,000", srt)
        self.assertIn("第一句", srt)
        self.assertIn("第二句", srt)


if __name__ == "__main__":
    unittest.main()
