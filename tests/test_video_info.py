"""
tests/test_video_info.py
"""
import unittest
from unittest.mock import patch
from src.research.video_info import anonymize_video_info, fetch_video_info


class TestVideoInfo(unittest.TestCase):
    def setUp(self):
        self.valid_url = "https://www.tiktok.com/@creator/video/1234567890123"

    def test_fetch_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            fetch_video_info("https://invalid.url")

    def test_anonymize_video_info(self):
        raw_info = {
            "author_id": "creator_real_id",
            "author_name": "Nguyen Van A",
            "avatar_thumb": "https://img.tiktok.com/avatar.jpg",
            "signature": "bio text",
            "video_id": "1234567890123",
            "title": "Video title",
            "view_count": 1000,
            "like_count": 200,
            "create_time": 1700000000,
        }
        anon = anonymize_video_info(raw_info)
        self.assertEqual(len(anon["author_id"]), 64)
        self.assertNotIn("author_name", anon)
        self.assertNotIn("avatar_thumb", anon)
        self.assertNotIn("signature", anon)
        self.assertEqual(anon["create_time"], "2023-11-14T22:13:20Z")

    @patch("src.research.video_info._call_selenium_video")
    def test_fetch_video_info_retry_success(self, mock_call):
        mock_call.return_value = {
            "video_id": "1234567890123",
            "author_id": "user_id",
            "like_count": 500,
        }
        res = fetch_video_info(self.valid_url, max_retries=2)
        self.assertEqual(res["video_id"], "1234567890123")
        self.assertEqual(mock_call.call_count, 1)


if __name__ == "__main__":
    unittest.main()