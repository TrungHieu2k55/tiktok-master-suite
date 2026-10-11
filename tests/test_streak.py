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
        # Cách ly Unit Test khỏi Live Supabase để không ghi đè dữ liệu thật
        self.patch_supa_get = patch("src.streak.bot.supabase_get", return_value=None)
        self.patch_supa_set = patch("src.streak.bot.supabase_set", return_value=True)
        self.patch_supa_get.start()
        self.patch_supa_set.start()

    def tearDown(self):
        self.patch_supa_get.stop()
        self.patch_supa_set.stop()
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


    def test_extract_conv_details(self):
        fake_conv = {
            "user": {"unique_id": "bestie_user"},
            "streak": {"count": 12},
            "unread_count": 1,
            "last_message": {"create_time": 1700000000},
        }
        details = self.bot._extract_conv_details(fake_conv)
        self.assertEqual(details["username"], "bestie_user")
        self.assertEqual(details["streak_count"], 12)
        self.assertTrue(details["friend_replied"])

    def test_auto_scan_friends_no_cookie(self):
        with patch.object(self.bot, "load_session_cookie_string", return_value=""):
            with patch.object(self.bot, "_get_driver", return_value=None):
                res = self.bot.auto_scan_friends_from_api()
                self.assertFalse(res["success"])
                self.assertIn("Chưa có Cookie", res["reason"])

    def test_auto_scan_friends_from_api_success(self):
        fake_json = {
            "data": {
                "conversations": [
                    {
                        "user": {"unique_id": "tiktok_friend1"},
                        "streak": {"count": 5},
                        "unread_count": 0,
                    },
                    {
                        "user": {"unique_id": "tiktok_friend2"},
                        "streak": {"count": 8},
                        "unread_count": 1,
                    }
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_json

        with patch.object(self.bot, "load_session_cookie_string", return_value="sessionid=fake_token_abc;"):
            with patch("requests.get", return_value=mock_resp):
                res = self.bot.auto_scan_friends_from_api()
                self.assertTrue(res["success"])
                self.assertEqual(res["total_scanned"], 2)
                targets = self.bot.load_targets()
                self.assertEqual(len(targets), 2)
                usernames = [t["username"] for t in targets]
                self.assertIn("tiktok_friend1", usernames)
                self.assertIn("tiktok_friend2", usernames)

    def test_check_streak_status_with_api_direct(self):
        with patch.object(self.bot, "load_session_cookie_string", return_value="sessionid=fake_token;"):
            with patch.object(self.bot, "_check_cloud_tiktok_chat_session", return_value={
                "success": True,
                "found": True,
                "streak_count": 15,
                "is_today": True,
                "friend_replied": True,
            }):
                res = self.bot.check_streak_status("friend_user")
                self.assertTrue(res["checked"])
                self.assertEqual(res["streak_count"], 15)
                self.assertTrue(res["friend_replied"])
                self.assertIn("TikTok API ⚡", res["status_desc"])


    def test_check_session_health_expired(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {"error_code": 13, "name": "session_expired", "description": "session expired, please sign in again"}
        }
        with patch.object(self.bot, "load_session_cookie_string", return_value="sessionid=expired_token;"):
            with patch("requests.get", return_value=mock_resp):
                health = self.bot.check_session_health()
                self.assertTrue(health["expired"])
                self.assertFalse(health["valid"])

    def test_check_session_health_active(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {"user_id": "12345", "username": "active_user", "is_login": True}
        }
        with patch.object(self.bot, "load_session_cookie_string", return_value="sessionid=active_token;"):
            with patch("requests.get", return_value=mock_resp):
                health = self.bot.check_session_health()
                self.assertFalse(health["expired"])
                self.assertTrue(health["valid"])
                self.assertEqual(health["username"], "active_user")


if __name__ == "__main__":
    unittest.main()