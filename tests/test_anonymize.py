"""
tests/test_anonymize.py
"""
import unittest
import pandas as pd
from unittest.mock import patch

from src.utils.anonymize import _hash, anonymize


class TestAnonymize(unittest.TestCase):
    def test_hash_consistency_and_one_way(self):
        val = "user_12345"
        h1 = _hash(val, salt="secret1")
        h2 = _hash(val, salt="secret1")
        h3 = _hash(val, salt="secret2")

        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 64)  # SHA-256 hex length
        self.assertNotIn(val, h1)

    def test_anonymize_empty_df(self):
        df = pd.DataFrame()
        res = anonymize(df)
        self.assertTrue(res.empty)

    @patch("src.utils.anonymize.AUTHOR_ID_COLUMNS", ["author_id"])
    @patch("src.utils.anonymize.PII_COLUMNS_TO_DROP", ["avatar_url", "nickname"])
    @patch("src.utils.anonymize.TIMESTAMP_COLUMNS", ["created_time"])
    def test_anonymize_pipeline(self):
        df = pd.DataFrame([
            {
                "comment_id": "c1",
                "author_id": "alice_123",
                "avatar_url": "https://img.tiktok.com/1.jpg",
                "nickname": "Alice In Wonderland",
                "created_time": 1700000000,
                "text": "Hello world!",
            }
        ])

        anon_df = anonymize(df)

        # 1. Author ID băm SHA-256
        self.assertNotEqual(anon_df.loc[0, "author_id"], "alice_123")
        self.assertEqual(len(anon_df.loc[0, "author_id"]), 64)

        # 2. PII cols bị xóa
        self.assertNotIn("avatar_url", anon_df.columns)
        self.assertNotIn("nickname", anon_df.columns)

        # 3. Timestamp convert sang ISO 8601
        self.assertEqual(anon_df.loc[0, "created_time"], "2023-11-14T22:13:20Z")

        # 4. Giữ lại các cột an toàn
        self.assertEqual(anon_df.loc[0, "comment_id"], "c1")
        self.assertEqual(anon_df.loc[0, "text"], "Hello world!")

        # 5. DataFrame gốc không bị mutate
        self.assertEqual(df.loc[0, "author_id"], "alice_123")
        self.assertIn("avatar_url", df.columns)


if __name__ == "__main__":
    unittest.main()
