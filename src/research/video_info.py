"""
research/video_info.py — Lấy metadata video bằng TikTok Item Detail API kết hợp Fallback Selenium ngầm.
"""
import time
from datetime import datetime
from pathlib import Path
import pandas as pd

from src.config import DEFAULT_MAX_RETRIES, OUTPUT_DIR
from src.research.api_scraper import get_video_detail_api
from src.research.comments import _get_guest_headless_driver
from src.utils.anonymize import _hash
from src.utils.logger import get_logger
from src.utils.validators import extract_video_id, is_valid_video_url

log = get_logger(__name__)


def anonymize_video_info(info: dict) -> dict:
    clean = info.copy()
    for k in ["author_id", "author_unique_id", "author"]:
        if k in clean and clean[k]:
            clean[k] = _hash(str(clean[k]))
    for pii in ["author_name", "avatar", "avatar_thumb", "signature", "bio", "nickname"]:
        clean.pop(pii, None)
    if "create_time" in clean and isinstance(clean["create_time"], (int, float)):
        clean["create_time"] = pd.to_datetime(clean["create_time"], unit="s", utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
    return clean


def _call_selenium_video(url: str) -> dict:
    vid_id = extract_video_id(url)
    driver = _get_guest_headless_driver()
    info = {"video_id": vid_id, "url": url}

    try:
        log.info("[Chạy ngầm] Lấy metadata video: %s", url)
        driver.get(url)
        time.sleep(4)
        from selenium.webdriver.common.by import By
        like_elems = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='like-count']")
        info["like_count"] = like_elems[0].text.strip() if like_elems else "0"
        comm_elems = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='comment-count']")
        info["comment_count"] = comm_elems[0].text.strip() if comm_elems else "0"
        share_elems = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='share-count']")
        info["share_count"] = share_elems[0].text.strip() if share_elems else "0"
        desc_elems = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='browse-video-desc']")
        info["description"] = desc_elems[0].text.strip() if desc_elems else ""
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return info


def fetch_video_info(url: str, max_retries: int = DEFAULT_MAX_RETRIES, status_callback=None) -> dict:
    if not is_valid_video_url(url):
        raise ValueError("URL không hợp lệ")

    vid_id = extract_video_id(url)

    # 1. ƯU TIÊN GỌI TRỰC TIẾP ITEM DETAIL REST API
    try:
        data = get_video_detail_api(vid_id, status_callback=status_callback)
        if data and data.get("like_count") is not None:
            return data
    except Exception as e:
        log.warning("Lỗi API Video, fallback Selenium: %s", e)

    # 2. DỰ PHÒNG CHROME HEADLESS NGẦM
    return _call_selenium_video(url)


def save_video_info(info: dict, output_path: Path | None = None) -> Path:
    anon_info = anonymize_video_info(info)
    vid_id = anon_info.get("video_id", "unknown")
    if output_path is None:
        output_path = OUTPUT_DIR / f"video_{vid_id}.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([anon_info])
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path