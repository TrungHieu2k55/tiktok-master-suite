"""
config.py — đọc biến môi trường từ .env, cung cấp hằng số toàn cục.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env nếu tồn tại (bỏ qua nếu không có)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path, override=False)

# --- Anonymization ---
ANON_SALT: str = os.getenv("ANON_SALT", "CHANGE_ME_BEFORE_USE")

# --- Playwright / pyktok ---
TIKTOK_BROWSER: str = os.getenv("TIKTOK_BROWSER", "chrome")

# --- Output ---
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Retry ---
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_BASE: int = 2  # giây, nhân đôi mỗi lần: 2s, 4s, 8s

# --- Pipeline ---
# File thô KHÔNG bao giờ ghi ra đĩa — chỉ DataFrame in-memory
# Thứ tự bắt buộc: fetch → anonymize → dedup → write
