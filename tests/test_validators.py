"""
tests/test_validators.py
"""
import unittest
from src.utils.validators import (
    extract_username,
    extract_video_id,
    is_valid_user_url,
    is_valid_video_url,
)


class TestValidators(unittest.TestCase):
    def test_valid_video_url(self):
        self.assertTrue(is_valid_video_url("https://www.tiktok.com/@user123/video/7890123456789"))
        self.assertTrue(is_valid_video_url("https://tiktok.com/@user.name/video/1234567890"))
        self.assertTrue(is_valid_video_url("http://www.tiktok.com/@user/video/111"))

    def test_invalid_video_url(self):
        self.assertFalse(is_valid_video_url("https://youtube.com/watch?v=abc"))
        self.assertFalse(is_valid_video_url("https://tiktok.com/@user"))
        self.assertFalse(is_valid_video_url("not_a_url"))
        self.assertFalse(is_valid_video_url(""))

    def test_valid_user_url(self):
        self.assertTrue(is_valid_user_url("https://www.tiktok.com/@username"))
        self.assertTrue(is_valid_user_url("https://tiktok.com/@some.user"))

    def test_invalid_user_url(self):
        self.assertFalse(is_valid_user_url("https://tiktok.com/without_at"))
        self.assertFalse(is_valid_user_url("https://facebook.com/@username"))

    def test_extract_video_id(self):
        vid = extract_video_id("https://www.tiktok.com/@user/video/9876543210")
        self.assertEqual(vid, "9876543210")

    def test_extract_video_id_invalid_raises(self):
        with self.assertRaises(ValueError):
            extract_video_id("https://www.tiktok.com/@user/other_path")

    def test_extract_username(self):
        user = extract_username("https://www.tiktok.com/@myuser/video/123")
        self.assertEqual(user, "myuser")

    def test_extract_username_invalid_raises(self):
        with self.assertRaises(ValueError):
            extract_username("https://www.tiktok.com/no_at_symbol")


if __name__ == "__main__":
    unittest.main()
