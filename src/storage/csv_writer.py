"""
storage/csv_writer.py — ghi DataFrame đã ẩn danh ra CSV, có deduplication.

Pipeline: anonymize(df) → deduplicate(df, path) → append_csv(df, path)
"""
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)

# TODO: Cập nhật sau khi xác nhận tên cột comment ID thật từ pyktok
COMMENT_ID_COL = "comment_id"  # TODO: xác nhận


def deduplicate(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Lọc bỏ các dòng đã có trong file CSV (dựa theo COMMENT_ID_COL).
    Nếu file chưa tồn tại hoặc không có cột ID → trả về df nguyên.
    """
    if not output_path.exists():
        return df

    try:
        existing = pd.read_csv(output_path, dtype={COMMENT_ID_COL: str})
    except Exception as e:
        log.warning("Không đọc được file cũ '%s': %s — bỏ qua dedup", output_path, e)
        return df

    if COMMENT_ID_COL not in existing.columns:
        log.warning(
            "File '%s' không có cột '%s' — bỏ qua dedup",
            output_path, COMMENT_ID_COL
        )
        return df

    if COMMENT_ID_COL not in df.columns:
        log.warning("DataFrame không có cột '%s' — bỏ qua dedup", COMMENT_ID_COL)
        return df

    seen = set(existing[COMMENT_ID_COL].dropna().astype(str))
    before = len(df)
    df = df[~df[COMMENT_ID_COL].astype(str).isin(seen)].copy()
    log.info("Dedup: bỏ %d dòng trùng, còn %d dòng mới", before - len(df), len(df))
    return df


def append_csv(df: pd.DataFrame, output_path: Path) -> None:
    """
    Ghi (append) DataFrame ra CSV.
    Ghi header chỉ khi file chưa tồn tại.
    Raise nếu df rỗng.
    """
    if df.empty:
        raise ValueError("Không ghi CSV — DataFrame rỗng.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_path.exists()

    df.to_csv(
        output_path,
        mode="a",
        header=write_header,
        index=False,
        encoding="utf-8",
    )
    log.info("Đã ghi %d dòng vào '%s'", len(df), output_path)
