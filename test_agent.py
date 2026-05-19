import unittest
import os
import shutil
import tempfile

from agent import get_prompt, save_llm_result, gen_video


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

        # Check if test video exists
        self.assertTrue(os.path.exists('test.mp4'), "Test video test.mp4 does not exist")
        
        in_path = "test.mp4"
        out_path = "test_real_output.mp4"
        srt_path = "test_real_sub.srt"
        
        # Create test subtitles
        srt_content = """1
00:00:00,000 --> 00:00:02,000
Test subtitle line 1

2
00:00:02,000 --> 00:00:04,000
Test subtitle line 2

"""
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        

        # Execute real video generation
        res = gen_video(in_path, out_path, srt_path)
        self.assertEqual(res, 0, "ffmpeg execution failed")
        
        # Verify output file is generated
        self.assertTrue(os.path.exists(out_path), f"Output video {out_path} was not generated")
        
        # Check file size is greater than 0
        self.assertGreater(os.path.getsize(out_path), 0, f"Output video {out_path} is empty")


if __name__ == '__main__':
    unittest.main()
