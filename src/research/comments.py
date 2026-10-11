"""
research/comments.py — Thu thập bình luận TikTok kết hợp song song:
1. Trực tiếp qua REST API nội bộ của TikTok (nhanh, sạch, lấy trọn bộ).
2. Fallback sang Selenium Headless Ẩn danh (nếu TikTok bắt giải captcha signature).
"""
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from src.config import DEFAULT_BACKOFF_BASE, DEFAULT_MAX_RETRIES, OUTPUT_DIR
from src.research.api_scraper import get_all_comments_api
from src.storage.csv_writer import append_csv, deduplicate
from src.utils.anonymize import anonymize
from src.utils.logger import get_logger
from src.utils.validators import extract_video_id, is_valid_video_url

log = get_logger(__name__)


def _get_guest_headless_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--incognito")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


def fetch_comments_selenium(url: str, max_scrolls: int = 4, status_callback=None) -> pd.DataFrame:
    def notify(msg: str):
        log.info(msg)
        if status_callback:
            status_callback(msg)

    notify("🕶️ [Fallback] Đang khởi động Chrome ngầm để quét...")
    driver = None
    comments_data = []

    try:
        driver = _get_guest_headless_driver()
        driver.get(url)
        time.sleep(4)

        for s in range(max_scrolls):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)

        comment_selectors = [
            "[data-e2e='comment-level-1']",
            "div[class*='CommentItemContainer']",
            "div[class*='comment-item']",
        ]
        comment_items = []
        for sel in comment_selectors:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found:
                comment_items = found
                break

        for idx, item in enumerate(comment_items):
            try:
                text_elems = item.find_elements(By.CSS_SELECTOR, "[data-e2e='comment-level-1-text'], p[class*='CommentText']")
                text = text_elems[0].text.strip() if text_elems else ""
                user_elems = item.find_elements(By.CSS_SELECTOR, "[data-e2e='comment-username-1'], a[class*='UserLink']")
                author = user_elems[0].text.strip() if user_elems else f"user_{idx}"
                like_elems = item.find_elements(By.CSS_SELECTOR, "[data-e2e='comment-like-count']")
                likes = like_elems[0].text.strip() if like_elems else "0"

                if text:
                    comments_data.append({
                        "comment_id": f"c_{extract_video_id(url)}_{idx}",
                        "author_id": author,
                        "text": text,
                        "like_count": likes,
                        "create_time": int(time.time()),
                    })
            except Exception:
                continue
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return pd.DataFrame(comments_data)


def fetch_comments(
    url: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: int = DEFAULT_BACKOFF_BASE,
    status_callback=None,
) -> pd.DataFrame:
    if not is_valid_video_url(url):
        raise ValueError(f"URL không hợp lệ: {url!r}")

    vid_id = extract_video_id(url)

    # 1. Thử gọi trực tiếp REST API TikTok
    try:
        api_results = get_all_comments_api(vid_id, max_count=200, status_callback=status_callback)
        if api_results:
            return pd.DataFrame(api_results)
    except Exception:
        pass

    # 2. Thử Fallback qua Selenium ngầm với Retry
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            df_selenium = fetch_comments_selenium(url, status_callback=status_callback)
            if not df_selenium.empty:
                return df_selenium
            time.sleep(1)
        except Exception as e:
            last_err = e
            if attempt == max_retries:
                raise RuntimeError(f"Không lấy được bình luận sau {max_retries} lần thử") from last_err
            time.sleep(1)

    return pd.DataFrame()


def collect_comments(
    url: str,
    output_path: Path | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    status_callback=None,
) -> int:
    video_id = extract_video_id(url)
    if output_path is None:
        output_path = OUTPUT_DIR / f"comments_{video_id}.csv"

    df_raw = fetch_comments(url, max_retries=max_retries, status_callback=status_callback)
    if df_raw is None or df_raw.empty:
        return 0

    df_raw["collected_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    df_raw["video_id"] = video_id

    df_anon = anonymize(df_raw)
    df_new = deduplicate(df_anon, output_path)
    if df_new.empty:
        return 0

    append_csv(df_new, output_path)
    return len(df_new)