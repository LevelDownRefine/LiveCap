"""Tests for editor/ffmpeg_ops.py — requires FFmpeg installed."""

import os
import shutil
import tempfile
import unittest

from editor.ffmpeg_ops import probe, trim, concat, VideoInfo


TEST_VIDEO = "test.mp4"


@unittest.skipUnless(
    shutil.which("ffmpeg") and os.path.exists(TEST_VIDEO),
    "FFmpeg or test.mp4 not available",
)
class TestProbe(unittest.TestCase):
    def test_probe_returns_video_info(self):
        info = probe(TEST_VIDEO)
        self.assertIsInstance(info, VideoInfo)
        self.assertGreater(info.duration, 0)
        self.assertGreater(info.width, 0)
        self.assertGreater(info.height, 0)
        self.assertGreater(info.fps, 0)

    def test_probe_invalid_file(self):
        with self.assertRaises(Exception):
            probe("nonexistent_file.mp4")


@unittest.skipUnless(
    shutil.which("ffmpeg") and os.path.exists(TEST_VIDEO),
    "FFmpeg or test.mp4 not available",
)
class TestTrim(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_trim_creates_output(self):
        out = os.path.join(self.tmp_dir, "trimmed.mp4")
        result = trim(TEST_VIDEO, 0, 1, out)
        self.assertEqual(result, out)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_trim_subset(self):
        out = os.path.join(self.tmp_dir, "trimmed2.mp4")
        trim(TEST_VIDEO, 0.5, 1.5, out)
        info = probe(out)
        # trimmed duration should be roughly 1 second (tolerance for keyframes)
        self.assertLess(info.duration, 3.0)


@unittest.skipUnless(
    shutil.which("ffmpeg") and os.path.exists(TEST_VIDEO),
    "FFmpeg or test.mp4 not available",
)
class TestConcat(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_concat_two_segments(self):
        seg1 = os.path.join(self.tmp_dir, "seg1.mp4")
        seg2 = os.path.join(self.tmp_dir, "seg2.mp4")
        trim(TEST_VIDEO, 0, 1, seg1)
        trim(TEST_VIDEO, 0, 1, seg2)

        out = os.path.join(self.tmp_dir, "concat.mp4")
        result = concat([seg1, seg2], out)
        self.assertEqual(result, out)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_concat_invalid_segment(self):
        with self.assertRaises(ValueError):
            concat(["nonexistent.mp4"], os.path.join(self.tmp_dir, "out.mp4"))


if __name__ == "__main__":
    unittest.main()
