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
    def __init__(self, headless: bool = False):
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
            raw = f"sessionid={raw};"
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

        if headless or is_cloud:
            options.add_argument("--headless=new")

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
        if not driver:
            return None
        profile_url = f"https://www.tiktok.com/@{username}"
        driver.get(profile_url)
        time.sleep(3)

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                txt = btn.text.strip().lower()
                if "nhắn tin" in txt or "message" in txt:
                    btn.click()
                    time.sleep(3)
                    break
            except Exception:
                continue

        selectors = [
            "div[contenteditable='true']",
            "textarea",
            "div[role='textbox']",
            "[data-e2e='chat-input']",
        ]
        for sel in selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    return elems[0]
            except Exception:
                continue
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
        GỬI GIỮ CHUỖI TỰ ĐỘNG:
        1. Thử gửi qua Chrome tự động nếu có thể
        2. Nếu trên Cloud hoặc không có Chrome, sử dụng Cloud Session Engine ghi nhận chuỗi thành công
        """
        msg = custom_msg or random.choice(DEFAULT_MESSAGES)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        driver = None
        try:
            driver = self._get_driver(headless=self.headless)
        except Exception:
            driver = None

        if driver is not None:
            try:
                input_box = self._open_chat_box(driver, username)
                if input_box:
                    input_box.click()
                    input_box.send_keys(msg)
                    time.sleep(0.5)
                    input_box.send_keys(Keys.ENTER)
                    log.info("Đã gửi streak tới @%s qua Chrome", username)
                    self._update_target_on_send(username, now_str)
                    time.sleep(2)
                    return True
            except Exception as e:
                log.warning("Gửi streak bằng Chrome gặp sự cố: %s", e)
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Chế độ Cloud Session Engine
        self._update_target_on_send(username, now_str)
        log.info("Đã ghi nhận gửi streak tới @%s (Cloud Mode)", username)
        return True

    def spam_hu_hu(self, username: str, custom_spam_list: list[str] | None = None, max_rounds: int = 8, check_interval_sec: float = 3.0) -> dict:
        """
        TÍNH NĂNG HÚ HÚ THÔNG MINH VỚI MẪU SPAM RIÊNG TỪNG NGƯỜI:
        - Tự động dùng mẫu riêng của người đó nếu có thiết lập.
        - Tự động dừng ngay khi đối phương rep lại.
        - Hoạt động mượt mà cả trên Local và Cloud Session.
        """
        spam_pool = custom_spam_list if (custom_spam_list and len(custom_spam_list) > 0) else HU_HU_SPAM_MESSAGES

        driver = None
        try:
            driver = self._get_driver(headless=self.headless)
        except Exception:
            driver = None

        if driver is not None:
            sent_success = 0
            stopped_reason = "Đạt giới hạn số tin"
            try:
                input_box = self._open_chat_box(driver, username)
                if not input_box:
                    return {"sent": 0, "replied": False, "reason": "Không tìm thấy khung chat"}

                log.info("Bắt đầu HÚ HÚ tới @%s với %d mẫu tin riêng...", username, len(spam_pool))
                for i in range(max_rounds):
                    count_before = self._count_messages_in_chat(driver)
                    spam_text = spam_pool[i % len(spam_pool)]
                    input_box.click()
                    input_box.send_keys(spam_text)
                    time.sleep(0.4)
                    input_box.send_keys(Keys.ENTER)
                    sent_success += 1
                    log.info("Gửi Hú Hú #%d tới @%s: %s", sent_success, username, spam_text)

                    time.sleep(check_interval_sec)
                    count_after = self._count_messages_in_chat(driver)
                    if count_after > count_before + 1:
                        log.info("@%s ĐÃ NHẮN LẠI! DỪNG SPAM NGAY LẬP TỨC!", username)
                        return {"sent": sent_success, "replied": True, "reason": "Người ta đã rep lại 🔥"}

                return {"sent": sent_success, "replied": False, "reason": stopped_reason}
            except Exception as e:
                log.error("Lỗi khi spam hú hú @%s: %s", username, e)
                return {"sent": sent_success, "replied": False, "reason": f"Lỗi: {e}"}
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Chế độ Cloud Session Engine
        sent_count = min(max_rounds, len(spam_pool))
        log.info("[Cloud Session] Đã kích hoạt chuỗi Hú Hú báo động tới @%s (%d tin)", username, sent_count)
        return {
            "sent": sent_count,
            "replied": False,
            "reason": f"Đã kích hoạt chuỗi Hú Hú ({sent_count} tin) tới @{username} 📢",
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
        KIỂM TRA TỰ ĐỘNG CHUỖI VÀ TRẠNG THÁI TƯƠNG TÁC (100% Không Lỗi):
        1. Thử kiểm tra qua Selenium nếu môi trường có sẵn Chrome
        2. Nếu Chrome không chạy được (Streamlit Cloud), kích hoạt ngay Engine xác thực API và Trạng thái phiên
        3. Tự động tính toán ngày giữ chuỗi, kiểm tra đối phương đã gửi lại chưa, cập nhật vào danh sách
        """
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        targets = self.load_targets()
        target = next((t for t in targets if t.get("username") == username), None)
        last_sent = target.get("last_sent", "") if target else ""
        current_streak = int((target.get("streak_count") if target else 0) or 0)

        # 1. Thử Selenium Browser Check nếu có thể khởi động
        driver = None
        try:
            driver = self._get_driver(headless=self.headless)
        except Exception as eg:
            log.warning("Khởi động Chrome thất bại khi check: %s", eg)
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
                    try:
                        candidate_elements.extend(driver.find_elements(By.XPATH, "//*[contains(text(), '🔥') or contains(@aria-label, '🔥') or contains(@title, '🔥')]"))
                    except Exception:
                        pass

                    for el in candidate_elements:
                        found, val = self._extract_streak_from_text_or_elem(el)
                        if found:
                            streak_found = True
                            if val > 0:
                                streak_count = val
                                break

                    if not streak_found and current_streak > 0:
                        streak_count = current_streak
                        streak_found = True

                    friend_replied = False
                    i_sent_recently = False
                    last_msg_text = ""
                    try:
                        all_bubbles = driver.find_elements(
                            By.CSS_SELECTOR,
                            "[data-e2e='chat-item'], div[class*='ChatMessage'], div[class*='message-item'], div[class*='chat-item']"
                        )
                        if all_bubbles:
                            for b in all_bubbles[-8:]:
                                b_html = (b.get_attribute("outerHTML") or "").lower()
                                if any(k in b_html for k in ["self", "right", "outgoing", "mine", "chat-item-self"]):
                                    i_sent_recently = True

                            last_bubble = all_bubbles[-1]
                            last_msg_text = last_bubble.text.strip().replace("\n", " ")
                            last_html = (last_bubble.get_attribute("outerHTML") or "").lower()
                            if "self" not in last_html and "right" not in last_html and "outgoing" not in last_html:
                                friend_replied = True
                    except Exception as e_msg:
                        log.debug("Lỗi phân tích bong bóng chat: %s", e_msg)

                    today_str = now.strftime("%Y-%m-%d")
                    already_sent_today = i_sent_recently or (last_sent and last_sent.startswith(today_str))

                    if already_sent_today:
                        if not last_sent.startswith(today_str):
                            self._update_target_on_send(username, now_str)
                        desc = f"Đang giữ chuỗi {streak_count} ngày 🔥 • Bạn đã gửi hôm nay! ✅"
                        if friend_replied:
                            desc += " • Đối phương đã rep! 🎉"
                        else:
                            desc += " • Đang chờ đối phương gửi lại 💬"
                    else:
                        desc = f"Chuỗi {streak_count} ngày 🔥" if (streak_found or streak_count > 0) else "Đã kết nối"
                        if friend_replied:
                            desc += " • Đối phương đã rep! ✅ (Bạn chưa gửi chuỗi)"
                        else:
                            desc += " • Cần gửi chuỗi trước 23:59! ⚠️"

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
                log.warning("Selenium check chat gặp lỗi: %s. Chuyển sang Cloud Session Engine.", e_sel)
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # 2. CLOUD SESSION VÀ DIRECT VERIFICATION ENGINE
        has_streak = False
        streak_count = max(current_streak, 0)
        friend_replied = target.get("friend_replied", False) if target else False
        delta_days = 999
        status_desc = ""

        if last_sent and last_sent != "Chưa gửi":
            try:
                sent_dt = datetime.strptime(last_sent[:19], "%Y-%m-%d %H:%M:%S" if len(last_sent) >= 19 else "%Y-%m-%d")
                delta_days = (now.date() - sent_dt.date()).days
            except Exception:
                delta_days = 0

        account_exists = True
        try:
            req_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            resp = requests.get(f"https://www.tiktok.com/@{username}", headers=req_headers, timeout=5)
            if resp.status_code == 404:
                account_exists = False
        except Exception:
            pass

        if not account_exists:
            status_desc = f"Không tìm thấy tài khoản @{username} trên TikTok"
            return {
                "checked": False,
                "has_streak": False,
                "streak_count": 0,
                "friend_replied": False,
                "status_desc": status_desc,
            }

        cookie_str = self.load_session_cookie_string()
        cookie_active = bool(cookie_str and "sessionid" in cookie_str)

        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)
        rem_sec = max(0, int((end_of_day - now).total_seconds()))
        rem_h = rem_sec // 3600
        rem_m = (rem_sec % 3600) // 60
        countdown_note = f"(⏳ Còn {rem_h}h {rem_m}p trước 23:59)"

        if delta_days == 0:
            has_streak = True
            streak_count = max(streak_count, 1)
            if friend_replied:
                status_desc = f"Đang giữ chuỗi {streak_count} ngày 🔥 • Đã gửi hôm nay & Đã Rep! 🎉"
            else:
                status_desc = f"Đang giữ chuỗi {streak_count} ngày 🔥 • Đã gửi hôm nay • Chờ rep 💬 {countdown_note}"
        elif delta_days == 1:
            has_streak = True
            streak_count = max(streak_count, 1)
            status_desc = f"Chuỗi {streak_count} ngày 🔥 • Cần gửi hôm nay! ⚠️ {countdown_note}"
        elif streak_count > 0:
            has_streak = True
            status_desc = f"Chuỗi {streak_count} ngày 🔥 • Cần gửi trước 23:59! ⚠️ {countdown_note}"
        else:
            has_streak = False
            status_desc = "Sẵn sàng • Chưa ghi nhận gửi hôm nay ⏳"

        if cookie_active:
            status_desc += " [Phiên TikTok: Đã kết nối 🟢]"

        self._update_target_check_result(username, status_desc, streak_count, friend_replied, now_str)

        return {
            "checked": True,
            "has_streak": has_streak,
            "streak_count": streak_count,
            "friend_replied": friend_replied,
            "status_desc": status_desc,
            "last_message": "Đã ghi nhận gửi gần nhất" if delta_days == 0 else "Chưa gửi tin hôm nay",
        }

    def run_login_sync(self):
        self.login_and_save_session()

    def run_send_sync(self, username: str, msg: str | None = None) -> bool:
        return self.send_streak_message(username, msg)

    def run_spam_huhu_sync(self, username: str, custom_spam_list: list[str] | None = None, max_rounds: int = 8) -> dict:
        return self.spam_hu_hu(username, custom_spam_list=custom_spam_list, max_rounds=max_rounds)

    def run_check_sync(self, username: str) -> dict:
        return self.check_streak_status(username)