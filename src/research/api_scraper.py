"""
research/api_scraper.py — Thu thập TOÀN BỘ dữ liệu TikTok qua Trực tiếp API nội bộ (REST API).
Không cần cuộn trang giả lập chuột:
- Gọi trực tiếp Endpoint API:
    + Comments API: https://www.tiktok.com/api/comment/list/
    + Video Detail API: https://www.tiktok.com/api/item/detail/
    + User Profile API: https://www.tiktok.com/api/user/detail/
- Lấy trọn vẹn: Full text, like, reply count, thời gian, user info, video metrics.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

from src.config import OUTPUT_DIR
from src.utils.anonymize import anonymize
from src.utils.logger import get_logger
from src.utils.validators import extract_video_id, extract_username, is_valid_video_url

log = get_logger(__name__)

# Fake Headers chuẩn trình duyệt Desktop xịn
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def get_all_comments_api(video_id: str, max_count: int = 100, status_callback=None) -> list[dict]:
    """
    Gọi trực tiếp API comment list của TikTok:
    https://www.tiktok.com/api/comment/list/?aweme_id={video_id}&count=50&cursor={cursor}
    Lấy toàn bộ bình luận qua phân trang cursor.
    """
    def notify(msg: str):
        log.info(msg)
        if status_callback:
            status_callback(msg)

    notify(f"🚀 [API] Đang truy vấn TikTok Comment List API cho Video ID: {video_id}...")
    comments = []
    cursor = 0
    has_more = True

    while has_more and len(comments) < max_count:
        api_url = "https://www.tiktok.com/api/comment/list/"
        params = {
            "aweme_id": video_id,
            "count": min(50, max_count - len(comments)),
            "cursor": cursor,
            "aid": "1988",
            "app_language": "vi-VN",
        }

        try:
            res = requests.get(api_url, headers=DEFAULT_HEADERS, params=params, timeout=10)
            if res.status_code != 200:
                notify(f"⚠️ API phản hồi mã lỗi {res.status_code}")
                break

            data = res.json()
            raw_comments = data.get("comments") or []
            if not raw_comments:
                notify("ℹ️ Không còn bình luận nào từ API.")
                break

            for c in raw_comments:
                cid = c.get("cid", "")
                text = c.get("text", "")
                digg_count = c.get("digg_count", 0)
                reply_count = c.get("reply_comment_total", 0)
                create_time = c.get("create_time", 0)
                user_info = c.get("user", {})
                author = user_info.get("unique_id") or user_info.get("uid") or "unknown"

                comments.append({
                    "comment_id": cid,
                    "author_id": author,
                    "text": text,
                    "like_count": digg_count,
                    "reply_count": reply_count,
                    "create_time": create_time,
                })

            cursor = data.get("cursor", 0)
            has_more = bool(data.get("has_more", 0))
            notify(f"📥 [API] Đã lấy {len(comments)} bình luận (cursor: {cursor})...")
            time.sleep(1)

        except Exception as e:
            notify(f"⚠️ Lỗi kết nối API Comments: {e}")
            break

    return comments


def get_video_detail_api(video_id: str, status_callback=None) -> dict:
    """
    Gọi trực tiếp API Item Detail của TikTok:
    https://www.tiktok.com/api/item/detail/?itemId={video_id}
    """
    def notify(msg: str):
        log.info(msg)
        if status_callback:
            status_callback(msg)

    notify(f"🎬 [API] Đang lấy chi tiết Video Metadata (Views, Likes, Sound, Tags)...")
    api_url = "https://www.tiktok.com/api/item/detail/"
    params = {"itemId": video_id, "aid": "1988"}

    try:
        res = requests.get(api_url, headers=DEFAULT_HEADERS, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            item = data.get("itemInfo", {}).get("itemStruct", {})
            if item:
                stats = item.get("stats", {})
                author = item.get("author", {})
                music = item.get("music", {})

                meta = {
                    "video_id": video_id,
                    "author_id": author.get("uniqueId", "unknown"),
                    "description": item.get("desc", ""),
                    "view_count": stats.get("playCount", 0),
                    "like_count": stats.get("diggCount", 0),
                    "comment_count": stats.get("commentCount", 0),
                    "share_count": stats.get("shareCount", 0),
                    "music_title": music.get("title", ""),
                    "create_time": item.get("createTime", 0),
                }
                notify("✅ [API] Lấy thành công trọn bộ Metadata Video!")
                return meta
    except Exception as e:
        notify(f"⚠️ Lỗi kết nối API Video Detail: {e}")

    return {"video_id": video_id}