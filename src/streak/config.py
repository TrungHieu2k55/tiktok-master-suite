"""
streak/config.py — Cấu hình giữ chuỗi & spam nhắc nhở (hú hú).
"""
from pathlib import Path

# Thư mục lưu trạng thái session trình duyệt Chrome
SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# File lưu cấu hình danh sách bạn bè
STREAK_CONFIG_FILE = Path("data/streak_targets.json")

# Danh sách tin nhắn giữ chuỗi thông thường
DEFAULT_MESSAGES = [
    "🔥",
    "streak 🔥",
    "🔥 streak",
    "giữ chuỗi nè 🔥",
    "🔥🔥",
    "day streak 🔥",
]

# Danh sách tin nhắn "HÚ HÚ SPAM ĐÒI CHUỖI" khi đối phương chưa gửi lại (đa dạng, thông minh, cấp độ leo thang)
HU_HU_SPAM_MESSAGES = [
    # Cấp độ 1: Nhẹ nhàng, dễ thương
    "HÚ HÚ gửi chuỗi đi má ơi 🔥🔥🔥",
    "Gửi chuỗi cứu chuỗi lẹ lẹ nè bà con ơi 🚨🔥",
    "Alo alo hú hú còn thức không gửi chuỗi điiii 📢🔥",
    "Chuỗi lửa của chúng ta đang chờ nè 🔥✨",

    # Cấp độ 2: Hối thúc, nhắc giờ
    "HÚ HÚ sắp hết ngày rồi kìa!! ⏰🔥",
    "Sắp qua 12h đêm rồi má ơi mau gửi chuỗi đi 🔥😱",
    "Còn vài phút nữa là đứt chuỗi đó trời ơiiiii 🚨🚨",
    "Dậy gửi chuỗi rồi ngủ tiếp người anh em ơi 😴🔥",

    # Cấp độ 3: Đe dọa hài hước, troll
    "Đứt chuỗi là tao qua nhà kiếm chuyện đó nha 🚨👊",
    "Đừng để công sức giữ chuỗi bấy lâu nay tan biến chứ!! 😭🔥",
    "Rep tin nhắn lẹ không tao hú liên tục tới sáng luôn á 📢🔊",
    "Chuông báo động khẩn cấp cứu chuỗi reng reng 🚨🔔🔥",

    # Cấp độ 4: Bắn spam dồn dập
    "HÚ HÚ HÚ HÚ HÚ HÚ 🔥🔥🔥",
    "GỬI CHUỖI ĐI MÀ TRỜI ƠI LẸ NÈ ⏰⚡",
    "🔥🔥🔥🔥🔥🔥🔥🔥",
    "Chỉ cần gửi 1 dấu chấm thôi cũng được cứu chuỗi đi! 🆘🔥",
]
# File lưu cấu hình hệ thống (trạng thái scheduler tự động)
APP_SETTINGS_FILE = Path("data/app_settings.json")
