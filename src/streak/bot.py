"""
streak/bot.py — Tự động giữ chuỗi & Spam "Hú Hú" thông minh (Tùy chỉnh mẫu spam riêng cho từng người).
"""
import json
import random
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.streak.config import DEFAULT_MESSAGES, HU_HU_SPAM_MESSAGES, SESSION_DIR, STREAK_CONFIG_FILE
from src.utils.logger import get_logger

log = get_logger(__name__)


class TikTokStreakBot:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.profile_dir = (SESSION_DIR / "chrome_tiktok_profile").resolve()
        self.config_path = STREAK_CONFIG_FILE
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _get_driver(self, headless: bool = False):
        options = Options()
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if headless:
            options.add_argument("--headless=new")

        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def load_targets(self) -> list[dict]:
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error("Lỗi đọc danh sách: %s", e)
            return []

    def save_targets(self, targets: list[dict]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(targets, f, ensure_ascii=False, indent=2)

    def login_and_save_session(self):
        log.info("Mở Chrome để đăng nhập TikTok...")
        driver = self._get_driver(headless=False)
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
        profile_url = f"https://www.tiktok.com/@{username}"
        driver.get(profile_url)
        time.sleep(3)

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            txt = btn.text.strip().lower()
            if "nhắn tin" in txt or "message" in txt:
                btn.click()
                time.sleep(3)
                break

        selectors = ["div[contenteditable='true']", "textarea", "div[role='textbox']"]
        for sel in selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                return elems[0]
        return None

    def _count_messages_in_chat(self, driver) -> int:
        try:
            bubbles = driver.find_elements(By.CSS_SELECTOR, "[data-e2e='chat-item'], div[class*='ChatMessage'], div[class*='message-item']")
            return len(bubbles)
        except Exception:
            return 0

    def send_streak_message(self, username: str, custom_msg: str | None = None) -> bool:
        msg = custom_msg or random.choice(DEFAULT_MESSAGES)
        driver = self._get_driver(headless=self.headless)
        try:
            input_box = self._open_chat_box(driver, username)
            if input_box:
                input_box.click()
                input_box.send_keys(msg)
                time.sleep(0.5)
                input_box.send_keys(Keys.ENTER)
                log.info("✅ Đã gửi streak tới @%s", username)
                time.sleep(2)
                return True
            return False
        except Exception as e:
            log.error("Lỗi gửi streak @%s: %s", username, e)
            return False
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def spam_hu_hu(self, username: str, custom_spam_list: list[str] | None = None, max_rounds: int = 8, check_interval_sec: float = 3.0) -> dict:
        """
        TÍNH NĂNG HÚ HÚ THÔNG MINH VỚI MẪU SPAM RIÊNG TỪNG NGƯỜI:
        - Nếu người này có danh sách mẫu tin riêng (`custom_spam_list`) -> Dùng mẫu riêng của họ!
        - Nếu không có -> Dùng danh sách mẫu chung mặc định.
        - Tự động dừng ngay khi người ta nhắn lại!
        """
        driver = self._get_driver(headless=self.headless)
        sent_success = 0
        stopped_reason = "Đạt giới hạn số tin"

        # Lấy danh sách mẫu spam của riêng người này hoặc mẫu chung
        spam_pool = custom_spam_list if (custom_spam_list and len(custom_spam_list) > 0) else HU_HU_SPAM_MESSAGES

        try:
            input_box = self._open_chat_box(driver, username)
            if not input_box:
                log.error("Không tìm thấy khung chat để hú hú @%s", username)
                return {"sent": 0, "replied": False, "reason": "Không tìm thấy khung chat"}

            log.info("🚨 Bắt đầu HÚ HÚ tới @%s với %d mẫu tin riêng...", username, len(spam_pool))

            for i in range(max_rounds):
                count_before = self._count_messages_in_chat(driver)

                # Chọn tin nhắn từ danh sách riêng của người đó
                spam_text = spam_pool[i % len(spam_pool)]
                input_box.click()
                input_box.send_keys(spam_text)
                time.sleep(0.4)
                input_box.send_keys(Keys.ENTER)
                sent_success += 1
                log.info("📢 Gửi Hú Hú #%d tới @%s: '%s'", sent_success, username, spam_text)

                time.sleep(check_interval_sec)

                # Kiểm tra xem đối phương có nhắn lại chưa
                count_after = self._count_messages_in_chat(driver)
                if count_after > count_before + 1:
                    log.info("🎉 @%s ĐÃ NHẮN LẠI! DỪNG SPAM NGAY LẬP TỨC!", username)
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

    def run_login_sync(self):
        self.login_and_save_session()

    def run_send_sync(self, username: str, msg: str | None = None) -> bool:
        return self.send_streak_message(username, msg)

    def run_spam_huhu_sync(self, username: str, custom_spam_list: list[str] | None = None, max_rounds: int = 8) -> dict:
        return self.spam_hu_hu(username, custom_spam_list=custom_spam_list, max_rounds=max_rounds)