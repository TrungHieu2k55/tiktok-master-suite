"""
tests/test_csv_writer.py
"""
import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
from unittest.mock import patch

from src.storage.csv_writer import append_csv, deduplicate


class TestCsvWriter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_path = Path(self.test_dir) / "test_comments.csv"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_append_csv_new_file(self):
        df = pd.DataFrame([{"comment_id": "1", "text": "Comment 1"}])
        append_csv(df, self.output_path)

        self.assertTrue(self.output_path.exists())
        saved = pd.read_csv(self.output_path, dtype=str)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved.loc[0, "comment_id"], "1")
        self.assertEqual(saved.loc[0, "text"], "Comment 1")

    def test_append_csv_existing_file(self):
        df1 = pd.DataFrame([{"comment_id": "1", "text": "Comment 1"}])
        append_csv(df1, self.output_path)

        df2 = pd.DataFrame([{"comment_id": "2", "text": "Comment 2"}])
        append_csv(df2, self.output_path)

        saved = pd.read_csv(self.output_path, dtype=str)
        self.assertEqual(len(saved), 2)
        self.assertListEqual(saved["comment_id"].tolist(), ["1", "2"])

    def test_append_csv_empty_dataframe_raises(self):
        df = pd.DataFrame()
        with self.assertRaises(ValueError):
            append_csv(df, self.output_path)

    @patch("src.storage.csv_writer.COMMENT_ID_COL", "comment_id")
    def test_deduplicate(self):
        df_old = pd.DataFrame([
            {"comment_id": "1", "text": "Comment 1"},
            {"comment_id": "2", "text": "Comment 2"},
        ])
        append_csv(df_old, self.output_path)

        df_incoming = pd.DataFrame([
            {"comment_id": "2", "text": "Comment 2 (duplicate)"},
            {"comment_id": "3", "text": "Comment 3 (new)"},
        ])

        df_filtered = deduplicate(df_incoming, self.output_path)
        self.assertEqual(len(df_filtered), 1)
        self.assertEqual(df_filtered.iloc[0]["comment_id"], "3")


if __name__ == "__main__":
    unittest.main()
