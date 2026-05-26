"""Tests for server.py FastAPI endpoints."""

import os
import shutil
import unittest

# httpx is bundled with fastapi/starlette test utilities
try:
    from fastapi.testclient import TestClient
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False

TEST_VIDEO = "test.mp4"


@unittest.skipUnless(HAS_TESTCLIENT, "fastapi TestClient not available")
@unittest.skipUnless(
    shutil.which("ffmpeg") and os.path.exists(TEST_VIDEO),
    "FFmpeg or test.mp4 not available",
)
class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import here so module-level import errors don't break other tests
        from server import app
        cls.client = TestClient(app)

    def test_upload_video(self):
        with open(TEST_VIDEO, "rb") as f:
            resp = self.client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("video_id", data)
        self.assertIn("duration", data)
        self.assertGreater(data["duration"], 0)
        # Store for subsequent tests
        self.__class__._video_id = data["video_id"]

    def test_upload_unsupported_format(self):
        from io import BytesIO
        resp = self.client.post(
            "/api/upload",
            files={"file": ("bad.txt", BytesIO(b"not a video"), "text/plain")},
        )
        self.assertEqual(resp.status_code, 400)

    def test_video_info(self):
        # Upload first
        with open(TEST_VIDEO, "rb") as f:
            upload = self.client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        vid = upload.json()["video_id"]
        resp = self.client.get(f"/api/video/{vid}/info")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("duration", resp.json())

    def test_video_stream(self):
        with open(TEST_VIDEO, "rb") as f:
            upload = self.client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        vid = upload.json()["video_id"]
        resp = self.client.get(f"/api/video/{vid}/stream")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("video", resp.headers.get("content-type", ""))

    def test_edit_single_segment(self):
        with open(TEST_VIDEO, "rb") as f:
            upload = self.client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        vid = upload.json()["video_id"]
        resp = self.client.post(
            "/api/edit",
            json={"video_id": vid, "segments": [{"start": 0, "end": 1}]},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("download_url", data)

    def test_edit_multiple_segments(self):
        with open(TEST_VIDEO, "rb") as f:
            upload = self.client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        vid = upload.json()["video_id"]
        resp = self.client.post(
            "/api/edit",
            json={
                "video_id": vid,
                "segments": [
                    {"start": 0, "end": 1},
                    {"start": 1, "end": 2},
                ],
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_edit_no_segments(self):
        with open(TEST_VIDEO, "rb") as f:
            upload = self.client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        vid = upload.json()["video_id"]
        resp = self.client.post(
            "/api/edit",
            json={"video_id": vid, "segments": []},
        )
        self.assertEqual(resp.status_code, 400)

    def test_video_not_found(self):
        resp = self.client.get("/api/video/00000000-0000-0000-0000-000000000000/info")
        self.assertEqual(resp.status_code, 404)

    def test_invalid_id_format(self):
        resp = self.client.get("/api/video/not-a-valid-uuid-!!!!/info")
        self.assertEqual(resp.status_code, 400)

    def test_download_not_found(self):
        resp = self.client.get("/api/download/00000000-0000-0000-0000-000000000000")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
