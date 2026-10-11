"""
research/creator_analytics.py — Phân tích toàn diện kênh Creator TikTok:
1. Thông tin kênh: Followers, Likes, Bio, Category.
2. Trạng thái E-commerce: Có gắn giỏ hàng TikTok Shop / Affiliate hay không.
3. Trạng thái Livestream: Đang Live hay không, mắt xem hiện tại, Stream Room ID.
4. Danh sách Video gần nhất: Tổng view, tỷ lệ tương tác (Engagement Rate).
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import OUTPUT_DIR
from src.research.api_scraper import DEFAULT_HEADERS
from src.utils.logger import get_logger
from src.utils.validators import extract_username

log = get_logger(__name__)


def fetch_creator_full_profile(username: str, status_callback=None) -> dict:
    """
    Trích xuất toàn diện thông tin Creator bằng cách cào SSR Hydration Data của TikTok Profile.
    Phương pháp này chuẩn theo cách làm của Evil0ctal & silencoo:
    TikTok nhúng toàn bộ state người dùng vào thẻ script `__UNIVERSAL_DATA_FOR_REHYDRATION__`.
    """
    def notify(msg: str):
        log.info(msg)
        if status_callback:
            status_callback(msg)

    clean_user = username.strip().replace("@", "")
    profile_url = f"https://www.tiktok.com/@{clean_user}"
    notify(f"🔍 Đang quét profile Creator: @{clean_user}...")

    result = {
        "username": clean_user,
        "nickname": clean_user,
        "sec_uid": "",
        "uid": "",
        "followers": 0,
        "following": 0,
        "total_likes": 0,
        "video_count": 0,
        "bio": "",
        "is_verified": False,
        "has_shop": False,         # Có gắn giỏ hàng TikTok Shop / Showcase không
        "is_live": False,          # Có đang Livestream không
        "live_room_id": "",
        "live_viewers": 0,
        "bio_links": [],
        "recent_videos": [],
    }

    try:
        res = requests.get(profile_url, headers=DEFAULT_HEADERS, timeout=12)
        if res.status_code != 200:
            notify(f"⚠️ Không truy cập được profile @{clean_user} (Status {res.status_code})")
            return result

        soup = BeautifulSoup(res.text, "html.parser")

        # 1. Tìm thẻ script chứa State Rehydration Data
        script_data = None
        for script_id in ["__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE"]:
            tag = soup.find("script", id=script_id)
            if tag and tag.string:
                try:
                    script_data = json.loads(tag.string)
                    break
                except Exception:
                    continue

        if script_data:
            notify("✅ Tìm thấy SSR Data của TikTok! Đang bóc tách thông số...")
            # Cấu trúc webApp.user-page
            user_page = script_data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
            user_info = user_page.get("userInfo", {}).get("user", {})
            user_stats = user_page.get("userInfo", {}).get("stats", {})

            if user_info:
                result["nickname"] = user_info.get("nickname", clean_user)
                result["sec_uid"] = user_info.get("secUid", "")
                result["uid"] = user_info.get("id", "")
                result["bio"] = user_info.get("signature", "")
                result["is_verified"] = user_info.get("verified", False)
                result["bio_links"] = [user_info.get("bioLink", {}).get("link", "")]

                # Kiểm tra TikTok Shop / E-commerce Flag
                # Các cờ thường thấy: commerceUserInfo, tabType, shop/showcase
                commerce_info = user_info.get("commerceUserInfo", {})
                result["has_shop"] = bool(commerce_info.get("commerceUser", False) or "shop" in str(user_info).lower())

            if user_stats:
                result["followers"] = user_stats.get("followerCount", 0)
                result["following"] = user_stats.get("followingCount", 0)
                result["total_likes"] = user_stats.get("heartCount", 0)
                result["video_count"] = user_stats.get("videoCount", 0)

            # Kiểm tra trạng thái Livestream (Live Room)
            live_info = user_page.get("liveRoom", {}) or user_info.get("liveRoom", {})
            if live_info and live_info.get("liveId"):
                result["is_live"] = True
                result["live_room_id"] = str(live_info.get("liveId", ""))
                result["live_viewers"] = live_info.get("liveUserCount", 0)
                notify(f"🔴 Creator @{clean_user} ĐANG LIVESTREAM! Mắt xem: {result['live_viewers']:,}")

            # 2. Bóc tách danh sách Video gần nhất của kênh
            item_list = script_data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("itemList", [])
            for it in item_list:
                stats = it.get("stats", {})
                result["recent_videos"].append({
                    "video_id": it.get("id"),
                    "desc": it.get("desc", ""),
                    "views": stats.get("playCount", 0),
                    "likes": stats.get("diggCount", 0),
                    "comments": stats.get("commentCount", 0),
                    "shares": stats.get("shareCount", 0),
                    "create_time": it.get("createTime", 0),
                })
        else:
            notify("ℹ️ Không bóc tách được SSR script, fallback sang regex HTML...")
            # Fallback regex
            followers_match = re.search(r'"followerCount":(\d+)', res.text)
            if followers_match:
                result["followers"] = int(followers_match.group(1))
            likes_match = re.search(r'"heartCount":(\d+)', res.text)
            if likes_match:
                result["total_likes"] = int(likes_match.group(1))

        notify(f"🎉 Hoàn tất phân tích @{clean_user}: {result['followers']:,} Followers, Shop: {result['has_shop']}, Live: {result['is_live']}")
    except Exception as e:
        notify(f"⚠️ Lỗi quét profile @{clean_user}: {e}")

    return result


def save_creator_report(profile_data: dict) -> Path:
    """Lưu báo cáo phân tích Creator thành CSV/JSON."""
    username = profile_data.get("username", "creator")
    out_path = OUTPUT_DIR / f"creator_{username}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)
    return out_path