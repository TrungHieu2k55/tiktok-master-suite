"""
utils/anonymize.py — ẩn danh hóa DataFrame trước khi ghi ra đĩa.

Pipeline bắt buộc: fetch → anonymize() → dedup → write
File thô KHÔNG bao giờ được ghi ra đĩa.

TODO: Sau khi chạy spike.py và xác nhận tên cột thật,
      điền vào AUTHOR_ID_COLUMNS và PII_COLUMNS_TO_DROP bên dưới.
"""
import hashlib

import pandas as pd

from src.config import ANON_SALT
from src.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# TODO: Cập nhật 2 danh sách này sau khi chạy spike.py
# và xác nhận df.columns thật từ pyktok.
# ---------------------------------------------------------------------------

# Cột chứa ID/username tác giả — sẽ bị băm SHA-256
AUTHOR_ID_COLUMNS: list[str] = [
    # "uniqueId",   # TODO: xác nhận
    # "uid",        # TODO: xác nhận
]

# Cột chứa PII không cần thiết — sẽ bị xóa hoàn toàn
PII_COLUMNS_TO_DROP: list[str] = [
    # "avatarThumb",  # TODO: xác nhận
    # "signature",    # TODO: xác nhận
]

# Cột timestamp Unix → ISO 8601
# TODO: xác nhận tên cột thật
TIMESTAMP_COLUMNS: list[str] = [
    # "createTime",  # TODO: xác nhận
]

# ---------------------------------------------------------------------------


def _hash(value: str, salt: str = ANON_SALT) -> str:
    """
    Băm SHA-256 với salt.
    Nhất quán (cùng input → cùng hash) nhưng không thể đảo ngược.
    """
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()


def anonymize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ẩn danh hóa DataFrame in-memory.
    Trả về DataFrame mới — không sửa input gốc.

    Thứ tự:
      1. Băm các cột ID tác giả
      2. Xóa các cột PII thừa
      3. Chuyển timestamp Unix → ISO 8601
    """
    if df.empty:
        return df

    df = df.copy()

    # 1. Băm ID tác giả
    for col in AUTHOR_ID_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(str).map(_hash)
            log.debug("Đã băm cột: %s", col)
        else:
            log.warning("Cột '%s' không có trong DataFrame — bỏ qua băm", col)

    # 2. Xóa PII thừa
    to_drop = [c for c in PII_COLUMNS_TO_DROP if c in df.columns]
    if to_drop:
        df = df.drop(columns=to_drop)
        log.debug("Đã xóa cột PII: %s", to_drop)

    # 3. Timestamp Unix → ISO 8601
    for col in TIMESTAMP_COLUMNS:
        if col in df.columns:
            df[col] = (
                pd.to_datetime(df[col], unit="s", utc=True)
                .dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            log.debug("Đã chuyển timestamp: %s", col)

    return df
