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


if __name__ == "__main__":
    unittest.main()
