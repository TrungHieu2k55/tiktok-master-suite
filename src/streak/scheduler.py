from src.storage.supabase_client import supabase_get, supabase_set
"""
streak/scheduler.py — Tiến trình chạy ngầm hẹn giờ giữ chuỗi & HÚ HÚ THÔNG MINH lúc 23h30.
Tự động dùng mẫu spam riêng của từng người nếu có.
Có cơ chế lưu file data/app_settings.json để F5 không bao giờ bị mất trạng thái.
"""
import json
import threading
import time
from datetime import datetime
from pathlib import Path

from src.streak.bot import TikTokStreakBot
from src.streak.config import APP_SETTINGS_FILE
from src.utils.logger import get_logger

log = get_logger(__name__)


def load_scheduler_enabled() -> bool:
    try:
        supa_val = supabase_get("auto_night_guard")
        if supa_val is not None:
            return bool(supa_val)
    except Exception:
        pass
    try:
        if APP_SETTINGS_FILE.exists():
            data = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
            return bool(data.get("auto_night_guard", False))
    except Exception as e:
        log.warning("Lỗi đọc app_settings: %s", e)
    return False


def save_scheduler_enabled(enabled: bool):
    try:
        APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if APP_SETTINGS_FILE.exists():
            try:
                data = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["auto_night_guard"] = bool(enabled)
        APP_SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            supabase_set("auto_night_guard", bool(enabled))
        except Exception:
            pass
    except Exception as e:
        log.warning("Lỗi ghi app_settings: %s", e)


class StreakScheduler:
    def __init__(self, check_interval_sec: int = 30):
        self.check_interval_sec = check_interval_sec
        self.is_running = False
        self._thread: threading.Thread | None = None
        self.last_run_tag = ""

    def run_normal_streak_check(self) -> int:
        """Gửi chuỗi bình thường trong ngày."""
        bot = TikTokStreakBot(headless=True)
        targets = bot.load_targets()
        if not targets:
            return 0

        today_str = datetime.now().strftime("%Y-%m-%d")
        sent_count = 0

        for t in targets:
            last_sent = t.get("last_sent", "")
            if not last_sent.startswith(today_str):
                u = t["username"]
                m = t.get("custom_msg")
                try:
                    ok = bot.send_streak_message(u, m)
                    if ok:
                        t["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        t["status"] = "Đã gửi chuỗi 🔥"
                        sent_count += 1
                except Exception as e:
                    log.error("Lỗi gửi streak @%s: %s", u, e)
                time.sleep(2)

        bot.save_targets(targets)
        return sent_count

    def run_night_emergency_huhu(self) -> int:
        """
        CƠ CHẾ ĐÊM KHẨN CẤP (Sau 23:30):
        Tự động kích hoạt Hú Hú thông minh dùng danh sách spam riêng của từng người!
        """
        bot = TikTokStreakBot(headless=True)
        targets = bot.load_targets()
        if not targets:
            return 0

        log.warning("🚨 [23h30 ĐÊM KHẨN CẤP] Bắt đầu kích hoạt HÚ HÚ THÔNG MINH cứu chuỗi!")
        saved_count = 0

        for t in targets:
            status = t.get("status", "")
            if "Đã Rep" not in status:
                u = t["username"]
                custom_spams = t.get("spam_messages")
                try:
                    res = bot.spam_hu_hu(u, custom_spam_list=custom_spams, max_rounds=8, check_interval_sec=3.0)
                    sent = res.get("sent", 0)
                    replied = res.get("replied", False)
                    if replied:
                        t["status"] = f"Người ta Đã Rep lại! 🎉🔥 ({sent} tin)"
                        saved_count += 1
                    else:
                        t["status"] = f"Đã Hú Hú đêm ({sent} tin) 📢"
                except Exception as e:
                    log.error("Lỗi Hú Hú đêm @%s: %s", u, e)
                time.sleep(2)

        bot.save_targets(targets)
        return saved_count

    def _loop(self):
        log.info("Scheduler bắt đầu chạy ngầm...")
        while self.is_running:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            hour = now.hour
            minute = now.minute

            # 1. Ban ngày: 08:00 và 20:00
            if hour in [8, 20] and self.last_run_tag != f"{today_str}_{hour}":
                log.info("⏰ Khung giờ gửi chuỗi: %02d:00", hour)
                self.run_normal_streak_check()
                self.last_run_tag = f"{today_str}_{hour}"

            # 2. Đêm: 23:30 trở đi
            tag_night = f"{today_str}_night_2330"
            if hour == 23 and minute >= 30 and self.last_run_tag != tag_night:
                log.warning("🚨 ĐÃ ĐẾN 23:30 ĐÊM! KÍCH HOẠT HÚ HÚ THÔNG MINH CỨU CHUỖI!")
                self.run_night_emergency_huhu()
                self.last_run_tag = tag_night

            time.sleep(self.check_interval_sec)

    def start(self, persist: bool = True):
        if persist:
            save_scheduler_enabled(True)
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            log.info("Đã bật tiến trình tự động hẹn giờ & Hú Hú đêm 23h30!")

    def stop(self, persist: bool = True):
        if persist:
            save_scheduler_enabled(False)
        self.is_running = False
        log.info("Đã dừng tiến trình tự động.")

    def auto_resume_if_enabled(self):
        """Tự động bật lại nếu trước đó người dùng đã bật."""
        if load_scheduler_enabled() and not self.is_running:
            self.start(persist=False)
            log.info("Khôi phục trạng thái Scheduler: Đang chạy 🟢")


global_scheduler = StreakScheduler()
# Tự động resume khi module được nạp
global_scheduler.auto_resume_if_enabled()
