"""
tests/test_comments.py
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import pandas as pd

from src.research.comments import fetch_comments, collect_comments


class TestComments(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_path = Path(self.test_dir) / "output.csv"
        self.valid_url = "https://www.tiktok.com/@testuser/video/1234567890123456789"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_fetch_comments_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            fetch_comments("https://invalid-url.com")

    @patch("src.research.comments.fetch_comments_selenium")
    def test_fetch_comments_retry_success(self, mock_call):
        mock_df = pd.DataFrame([{"comment_id": "c1", "text": "hello"}])
        mock_call.side_effect = [Exception("Network error"), mock_df]

        df = fetch_comments(self.valid_url, max_retries=2, backoff_base=1)
        self.assertEqual(len(df), 1)
        self.assertEqual(mock_call.call_count, 2)

    @patch("src.research.comments.fetch_comments_selenium")
    def test_fetch_comments_retry_exhausted_raises(self, mock_call):
        mock_call.side_effect = Exception("Persistent timeout")

        with self.assertRaises(RuntimeError):
            fetch_comments(self.valid_url, max_retries=2, backoff_base=1)
        self.assertEqual(mock_call.call_count, 2)

    @patch("src.research.comments.fetch_comments")
    def test_collect_comments_empty_raw(self, mock_fetch):
        mock_fetch.return_value = pd.DataFrame()
        count = collect_comments(self.valid_url, output_path=self.output_path)
        self.assertEqual(count, 0)
        self.assertFalse(self.output_path.exists())

    @patch("src.research.comments.fetch_comments")
    @patch("src.utils.anonymize.AUTHOR_ID_COLUMNS", ["author_id"])
    @patch("src.storage.csv_writer.COMMENT_ID_COL", "comment_id")
    def test_collect_comments_pipeline_success(self, mock_fetch):
        raw_df = pd.DataFrame([
            {"comment_id": "1", "author_id": "user1", "text": "Nice video!"},
            {"comment_id": "2", "author_id": "user2", "text": "Awesome!"},
        ])
        mock_fetch.return_value = raw_df

        written_count = collect_comments(self.valid_url, output_path=self.output_path)
        self.assertEqual(written_count, 2)
        self.assertTrue(self.output_path.exists())

        result_df = pd.read_csv(self.output_path, dtype=str)
        self.assertEqual(len(result_df), 2)
        self.assertIn("video_id", result_df.columns)
        self.assertIn("collected_at", result_df.columns)


if __name__ == "__main__":
    unittest.main()