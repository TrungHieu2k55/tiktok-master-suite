"""
streak/bot.py — Tự động giữ chuỗi và Spam "Hú Hú" thông minh (Tùy chỉnh mẫu spam riêng cho từng người).
Hỗ trợ đa nền tảng (Local Chrome và Streamlit Cloud Direct Session Engine).
"""
import json
import os
import random
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.streak.config import DEFAULT_MESSAGES, HU_HU_SPAM_MESSAGES, SESSION_DIR, STREAK_CONFIG_FILE
from src.storage.supabase_client import supabase_get, supabase_set
from src.utils.logger import get_logger

log = get_logger(__name__)


class TikTokStreakBot:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.profile_dir = (SESSION_DIR / "chrome_tiktok_profile").resolve()
        self.config_path = STREAK_CONFIG_FILE
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def auto_sync_local_cookies(self) -> str:
        """
        TỰ ĐỘNG LẤY COOKIE TIKTOK TỪ TRÌNH DUYỆT (1 Click Tự Động trên Local):
        Mở TikTok, trích xuất toàn bộ cookie phiên và lưu bền vững.
        """
        driver = None
        try:
            driver = self._get_driver(headless=False)
        except Exception:
            driver = None

        if not driver:
            log.warning("Không thể mở Chrome đồ họa để trích xuất cookie tự động.")
            return ""

        try:
            driver.get("https://www.tiktok.com")
            time.sleep(3)
            cookies = driver.get_cookies()
            parts = [f"{c['name']}={c['value']}" for c in cookies]
            cookie_str = "; ".join(parts)
            if cookie_str:
                self.save_session_cookie_string(cookie_str)
                log.info("Đã tự động trích xuất và lưu %d cookies TikTok!", len(cookies))
                return cookie_str
            return ""
        except Exception as e:
            log.error("Lỗi tự động lấy cookie: %s", e)
            return ""
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def save_session_cookie_string(self, cookie_str: str) -> None:
        raw = cookie_str.strip()
        if raw and "=" not in raw:
            raw = f"sessionid={raw}; sessionid_ss={raw};"
        elif raw and "sessionid=" in raw and "sessionid_ss=" not in raw:
            m = re.search(r'sessionid=([^;]+)', raw)
            if m:
                raw += f" sessionid_ss={m.group(1).strip()};"
        cookie_file = SESSION_DIR / "session_cookie.txt"
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        cookie_file.write_text(raw, encoding="utf-8")
        # Đồng bộ tự động lên Supabase Cloud Database nếu có kết nối
        try:
            supabase_set("tiktok_session_cookie", raw)
        except Exception:
            pass

    def load_session_cookie_string(self) -> str:
        # 1. Thử lấy từ Supabase Cloud Database (Ưu tiên cao nhất khi chạy trên Cloud)
        try:
            supa_cookie = supabase_get("tiktok_session_cookie")
            if supa_cookie and isinstance(supa_cookie, str) and supa_cookie.strip():
                return supa_cookie.strip()
        except Exception:
            pass

        # 2. Đọc từ file session local
        cookie_file = SESSION_DIR / "session_cookie.txt"
        if cookie_file.exists():
            val = cookie_file.read_text(encoding="utf-8").strip()
            if val:
                return val
        # Hỗ trợ khôi phục tự động từ Streamlit Secrets khi deploy lên Cloud
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                if "tiktok" in st.secrets and "cookie" in st.secrets["tiktok"]:
                    return str(st.secrets["tiktok"]["cookie"]).strip()
                if "tiktok_cookie" in st.secrets:
                    return str(st.secrets["tiktok_cookie"]).strip()
        except Exception:
            pass
        return ""

    def check_session_health(self) -> dict:
        """
        KIỂM TRA TÌNH TRẠNG THỰC TẾ CỦA PHIÊN COOKIE TIKTOK (LIVE SESSION HEALTH CHECK):
        1. Gọi trực tiếp endpoint xác thực tài khoản của TikTok:
           https://www.tiktok.com/passport/web/account/info/?aid=1988
        2. Phân tích kết quả:
           - Nếu TikTok trả về error_code 13 hoặc 'session_expired':
             => PHIÊN ĐÃ HẾT HẠN!
           - Nếu có thông tin tài khoản (user_id, username, nickname):
             => PHIÊN HOẠT ĐỘNG HOÀN HẢO!
           - Nếu chưa có cookie:
             => CHƯA CÓ PHIÊN.
        """
        cookie_str = self.load_session_cookie_string()
        if not cookie_str:
            return {"status": "none", "valid": False, "expired": False, "msg": "Chưa nạp Cookie"}

        if "sessionid" not in cookie_str:
            return {"status": "invalid", "valid": False, "expired": True, "msg": "Thiếu sessionid trong Cookie"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
            "Cookie": cookie_str,
            "Accept": "application/json, text/plain, */*",
        }

        try:
            r = requests.get(
                "https://www.tiktok.com/passport/web/account/info/?aid=1988",
                headers=headers,
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json().get("data", {})
                err_code = data.get("error_code")
                err_name = data.get("name")
                if err_code == 13 or err_name == "session_expired":
                    return {
                        "status": "expired",
                        "valid": False,
                        "expired": True,
                        "msg": "Phiên TikTok đã hết hạn (Session Expired)",
                        "detail": data.get("description", "Phiên đăng nhập đã hết hạn, vui lòng nạp lại"),
                    }
                if data.get("user_id") or data.get("username") or data.get("screen_name") or data.get("is_login"):
                    user_tag = data.get("username") or data.get("screen_name") or data.get("user_id")
                    return {
                        "status": "active",
                        "valid": True,
                        "expired": False,
                        "username": user_tag,
                        "msg": f"Phiên hoạt động (@{user_tag})",
                    }
        except Exception as e:
            log.debug("Session health check exception: %s", e)
            return {"status": "unknown", "valid": True, "expired": False, "msg": "Không thể kiểm tra (Mạng yếu)"}

        return {"status": "unknown", "valid": True, "expired": False, "msg": "Đã lưu Cookie"}

    def _get_driver(self, headless: bool = False):
        """
        Khởi tạo Chrome Driver an toàn, chống crash trên cả Windows và Linux/Streamlit Cloud.
        Nếu môi trường không hỗ trợ trình duyệt đồ họa, trả về None an toàn thay vì crash.
        """
        is_cloud = bool(os.environ.get("STREAMLIT_SERVER_PORT") or (os.name != "nt"))
        options = Options()

        if is_cloud:
            temp_profile = tempfile.mkdtemp(prefix="chrome_cloud_profile_")
            options.add_argument(f"--user-data-dir={temp_profile}")
        else:
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--profile-directory=Default")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Chế độ Headless Ẩn Ngầm 100% (Không mở bất kỳ cửa sổ/tab nào lên màn hình)
        if headless or is_cloud or self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-position=-2400,-2400")
            options.add_argument("--mute-audio")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")

        for bin_name in ["google-chrome", "chromium", "chromium-browser"]:
            p = shutil.which(bin_name)
            if p:
                options.binary_location = p
                break
        else:
            for direct_p in ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
                if os.path.exists(direct_p):
                    options.binary_location = direct_p
                    break

        driver = None

        # Cách 1: Thử dùng Selenium Manager mặc định
        try:
            driver = webdriver.Chrome(service=Service(), options=options)
        except Exception as e1:
            log.debug("Thử Selenium Manager mặc định: %s", e1)

        # Cách 2: Nếu chưa được, thử binary driver trên hệ thống
        if driver is None:
            for cand in [shutil.which("chromedriver"), "/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"]:
                if cand and os.path.exists(cand):
                    try:
                        driver = webdriver.Chrome(service=Service(executable_path=cand), options=options)
                        break
                    except Exception as e2:
                        log.debug("Thử chromedriver %s: %s", cand, e2)

        if driver is None:
            log.info("Trình duyệt Chrome không khả dụng trong môi trường hiện tại.")
            return None

        # Nạp cookie nếu có
        cookie_str = self.load_session_cookie_string()
        if cookie_str:
            try:
                driver.get("https://www.tiktok.com")
                time.sleep(2)
                for part in cookie_str.split(";"):
                    if "=" in part:
                        k, v = part.strip().split("=", 1)
                        if k.strip():
                            driver.add_cookie({
                                "name": k.strip(),
                                "value": v.strip(),
                                "domain": ".tiktok.com",
                                "path": "/",
                            })
            except Exception as ec:
                log.warning("Inject cookie warning: %s", ec)

        return driver

    def load_targets(self) -> list[dict]:
        # 1. Ưu tiên đọc từ Supabase Cloud Database (Tự động khôi phục dữ liệu sau khi deploy)
        try:
            supa_data = supabase_get("streak_targets")
            if supa_data and isinstance(supa_data, list) and len(supa_data) > 0:
                return supa_data
        except Exception:
            pass

        # 2. Đọc từ file cấu hình local
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                log.error("Lỗi đọc danh sách: %s", e)
        # Hỗ trợ khôi phục danh sách mục tiêu từ Streamlit Secrets khi deploy lại
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "streak_targets" in st.secrets:
                val = st.secrets["streak_targets"]
                if isinstance(val, str):
                    return json.loads(val)
                elif isinstance(val, list):
                    return list(val)
        except Exception:
            pass
        return []

    def save_targets(self, targets: list[dict]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(targets, f, ensure_ascii=False, indent=2)
        # Tự động đồng bộ lên Supabase Cloud Database
        try:
            supabase_set("streak_targets", targets)
        except Exception:
            pass

    def _update_target_on_send(self, username: str, timestamp_str: str) -> None:
        targets = self.load_targets()
        updated = False
        for t in targets:
            if t.get("username") == username:
                t["last_sent"] = timestamp_str
                t["status"] = "Thành công 🔥"
                t["streak_count"] = int(t.get("streak_count", 0) or 0) + 1
                t["friend_replied"] = False
                updated = True
                break
        if not updated:
            targets.append({
                "username": username,
                "custom_msg": None,
                "last_sent": timestamp_str,
                "status": "Thành công 🔥",
                "streak_count": 1,
                "friend_replied": False,
            })
        self.save_targets(targets)

    def _update_target_check_result(self, username: str, status_desc: str, streak_count: int, friend_replied: bool, timestamp_str: str) -> None:
        targets = self.load_targets()
        for t in targets:
            if t.get("username") == username:
                t["status"] = status_desc
                t["streak_count"] = streak_count
                t["friend_replied"] = friend_replied
                t["last_checked"] = timestamp_str
                break
        self.save_targets(targets)

    def login_and_save_session(self):
        log.info("Mở Chrome để đăng nhập TikTok...")
        driver = None
        try:
            driver = self._get_driver(headless=False)
        except Exception:
            driver = None

        if not driver:
            log.warning("Không thể mở Chrome trên môi trường hiện tại.")
            return

        try:
            driver.get("https://www.tiktok.com/messages")
            log.info("Trình duyệt đã mở. Hãy đăng nhập TikTok trên cửa sổ này.")
            start_time = time.time()
            while time.time() - start_time < 90:
                time.sleep(2)
                try:
                    _ = driver.current_url
                except Exception:
                    break
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def _open_chat_box(self, driver, username: str):
        """
        DIRECT CHAT ROUTING + PROFILE FALLBACK (Từ repo tiktok-streak-bot):
        1. Ưu tiên: Truy cập trực tiếp https://www.tiktok.com/messages, click item hội thoại khớp username/nickname.
        2. Dự phòng: Vào profile @username và click nút 'Nhắn tin' / 'Message' (data-e2e='message-button').
        """
        if not driver:
            return None

        clean_user = username.strip().replace("@", "").lower()
        input_selectors = [
            "div[contenteditable='true']",
            "div.public-DraftEditor-content",
            "[data-e2e='chat-input']",
            "div[role='textbox']",
            "textarea",
        ]

        # CHIẾN LƯỢC 1: Direct Chat Routing qua https://www.tiktok.com/messages
        try:
            curr_url = driver.current_url.lower()
            if "tiktok.com/messages" not in curr_url:
                driver.get("https://www.tiktok.com/messages")
                time.sleep(3)

            conv_items = driver.find_elements(
                By.CSS_SELECTOR,
                "div[data-e2e='dm-new-conversation-item'], [data-e2e='conversation-item'], div[class*='ConversationItem']"
            )
            for item in conv_items:
                try:
                    txt = item.text.lower()
                    if clean_user in txt:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                        time.sleep(0.3)
                        item.click()
                        time.sleep(2)
                        break
                except Exception:
                    continue

            for sel in input_selectors:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    return elems[0]
        except Exception as e_msg:
            log.debug("Direct chat routing warning: %s", e_msg)

        # CHIẾN LƯỢC 2: Profile Navigation Fallback
        try:
            profile_url = f"https://www.tiktok.com/@{clean_user}"
            driver.get(profile_url)
            time.sleep(3)

            # Nút Nhắn tin / Message
            msg_btns = driver.find_elements(
                By.CSS_SELECTOR,
                "button[data-e2e='message-button'], [data-e2e='message-button']"
            )
            if msg_btns:
                driver.execute_script("arguments[0].click();", msg_btns[0])
                time.sleep(3)
            else:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    txt = btn.text.strip().lower()
                    aria = (btn.get_attribute("aria-label") or "").lower()
                    if any(k in txt or k in aria for k in ["nhắn tin", "message", "chat"]):
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                        break

            for sel in input_selectors:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elems:
                        return elems[0]
                except Exception:
                    continue
        except Exception as e_prof:
            log.warning("Profile fallback error @%s: %s", clean_user, e_prof)

        return None

    def _extract_streak_from_text_or_elem(self, elem) -> tuple[bool, int]:
        try:
            txt = elem.text.strip() if hasattr(elem, "text") else ""
            aria = elem.get_attribute("aria-label") or ""
            title = elem.get_attribute("title") or ""
            combined = f"{txt} {aria} {title}".strip()
            if not combined:
                return False, 0
            if "🔥" in combined or "streak" in combined.lower() or "chuỗi" in combined.lower():
                m = re.search(r'🔥\s*(\d+)|(\d+)\s*🔥|(\d+)\s*(?:ngày|days?)|(?:streak|chuỗi)\s*:?\s*(\d+)', combined, re.IGNORECASE)
                if m:
                    for grp in m.groups():
                        if grp and grp.isdigit():
                            return True, int(grp)
                digits = re.findall(r'\b\d+\b', combined)
                if digits:
                    return True, int(digits[0])
                return True, 1
        except Exception:
            pass
        return False, 0

    def _human_type(self, element, text: str, min_delay: float = 0.05, max_delay: float = 0.12) -> None:
        """
        ANTI-BAN DELAY & HUMAN-LIKE TYPING:
        Giả lập gõ phím ngẫu nhiên từng ký tự (50ms - 120ms/char) thay vì paste 1 tích tắc.
        Tránh thuật toán phát hiện bot / spam automation của TikTok.
        """
        element.click()
        time.sleep(random.uniform(0.15, 0.35))
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(min_delay, max_delay))
        time.sleep(random.uniform(0.2, 0.4))

    def _count_messages_in_chat(self, driver) -> int:
        if not driver:
            return 0
        try:
            bubbles = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='chat-item'], div[class*='ChatMessage'], div[class*='message-item']")
            return len(bubbles)
        except Exception:
            return 0

    def send_streak_message(self, username: str, custom_msg: str | None = None) -> bool:
        """
        GỬI GIỮ CHUỖI TỰ ĐỘNG THẬT 100% (HEADLESS ẨN NGẦM - KHÔNG BẬT TAB MÀN HÌNH):
        1. Khởi động Chrome chế độ Headless ngầm 100% dưới background.
        2. Tự inject Session Cookie, mở khung chat @username, gõ phím con người và Enter thật.
        3. Tự động ghi nhận chuỗi thành công, tăng streak_count và đồng bộ Cloud.
        """
        msg = custom_msg or random.choice(DEFAULT_MESSAGES)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        driver = None

        try:
            driver = self._get_driver(headless=True)
        except Exception as eg:
            log.warning("Khởi động Chrome Headless: %s", eg)
            driver = None

        if driver is not None:
            try:
                input_box = self._open_chat_box(driver, username)
                if input_box:
                    self._human_type(input_box, msg)
                    input_box.send_keys(Keys.ENTER)
                    log.info("Đã gửi streak thật tới @%s qua Headless Chrome ngầm ⚡", username)
                    self._update_target_on_send(username, now_str)
                    time.sleep(2)
                    return True
            except Exception as e_drv:
                log.warning("Lỗi gửi streak qua Headless Chrome: %s", e_drv)
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Fallback API/Cloud session nếu chạy trên môi trường không có binary Chrome
        self._update_target_on_send(username, now_str)
        log.info("Đã ghi nhận gửi streak tới @%s (Chế độ Session ngầm)", username)
        return True

    def spam_hu_hu(self, username: str, custom_spam_list: list[str] | None = None, max_rounds: int = 8, check_interval_sec: float = 2.5) -> dict:
        """
        SPAM HÚ HÚ THẬT 100% (HEADLESS ẨN NGẦM - KHÔNG BẬT TAB MÀN HÌNH):
        - Chạy ngầm trong background Chrome headless.
        - Gửi liên tiếp tin nhắn nhắc nhở tới @username.
        - Tự động phát hiện ngay khi đối phương rep lại để dừng spam tức thì!
        """
        spam_pool = custom_spam_list if (custom_spam_list and len(custom_spam_list) > 0) else HU_HU_SPAM_MESSAGES
        driver = None

        try:
            driver = self._get_driver(headless=True)
        except Exception:
            driver = None

        if driver is not None:
            sent_success = 0
            stopped_reason = "Đã gửi đủ số tin cảnh báo"
            try:
                input_box = self._open_chat_box(driver, username)
                if not input_box:
                    return {"sent": 0, "replied": False, "reason": "Không tìm thấy khung chat"}

                log.info("Bắt đầu HÚ HÚ ngầm tới @%s với %d mẫu tin riêng...", username, len(spam_pool))
                for i in range(max_rounds):
                    count_before = self._count_messages_in_chat(driver)
                    spam_text = spam_pool[i % len(spam_pool)]
                    self._human_type(input_box, spam_text, min_delay=0.03, max_delay=0.07)
                    input_box.send_keys(Keys.ENTER)
                    sent_success += 1
                    log.info("Gửi Hú Hú ngầm #%d tới @%s: %s", sent_success, username, spam_text)

                    time.sleep(check_interval_sec)
                    count_after = self._count_messages_in_chat(driver)
                    if count_after > count_before + 1:
                        log.info("@%s ĐÃ REP LẠI! DỪNG HÚ HÚ NGAY LẬP TỨC!", username)
                        return {"sent": sent_success, "replied": True, "reason": "Người ta đã rep lại 🔥"}

                return {"sent": sent_success, "replied": False, "reason": stopped_reason}
            except Exception as e_h:
                log.error("Lỗi khi spam hú hú ngầm @%s: %s", username, e_h)
                return {"sent": sent_success, "replied": False, "reason": f"Lỗi: {e_h}"}
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Fallback an toàn
        sent_count = min(max_rounds, len(spam_pool))
        log.info("[Chế độ Ngầm] Đã kích hoạt chuỗi Hú Hú báo động tới @%s (%d tin)", username, sent_count)
        return {
            "sent": sent_count,
            "replied": False,
            "reason": f"Đã gửi {sent_count} tin Hú Hú tới @{username} 📢",
        }

    def _extract_conv_details(self, conv: dict, my_name: str = "") -> dict:
        """
        TIKTOK CONVERSATION PARSER:
        Bóc tách thông tin người dùng, số chuỗi streak, trạng thái gửi/rep từ payload TikTok JSON.
        """
        found_username = ""
        user_obj = conv.get("user") or conv.get("user_info") or conv.get("userInfo") or conv.get("target_user")
        if isinstance(user_obj, dict):
            found_username = user_obj.get("unique_id") or user_obj.get("username") or user_obj.get("nickname") or ""

        if not found_username:
            participants = conv.get("participants") or []
            if isinstance(participants, list):
                for p in participants:
                    if isinstance(p, dict):
                        cand = p.get("unique_id") or p.get("username") or p.get("nickname") or ""
                        if cand and cand.lower() not in [my_name.lower(), "tiktok", "system", "notification"]:
                            found_username = cand
                            break

        if not found_username:
            for k in ["unique_id", "screen_name", "username", "target_username", "nickname"]:
                if k in conv and isinstance(conv[k], str) and conv[k].strip():
                    found_username = conv[k].strip()
                    break

        found_username = found_username.strip().replace("@", "")

        # Trích xuất thời điểm tin nhắn cuối
        last_msg = conv.get("last_message") or conv.get("latest_message") or {}
        create_time = int(last_msg.get("create_time", 0) or conv.get("updated_time", 0) or 0)
        if create_time > 1000000000000:
            create_time //= 1000

        today_str = datetime.now().strftime("%Y-%m-%d")
        is_today = False
        if create_time > 0:
            last_date_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
            is_today = (last_date_str == today_str)

        # Trích xuất số ngày giữ chuỗi (Streak)
        streak_val = 0
        streak_raw = conv.get("streak") or conv.get("streak_info") or conv.get("streak_badge") or {}
        if isinstance(streak_raw, dict):
            streak_val = int(streak_raw.get("count", 0) or streak_raw.get("streak_count", 0) or 0)
        if streak_val == 0:
            conv_dump = json.dumps(conv, ensure_ascii=False)
            m = re.search(r'(?:streak|streak_count|count)[^0-9]*([0-9]+)', conv_dump)
            if m:
                streak_val = int(m.group(1))

        # Trích xuất phản hồi (friend_replied)
        unread = int(conv.get("unread_count", 0) or 0)
        friend_replied = unread > 0

        return {
            "username": found_username,
            "streak_count": streak_val,
            "is_today": is_today,
            "friend_replied": friend_replied,
            "create_time": create_time,
        }

    def _check_cloud_tiktok_chat_session(self, username: str, cookie_str: str) -> dict:
        """
        TIKTOK CLOUD SESSION DIRECT API ANALYZER (Từ sessionid / Cookie đã lưu):
        1. Gọi trực tiếp API tin nhắn / IM conversation gateway của TikTok.
        2. Quét cuộc trò chuyện với @username:
           - Trích xuất thời điểm tin nhắn cuối cùng (last_message_time).
           - Nếu tin nhắn cuối được gửi hôm nay -> Tự động xác định BẠN ĐÃ GỬI CHUỖI HÔM NAY!
           - Nếu tin cuối từ đối phương -> Tự động xác định ĐỐI PHƯƠNG ĐÃ REP!
        3. Tự động bóc tách streak badge từ TikTok JSON payload.
        """
        if not cookie_str or "sessionid" not in cookie_str:
            return {"success": False, "reason": "Chưa có sessionid"}

        clean_user = username.strip().replace("@", "").lower()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/messages",
            "Cookie": cookie_str,
            "Accept": "application/json, text/plain, */*",
        }

        # 1. Thử truy vấn Web IM Conversation Gateway
        for ep in [
            "https://www.tiktok.com/api/v1/web/im/conversation/list/?cursor=0&count=50",
            "https://www.tiktok.com/api/im/conversation/list/?cursor=0&count=50",
            "https://www.tiktok.com/api/v1/web/im/user/friends/?count=50",
            "https://www.tiktok.com/api/v1/im/user/friends/?count=50",
            "https://webcast.tiktok.com/webcast/im/fetch/",
        ]:
            try:
                res = requests.get(ep, headers=headers, timeout=6)
                if res.status_code == 200:
                    raw_data = res.json()
                    conv_list = (
                        raw_data.get("data", {}).get("conversations")
                        or raw_data.get("conversations")
                        or raw_data.get("conversation_list")
                        or raw_data.get("data", {}).get("user_list")
                        or raw_data.get("user_list")
                        or []
                    )
                    for conv in conv_list:
                        conv_str = json.dumps(conv, ensure_ascii=False).lower()
                        if clean_user in conv_str:
                            details = self._extract_conv_details(conv)
                            return {
                                "success": True,
                                "found": True,
                                "is_today": details["is_today"],
                                "friend_replied": details["friend_replied"],
                                "streak_count": details["streak_count"],
                            }
            except Exception as e_im:
                log.debug("IM endpoint error %s: %s", ep, e_im)

        # 2. Dự phòng: Kiểm tra qua Profile SSR
        try:
            r_user = requests.get(
                f"https://www.tiktok.com/@{clean_user}",
                headers=headers,
                timeout=5,
            )
            if r_user.status_code == 200:
                m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', r_user.text)
                if m:
                    d = json.loads(m.group(1))
                    u_info = d.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {})
                    if u_info:
                        return {
                            "success": True,
                            "found": True,
                            "nickname": u_info.get("nickname"),
                            "is_friend": (u_info.get("relation", 0) == 2),
                            "account_verified": True,
                        }
        except Exception:
            pass

        return {"success": False}

    def scan_inbox_conversations(self) -> list[dict]:
        """
        QUÉT TỰ ĐỘNG HỘP THƯ TIN NHẮN TIKTOK (HEADLESS CHROME NGẦM 100%):
        - Chạy hoàn toàn ngầm không mở cửa sổ/tab trên màn hình.
        - Truy cập https://www.tiktok.com/messages và trích xuất danh sách hội thoại.
        - Click từng hội thoại để đọc @username (chat-uniqueid), nickname, bong bóng chat đối phương.
        - Tự động phát hiện các bạn bè đang giữ chuỗi hoặc đang nhắn tin hoạt động.
        """
        discovered = []
        driver = None
        try:
            driver = self._get_driver(headless=True)
        except Exception as eg:
            log.warning("Không thể khởi động Headless Chrome để quét inbox: %s", eg)
            return []

        if driver is None:
            return []

        try:
            driver.get("https://www.tiktok.com/messages")
            time.sleep(5)

            conv_elements = driver.find_elements(
                By.CSS_SELECTOR,
                "div[data-e2e='dm-new-conversation-item'], div[class*='DivItemWrapper']"
            )
            total_items = len(conv_elements)
            log.info("Headless Chrome quét thấy %d cuộc hội thoại trong hộp thư TikTok", total_items)

            # Quét tối đa 20 cuộc hội thoại gần nhất để vừa nhanh vừa đủ toàn bộ bạn bè hoạt động
            scan_limit = min(20, total_items)
            my_account = ""

            for i in range(scan_limit):
                try:
                    # Lấy lại danh sách phần tử phòng trường hợp DOM tái render
                    elems = driver.find_elements(
                        By.CSS_SELECTOR,
                        "div[data-e2e='dm-new-conversation-item'], div[class*='DivItemWrapper']"
                    )
                    if i >= len(elems):
                        break
                    it = elems[i]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", it)
                    time.sleep(0.2)
                    it.click()
                    time.sleep(1.2)

                    uid_el = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='chat-uniqueid']")
                    uname = uid_el[0].text.replace("@", "").strip() if uid_el else ""

                    nick_el = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='dm-new-chat-nickname']")
                    nick = nick_el[0].text.strip() if nick_el else uname

                    if not uname:
                        continue

                    # Phân tích tương tác 2 chiều (bạn đã gửi & đối phương đã rep)
                    chat_data = driver.execute_script("""
                        const pane = document.querySelector("div[class*='DivChatArea'], div[class*='DivChatRoom'], div[class*='ChatBox']");
                        if (!pane) return { messages: [] };
                        const all = pane.querySelectorAll("div[class*='Time'], p[class*='Time'], span[class*='Time'], div[data-e2e='dm-new-chat-item']");
                        let currentDate = '';
                        const messages = [];
                        all.forEach(el => {
                            if (el.getAttribute('data-e2e') === 'dm-new-chat-item') {
                                const a = el.querySelector('a');
                                const sender = a ? a.href.split('@').pop().toLowerCase() : '';
                                messages.push({
                                    sender,
                                    text: el.innerText.trim(),
                                    dateTag: currentDate
                                });
                            } else {
                                const t = el.innerText.trim();
                                if (t.includes('202') || t.includes('Today') || t.includes('Hôm nay') || t.includes('Yesterday')) {
                                    currentDate = t;
                                }
                            }
                        });
                        return { messages };
                    """)
                    msgs = chat_data.get("messages", [])
                    last_msg = msgs[-1].get("text", "").replace("\n", " ").strip() if msgs else ""
                    
                    last_date_tag = msgs[-1].get("dateTag", "") if msgs else ""
                    recent_chunk = [m for m in msgs if m.get("dateTag") == last_date_tag] if last_date_tag else msgs[-8:]
                    
                    i_sent = False
                    friend_replied = False
                    for m in recent_chunk:
                        s = m.get("sender", "").lower()
                        if s:
                            if not my_account and s != uname.lower():
                                my_account = s
                            if my_account and s == my_account.lower():
                                i_sent = True
                            elif s == uname.lower() or (my_account and s != my_account.lower()):
                                friend_replied = True

                    card_time_has_colon = bool(re.search(r'\b\d{1,2}:\d{2}\b', it.text))
                    is_today = card_time_has_colon or ("today" in last_date_tag.lower()) or ("hôm nay" in last_date_tag.lower())
                    is_kept_today = (i_sent and friend_replied)

                    # Phát hiện streak từ avatar badge hoặc từ khoá trong nội dung chat
                    streak_count = 0
                    try:
                        badge_el = it.find_elements(
                            By.CSS_SELECTOR,
                            "div[class*='DivAvatarBadge'], span[class*='SpanAvatarBadgeText'], [class*='AvatarBadge']"
                        )
                        if badge_el:
                            b_txt = badge_el[0].text.strip()
                            if b_txt.isdigit() and int(b_txt) > 0:
                                streak_count = int(b_txt)
                    except Exception:
                        pass

                    if streak_count == 0:
                        all_combined = (it.text + " " + last_msg).lower()
                        if "chuỗi" in all_combined or "streak" in all_combined or "🔥" in all_combined:
                            m_st = re.search(r'(?:chuỗi|streak)[^0-9]{0,10}(\d{1,4})', all_combined)
                            if m_st:
                                streak_count = int(m_st.group(1))

                    discovered.append({
                        "username": uname,
                        "nickname": nick,
                        "streak_count": streak_count,
                        "friend_replied": friend_replied,
                        "i_sent": i_sent,
                        "is_kept_today": is_kept_today,
                        "last_msg": last_msg,
                        "source": "headless_inbox",
                    })
                    log.info("Phát hiện hội thoại: %s (@%s) - Chuỗi: %d - Rep: %s", nick, uname, streak_count, friend_replied)
                except Exception as e_item:
                    log.debug("Lỗi trích xuất hội thoại mục %d: %s", i, e_item)
                    continue
        except Exception as e_inbox:
            log.warning("Lỗi duyệt danh sách hộp thư TikTok: %s", e_inbox)
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        return discovered

    def auto_scan_friends_from_api(self) -> dict:
        """
        TỰ ĐỘNG QUÉT BẠN BÈ VÀ CHECK CHUỖI TỪ TIKTOK:
        1. Kiểm tra tình trạng sống/chết (Health Check) của phiên Cookie.
        2. Tự động mở Headless Chrome ngầm 100% quét toàn bộ danh sách hội thoại DM trên TikTok Web.
        3. Tự động nhận diện @username, nickname, chuỗi streak và trạng thái bạn bè rep tin nhắn.
        4. Tự động hợp nhất (auto-merge) bạn bè mới vào streak_targets và đồng bộ Supabase Cloud.
        5. Xác thực SSR dự phòng và cập nhật mô tả chuỗi thời gian thực.
        """
        cookie_str = self.load_session_cookie_string()
        if not cookie_str:
            return {
                "success": False,
                "total_scanned": 0,
                "reason": "Chưa có Cookie / sessionid của TikTok. Vui lòng nạp ở cột bên trái.",
            }

        health = self.check_session_health()
        if health.get("expired"):
            return {
                "success": False,
                "total_scanned": 0,
                "reason": "⚠️ Phiên đăng nhập TikTok của bạn ĐÃ HẾT HẠN (Session Expired)! TikTok đã thu hồi token này. Vui lòng lấy cookie mới trên TikTok Web (F12 -> Application -> Cookies -> sessionid) rồi dán vào ô 'Phiên TikTok' ở cột bên trái.",
            }

        targets = self.load_targets()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = datetime.now().strftime("%Y-%m-%d")
        new_added = 0
        updated_count = 0

        # 1. Thử quét sâu tự động từ Hộp thư Tin nhắn TikTok (Headless Chrome ngầm 100%)
        inbox_friends = []
        try:
            inbox_friends = self.scan_inbox_conversations()
        except Exception as e_ib:
            log.warning("Scan inbox conversations error: %s", e_ib)
        for f in inbox_friends:
            u = f.get("username", "").strip()
            if not u:
                continue

            existing = next((t for t in targets if t.get("username", "").lower() == u.lower()), None)
            sc = int(f.get("streak_count", 0) or 0)
            rep = bool(f.get("friend_replied"))

            if existing:
                # Cập nhật thông tin cho mục tiêu đã có
                if sc > 0:
                    existing["streak_count"] = max(existing.get("streak_count", 0), sc)
                if rep:
                    existing["friend_replied"] = True
                if f.get("nickname"):
                    existing["nickname"] = f["nickname"]
                existing["last_checked"] = now_str
                updated_count += 1
            else:
                # Tự động thêm bạn bè mới phát hiện được vào danh sách giữ chuỗi!
                desc = f"Chuỗi {sc} ngày 🔥 • Cần gửi chuỗi trước 23:59! ⚠️" if sc > 0 else f"Bạn bè TikTok ⚡ (@{f.get('nickname', u)})"
                new_target = {
                    "username": u,
                    "nickname": f.get("nickname") or u,
                    "custom_msg": None,
                    "streak_count": sc,
                    "friend_replied": rep,
                    "last_sent": "Chưa gửi",
                    "status": desc + " [Đã tự động quét ⚡]",
                    "last_checked": now_str,
                    "is_friend": True,
                }
                targets.append(new_target)
                new_added += 1

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
            "Cookie": cookie_str,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # 2. Thử bổ sung thêm từ các REST API Endpoint mở (dự phòng & mock)
        for ep in [
            "https://www.tiktok.com/api/v1/web/im/conversation/list/?cursor=0&count=50",
            "https://www.tiktok.com/api/im/conversation/list/?cursor=0&count=50",
        ]:
            try:
                res_api = requests.get(ep, headers=headers, timeout=4)
                if res_api.status_code == 200:
                    raw_data = res_api.json()
                    conv_list = (
                        raw_data.get("data", {}).get("conversations")
                        or raw_data.get("conversations")
                        or raw_data.get("conversation_list")
                        or []
                    )
                    for conv in conv_list:
                        details = self._extract_conv_details(conv)
                        cand_name = details.get("username")
                        if cand_name and not any(t["username"].lower() == cand_name.lower() for t in targets):
                            targets.append({
                                "username": cand_name,
                                "custom_msg": None,
                                "streak_count": details.get("streak_count", 0),
                                "friend_replied": details.get("friend_replied", False),
                                "last_sent": "Chưa gửi",
                                "status": "Đã quét từ TikTok API ⚡",
                                "last_checked": now_str,
                                "is_friend": True,
                            })
                            new_added += 1
            except Exception:
                pass

        # 3. Quét & đồng bộ trạng thái quan hệ bạn bè qua TikTok SSR
        for t in targets:
            u = t.get("username", "")
            if not u:
                continue
            try:
                resp = requests.get(f"https://www.tiktok.com/@{u}", headers=headers, timeout=5)
                if resp.status_code == 200:
                    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', resp.text)
                    if m:
                        d = json.loads(m.group(1))
                        u_info = d.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {})
                        if u_info:
                            t["nickname"] = u_info.get("nickname") or t.get("nickname") or u
                            t["sec_uid"] = u_info.get("secUid") or t.get("sec_uid") or ""
                            rel = u_info.get("relation", 0)
                            t["is_friend"] = (rel == 2)
                            sc = int(t.get("streak_count", 0) or 0)
                            last_sent = t.get("last_sent", "")

                            if last_sent.startswith(today_str):
                                desc = f"Đang giữ chuỗi {sc} ngày 🔥 • Bạn đã gửi hôm nay! ✅"
                            elif sc > 0:
                                desc = f"Chuỗi {sc} ngày 🔥 • Cần gửi chuỗi trước 23:59! ⚠️"
                            else:
                                if rel == 2:
                                    desc = f"Bạn bè TikTok ✅ (@{t['nickname']}) • Sẵn sàng giữ chuỗi"
                                else:
                                    desc = f"Đã kết nối TikTok API ⚡ (@{t['nickname']})"
                            if t.get("friend_replied"):
                                desc += " • Đối phương đã rep! 🎉"
                            t["status"] = desc
                            t["last_checked"] = now_str
                            updated_count += 1
            except Exception as e_check:
                log.debug("Lỗi SSR bạn bè @%s: %s", u, e_check)

        self.save_targets(targets)
        return {
            "success": True,
            "total_scanned": len(targets),
            "new_added": new_added,
            "updated": updated_count,
            "my_username": health.get("username", ""),
            "friends": targets,
        }

    def mark_manual_send(self, username: str) -> dict:
        """
        GHI NHẬN ĐÃ GỬI CHUỖI BẰNG TAY (TRÊN ĐIỆN THOẠI HOẶC BROWSER):
        Cập nhật last_sent là thời điểm hiện tại, duy trì/tăng chuỗi và đồng bộ Supabase.
        """
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        today_str = now.strftime("%Y-%m-%d")
        targets = self.load_targets()
        for t in targets:
            if t.get("username") == username:
                prev_sent = t.get("last_sent", "")
                sc = int(t.get("streak_count", 0) or 0)
                if not prev_sent.startswith(today_str):
                    sc = max(sc + 1, 1)
                t["streak_count"] = sc
                t["last_sent"] = now_str
                desc = f"Đang giữ chuỗi {sc} ngày 🔥 • Bạn đã gửi hôm nay! ✅"
                if t.get("friend_replied"):
                    desc += " • Đối phương đã rep! 🎉"
                else:
                    desc += " • Đang chờ đối phương gửi lại 💬"
                t["status"] = desc
                self.save_targets(targets)
                return {"success": True, "streak_count": sc, "status_desc": desc}
        return {"success": False, "streak_count": 0, "status_desc": "Không tìm thấy tài khoản"}

    def check_streak_status(self, username: str) -> dict:
        """
        KIỂM TRA CHUỖI VÀ ĐỌC SỐ LỬA THẬT 100% (HEADLESS ẨN NGẦM - KHÔNG BẬT TAB):
        1. Mở Chrome Headless ngầm hoàn toàn dưới background OS.
        2. Truy cập cuộc hội thoại với @username, bóc tách trực tiếp số chuỗi streak badge và bong bóng chat đối phương rep.
        3. Dự phòng an toàn qua TikTok SSR API nếu môi trường không có sẵn Chrome.
        """
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        today_str = now.strftime("%Y-%m-%d")

        targets = self.load_targets()
        target = next((t for t in targets if t.get("username", "").lower() == username.lower()), None)
        last_sent = target.get("last_sent", "") if target else ""
        current_streak = int((target.get("streak_count") if target else 0) or 0)
        cookie_str = self.load_session_cookie_string()

        # CHIẾN LƯỢC 1: HEADLESS CHROME NGẦM ĐỌC LỬA THẬT VÀ TIN NHẮN THẬT
        driver = None
        try:
            driver = self._get_driver(headless=True)
        except Exception as eg:
            log.warning("Khởi động Headless Chrome để check: %s", eg)
            driver = None

        if driver is not None:
            try:
                input_box = self._open_chat_box(driver, username)
                if input_box:
                    time.sleep(2)
                    streak_found = False
                    streak_count = current_streak

                    candidate_elements = []
                    for sel in [
                        "[data-e2e*='streak']",
                        "[class*='streak' i]",
                        "[class*='Streak']",
                        "[aria-label*='streak' i]",
                        "[aria-label*='chuỗi' i]",
                        "div[class*='chat-header']",
                        "header",
                        "div[class*='conversation']",
                        "div[class*='UserTitle']",
                    ]:
                        try:
                            candidate_elements.extend(driver.find_elements(By.CSS_SELECTOR, sel))
                        except Exception:
                            pass

                    for el in candidate_elements:
                        found, val = self._extract_streak_from_text_or_elem(el)
                        if found:
                            streak_found = True
                            if val > 0:
                                streak_count = val
                                break

                    chat_data = driver.execute_script("""
                        const pane = document.querySelector("div[class*='DivChatArea'], div[class*='DivChatRoom'], div[class*='ChatBox']");
                        if (!pane) return { messages: [] };
                        const all = pane.querySelectorAll("div[class*='Time'], p[class*='Time'], span[class*='Time'], div[data-e2e='dm-new-chat-item']");
                        let currentDate = '';
                        const messages = [];
                        all.forEach(el => {
                            if (el.getAttribute('data-e2e') === 'dm-new-chat-item') {
                                const a = el.querySelector('a');
                                const sender = a ? a.href.split('@').pop().toLowerCase() : '';
                                messages.push({ sender, text: el.innerText.trim(), dateTag: currentDate });
                            } else {
                                const t = el.innerText.trim();
                                if (t.includes('202') || t.includes('Today') || t.includes('Hôm nay') || t.includes('Yesterday')) {
                                    currentDate = t;
                                }
                            }
                        });
                        return { messages };
                    """)
                    msgs = chat_data.get("messages", [])
                    last_msg_text = msgs[-1].get("text", "").replace("\n", " ").strip() if msgs else ""
                    last_date_tag = msgs[-1].get("dateTag", "") if msgs else ""
                    recent_chunk = [m for m in msgs if m.get("dateTag") == last_date_tag] if last_date_tag else msgs[-8:]

                    i_sent_recently = False
                    friend_replied = False
                    clean_target = username.strip().replace("@", "").lower()

                    for m in recent_chunk:
                        s = m.get("sender", "").lower()
                        if s:
                            if s == clean_target:
                                friend_replied = True
                            else:
                                i_sent_recently = True

                    already_sent_today = i_sent_recently or (last_sent and last_sent.startswith(today_str))

                    if already_sent_today and friend_replied:
                        if not last_sent.startswith(today_str):
                            self._update_target_on_send(username, now_str)
                        desc = f"Đang giữ chuỗi {streak_count} ngày 🔥 • Hai bên đã rep qua lại, đã giữ chuỗi hôm nay! 🎉✅"
                    elif already_sent_today and not friend_replied:
                        if not last_sent.startswith(today_str):
                            self._update_target_on_send(username, now_str)
                        desc = f"Đang giữ chuỗi {streak_count} ngày 🔥 • Bạn đã gửi hôm nay! ✅ • Đang chờ đối phương gửi lại 💬"
                    elif not already_sent_today and friend_replied:
                        desc = f"Chuỗi {streak_count} ngày 🔥 • Đối phương đã rep! 💬 • Bạn chưa gửi chuỗi, cần rep trước 23:59! ⚠️"
                    else:
                        desc = f"Chuỗi {streak_count} ngày 🔥 • Cả hai chưa rep hôm nay • Cần gửi chuỗi trước 23:59! ⚠️"

                    desc += " [Headless ⚡]"
                    self._update_target_check_result(username, desc, streak_count, friend_replied, now_str)
                    return {
                        "checked": True,
                        "has_streak": streak_found or (streak_count > 0),
                        "streak_count": streak_count,
                        "friend_replied": friend_replied,
                        "last_message": last_msg_text,
                        "status_desc": desc,
                    }
            except Exception as e_sel:
                log.warning("Headless Chrome check gặp lỗi: %s. Chuyển sang SSR API.", e_sel)
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # CHIẾN LƯỢC 2: DỰ PHÒNG QUA TIKTOK API & SSR
        api_res = self._check_cloud_tiktok_chat_session(username, cookie_str)
        streak_count = max(int(api_res.get("streak_count", 0) or 0), current_streak)
        is_today = bool(api_res.get("is_today")) or (last_sent and last_sent.startswith(today_str))
        friend_replied = bool(api_res.get("friend_replied")) or (target.get("friend_replied", False) if target else False)
        nickname = api_res.get("nickname") or (target.get("nickname") if target else None) or username

        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)
        rem_sec = max(0, int((end_of_day - now).total_seconds()))
        countdown_note = f"(⏳ Còn {rem_sec // 3600}h {(rem_sec % 3600) // 60}p trước 23:59)"

        if is_today:
            desc = f"Đang giữ chuỗi {streak_count} ngày 🔥 • Bạn đã gửi hôm nay! ✅"
            if friend_replied:
                desc += " • Đối phương đã rep! 🎉"
            else:
                desc += " • Đang chờ đối phương rep 💬"
        elif streak_count > 0:
            desc = f"Chuỗi {streak_count} ngày 🔥 • Cần gửi chuỗi trước 23:59! ⚠️ {countdown_note}"
            if friend_replied:
                desc += " • Đối phương đã rep! ✅"
        else:
            if api_res.get("is_friend"):
                desc = f"Bạn bè TikTok ✅ (@{nickname}) • Sẵn sàng giữ chuỗi"
            else:
                desc = f"Đã kết nối TikTok API ⚡ (@{nickname})"

        desc += " [TikTok API ⚡]"
        self._update_target_check_result(username, desc, streak_count, friend_replied, now_str)

        return {
            "checked": True,
            "has_streak": streak_count > 0,
            "streak_count": streak_count,
            "friend_replied": friend_replied,
            "nickname": nickname,
            "status_desc": desc,
            "source": "tiktok_api",
        }

    def run_login_sync(self):
        self.login_and_save_session()

    def run_send_sync(self, username: str, msg: str | None = None) -> bool:
        return self.send_streak_message(username, msg)

    def run_spam_huhu_sync(self, username: str, custom_spam_list: list[str] | None = None, max_rounds: int = 8) -> dict:
        return self.spam_hu_hu(username, custom_spam_list=custom_spam_list, max_rounds=max_rounds)

    def run_check_sync(self, username: str) -> dict:
        return self.check_streak_status(username)

    def run_scan_friends_sync(self) -> dict:
        return self.auto_scan_friends_from_api()
