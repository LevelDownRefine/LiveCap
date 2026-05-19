import unittest
import os
import shutil
import tempfile
from unittest.mock import patch

from agent import SubtitleAgent, get_prompt, save_llm_result, gen_video


class TestNonLLMFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def test_get_prompt(self):
        texts = ["第一句文案", "第二句文案"]
        result = get_prompt(texts)

        self.assertIn("请严格输出标准SRT字幕", result)
        self.assertIn("序号从1递增", result)
        self.assertIn("时间格式 00:00:00,000 --> 00:00:05,000", result)
        self.assertIn("第一句文案", result)
        self.assertIn("第二句文案", result)

    def test_get_prompt_empty_list(self):
        texts = []
        result = get_prompt(texts)

        self.assertIn("请严格输出标准SRT字幕", result)
        self.assertIn("文案：[]", result)

    def test_get_prompt_single_item(self):
        texts = ["单个测试文案"]
        result = get_prompt(texts)

        self.assertIn("单个测试文案", result)

    def test_save_llm_result(self):
        content = "1\n00:00:00,000 --> 00:00:05,000\n测试字幕\n\n"
        save_llm_result(self.temp_path, content)

        with open(self.temp_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()

        self.assertEqual(saved_content, content)

    def test_save_llm_result_empty_content(self):
        save_llm_result(self.temp_path, "")

        with open(self.temp_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()

        self.assertEqual(saved_content, "")

    def test_gen_video_real(self):
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not installed")

        # 检查测试视频是否存在
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")
        
        in_path = "test.mp4"
        out_path = "test_real_output.mp4"
        srt_path = "test_real_sub.srt"
        
        # 创建测试字幕
        srt_content = """1
00:00:00,000 --> 00:00:02,000
测试字幕第一行

2
00:00:02,000 --> 00:00:04,000
测试字幕第二行

"""
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        

        # 执行真实的视频生成
        res = gen_video(in_path, out_path, srt_path)
        self.assertEqual(res, 0, "ffmpeg execution failed")
        
        # 验证输出文件是否生成
        self.assertTrue(os.path.exists(out_path), f"输出视频 {out_path} 没有被生成")
        
        # 检查文件大小大于 0
        self.assertGreater(os.path.getsize(out_path), 0, f"输出视频 {out_path} 是空的")


class TestSubtitleAgent(unittest.TestCase):
    @patch("agent.OpenAI")
    @patch("agent.gen_video")
    @patch("agent.save_llm_result")
    @patch("agent.llm_inference")
    def test_run_accepts_paths_as_parameters(self, mock_llm_inference, mock_save_llm_result, mock_gen_video, mock_openai):
        mock_llm_inference.return_value = "1\n00:00:00,000 --> 00:00:01,000\n测试字幕\n"
        mock_gen_video.return_value = 0

        agent = SubtitleAgent(api_key="test-key")
        result = agent.run(
            ["测试文案"],
            in_video="input.mp4",
            out_video="output.mp4",
            srt_path="output.srt",
        )

        mock_openai.assert_called_once_with(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_llm_inference.assert_called_once()
        mock_save_llm_result.assert_called_once_with("output.srt", mock_llm_inference.return_value)
        mock_gen_video.assert_called_once_with("input.mp4", "output.mp4", "output.srt")
        self.assertEqual(result, "output.mp4")

    @patch("agent.OpenAI")
    @patch("agent.gen_video")
    @patch("agent.save_llm_result")
    @patch("agent.llm_inference")
    def test_run_raises_when_video_generation_fails(self, mock_llm_inference, mock_save_llm_result, mock_gen_video, mock_openai):
        mock_llm_inference.return_value = "1\n00:00:00,000 --> 00:00:01,000\n测试字幕\n"
        mock_gen_video.return_value = 1

        agent = SubtitleAgent(api_key="test-key")

        with self.assertRaises(RuntimeError):
            agent.run(
                ["测试文案"],
                in_video="input.mp4",
                out_video="output.mp4",
                srt_path="output.srt",
            )


if __name__ == '__main__':
    unittest.main()
