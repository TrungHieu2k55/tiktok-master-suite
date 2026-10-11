"""
tests/test_streak.py
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.streak.bot import TikTokStreakBot


class TestStreakBot(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bot = TikTokStreakBot(headless=True)
        self.bot.config_path = Path(self.test_dir) / "streak_targets.json"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_empty_targets(self):
        targets = self.bot.load_targets()
        self.assertEqual(targets, [])

    def test_save_and_load_targets(self):
        sample = [
            {"username": "user1", "custom_msg": "hi 🔥", "status": "Ready"},
            {"username": "user2", "custom_msg": None, "status": "Ready"},
        ]
        self.bot.save_targets(sample)
        loaded = self.bot.load_targets()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["username"], "user1")
        self.assertEqual(loaded[1]["username"], "user2")

    def test_save_and_load_cookie_string(self):
        with patch("src.streak.bot.SESSION_DIR", Path(self.test_dir)):
            self.bot.save_session_cookie_string("my_raw_session_token_123")
            loaded = self.bot.load_session_cookie_string()
            self.assertIn("sessionid=my_raw_session_token_123", loaded)

    def test_check_streak_status_cloud_engine(self):
        # Khi driver là None (chạy trên Streamlit Cloud không có đồ họa)
        with patch.object(self.bot, "_get_driver", return_value=None):
            res = self.bot.check_streak_status("tiktok")
            self.assertIsInstance(res, dict)
            self.assertTrue(res.get("checked"))
            self.assertIn("status_desc", res)

    def test_send_streak_message_cloud_fallback(self):
        with patch.object(self.bot, "_get_driver", return_value=None):
            ok = self.bot.send_streak_message("target_user")
            self.assertTrue(ok)
            targets = self.bot.load_targets()
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0]["username"], "target_user")
            self.assertIn("Thành công", targets[0]["status"])

    def test_spam_hu_hu_cloud_fallback(self):
        with patch.object(self.bot, "_get_driver", return_value=None):
            res = self.bot.spam_hu_hu("target_user", max_rounds=3)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["sent"], 3)
            self.assertFalse(res["replied"])


if __name__ == "__main__":
    unittest.main()