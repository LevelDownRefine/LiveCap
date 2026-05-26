import unittest
import os
import shutil
import tempfile

from agent import (
    get_prompt, save_llm_result, gen_video,
    clip_video, concat_videos, change_speed, VideoEditor,
)


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
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")

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
        gen_video(in_path, out_path, srt_path)
        
        # 验证输出文件是否生成
        self.assertTrue(os.path.exists(out_path), f"输出视频 {out_path} 没有被生成")
        
        # 检查文件大小大于 0
        self.assertGreater(os.path.getsize(out_path), 0, f"输出视频 {out_path} 是空的")


    def test_clip_video(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")

        out_path = "test_clip_output.mp4"
        clip_video("test.mp4", out_path, "00:00:00", "00:00:02")

        self.assertTrue(os.path.exists(out_path), f"剪辑输出 {out_path} 没有被生成")
        self.assertGreater(os.path.getsize(out_path), 0)

        if os.path.exists(out_path):
            os.remove(out_path)

    def test_concat_videos(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")

        # 先裁剪两段
        seg1 = "test_seg1.mp4"
        seg2 = "test_seg2.mp4"
        clip_video("test.mp4", seg1, "00:00:00", "00:00:02")
        clip_video("test.mp4", seg2, "00:00:02", "00:00:04")

        out_path = "test_concat_output.mp4"
        concat_videos([seg1, seg2], out_path)

        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)

        for f in [seg1, seg2, out_path]:
            if os.path.exists(f):
                os.remove(f)

    def test_change_speed(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")

        out_path = "test_speed_output.mp4"
        change_speed("test.mp4", out_path, 2.0)

        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)

        if os.path.exists(out_path):
            os.remove(out_path)

    def test_change_speed_invalid(self):
        with self.assertRaises(ValueError):
            change_speed("test.mp4", "out.mp4", 0)

    def test_video_editor_single_segment(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")

        out_path = "test_editor_single.mp4"
        VideoEditor("test.mp4").add_segment("00:00:00", "00:00:02").export(out_path)

        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)

        if os.path.exists(out_path):
            os.remove(out_path)

    def test_video_editor_multi_segment(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")

        out_path = "test_editor_multi.mp4"
        (VideoEditor("test.mp4")
            .add_segment("00:00:00", "00:00:02")
            .add_segment("00:00:03", "00:00:04")
            .export(out_path))

        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)

        if os.path.exists(out_path):
            os.remove(out_path)

    def test_video_editor_with_speed(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg 未安装")
        self.assertTrue(os.path.exists('test.mp4'), "测试视频 test.mp4 不存在")

        out_path = "test_editor_speed.mp4"
        (VideoEditor("test.mp4")
            .add_segment("00:00:00", "00:00:04")
            .set_speed(1.5)
            .export(out_path))

        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)

        if os.path.exists(out_path):
            os.remove(out_path)

    def test_video_editor_no_segment_raises(self):
        editor = VideoEditor("test.mp4")
        with self.assertRaises(ValueError):
            editor.export("out.mp4")

    def test_video_editor_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            VideoEditor("nonexistent.mp4")


if __name__ == '__main__':
    unittest.main()
