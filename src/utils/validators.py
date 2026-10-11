"""
utils/validators.py — validate input trước khi chạy pipeline.
"""
import re

_TIKTOK_VIDEO_RE = re.compile(
    r"https?://(www\.)?tiktok\.com/@[\w.]+/video/\d+"
)

_TIKTOK_USER_RE = re.compile(
    r"https?://(www\.)?tiktok\.com/@[\w.]+"
)


def is_valid_video_url(url: str) -> bool:
    """Kiểm tra URL đúng định dạng video TikTok công khai."""
    return bool(_TIKTOK_VIDEO_RE.match(url.strip()))


def is_valid_user_url(url: str) -> bool:
    """Kiểm tra URL đúng định dạng profile TikTok."""
    return bool(_TIKTOK_USER_RE.match(url.strip()))


def extract_video_id(url: str) -> str:
    """
    Lấy video ID từ URL.
    Raise ValueError nếu không tìm thấy.
    """
    match = re.search(r"/video/(\d+)", url)
    if not match:
        raise ValueError(f"Không tìm thấy video ID trong URL: {url!r}")
    return match.group(1)


def extract_username(url: str) -> str:
    """
    Lấy username từ URL TikTok (bỏ @).
    Raise ValueError nếu không tìm thấy.
    """
    match = re.search(r"tiktok\.com/@([\w.]+)", url)
    if not match:
        raise ValueError(f"Không tìm thấy username trong URL: {url!r}")
    return match.group(1)
