"""
streak/notifier.py — Báo động âm thanh & thông báo Windows (Hú hú).
"""
import winsound
import threading
from src.utils.logger import get_logger

log = get_logger(__name__)


def play_hu_hu_sound():
    """Phát chuỗi âm thanh beep gấp gáp cảnh báo sắp đứt chuỗi."""
    def _beep():
        try:
            # Beep nhịp điệu cảnh báo 3 lần: hú hú hú!
            for _ in range(3):
                winsound.Beep(1200, 200)  # Tần số cao
                winsound.Beep(1600, 300)  # Hú cao hơn
        except Exception as e:
            log.warning("Không thể phát âm thanh winsound: %s", e)

    threading.Thread(target=_beep, daemon=True).start()