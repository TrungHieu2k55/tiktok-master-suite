"""
run_bot.py — CLI Runner cho TikTok Streak Suite & Tự động chạy ngầm (Autonomous Daemon).

Sử dụng:
    python run_bot.py --help                : Xem hướng dẫn lệnh
    python run_bot.py send                  : Gửi giữ chuỗi tới tất cả bạn bè ngay lập tức
    python run_bot.py check                 : Kiểm tra trạng thái chuỗi & rep 2 chiều tất cả bạn bè
    python run_bot.py huhu                  : Kích hoạt Hú Hú khẩn cấp tới những ai chưa giữ chuỗi hôm nay
    python run_bot.py scan                  : Quét hộp thư TikTok và tự động cập nhật bạn bè
    python run_bot.py daemon                : Chạy tiến trình canh gác ngầm liên tục theo giờ hẹn
    python run_bot.py daemon --huhu 23:30   : Canh gác ngầm với mốc Hú Hú tuỳ chọn
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Đảm bảo root nằm trong PYTHONPATH
_root = str(Path(__file__).resolve().parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.streak.bot import TikTokStreakBot
from src.streak.scheduler import StreakScheduler, load_scheduler_config, save_scheduler_config
from src.utils.logger import get_logger

log = get_logger("run_bot")


def cmd_send(args):
    print("🔥 Đang bắt đầu đợt gửi giữ chuỗi tự động...")
    bot = TikTokStreakBot(headless=True)
    targets = bot.load_targets()
    if not targets:
        print("⚠️ Chưa có bạn bè nào trong danh sách. Hãy chạy 'python run_bot.py scan' trước.")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    success_count = 0
    for idx, t in enumerate(targets, 1):
        u = t.get("username")
        m = t.get("custom_msg")
        last_sent = t.get("last_sent", "")
        if not args.force and last_sent.startswith(today_str):
            print(f"[{idx}/{len(targets)}] @{u}: Đã gửi hôm nay rồi, bỏ qua (dùng --force để gửi lại).")
            continue

        print(f"[{idx}/{len(targets)}] Đang gửi tới @{u}...")
        ok = bot.send_streak_message(u, m)
        if ok:
            t["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            t["status"] = "Đang giữ chuỗi • Bạn đã gửi hôm nay! ✅"
            success_count += 1
            print(f"  ✅ Đã gửi thành công tới @{u}!")
        else:
            print(f"  ❌ Gửi thất bại tới @{u}.")
        time.sleep(1.5)

    bot.save_targets(targets)
    print(f"🎉 Hoàn tất! Đã gửi thành công {success_count}/{len(targets)} bạn bè.")


def cmd_check(args):
    print("🔍 Đang kiểm tra trạng thái chuỗi & rep 2 chiều từ TikTok...")
    bot = TikTokStreakBot(headless=True)
    targets = bot.load_targets()
    if not targets:
        print("⚠️ Danh sách bạn bè trống.")
        return

    for idx, t in enumerate(targets, 1):
        u = t.get("username")
        print(f"[{idx}/{len(targets)}] Đang kiểm tra @{u}...")
        res = bot.check_streak_status(u)
        status_desc = res.get("status_desc", "")
        print(f"  -> {status_desc}")

    print("🎉 Hoàn tất kiểm tra!")


def cmd_huhu(args):
    print("🚨 Kích hoạt chế độ khẩn cấp Hú Hú cứu chuỗi...")
    scheduler = StreakScheduler()
    saved = scheduler.run_night_emergency_huhu()
    print(f"🎉 Đã xong đợt Hú Hú! Có {saved} người bạn đã rep lại.")


def cmd_scan(args):
    print("🔄 Đang quét danh sách hội thoại từ hộp thư TikTok (Headless ngầm)...")
    bot = TikTokStreakBot(headless=True)
    res = bot.auto_scan_friends_from_api()
    if res.get("success"):
        print(f"🎉 Quét thành công! Đã phát hiện và cập nhật {res.get('total_scanned', 0)} bạn bè.")
    else:
        print(f"⚠️ Lỗi quét: {res.get('reason', 'Không rõ nguyên nhân')}")


def cmd_daemon(args):
    cfg = load_scheduler_config()
    if args.huhu:
        cfg["huhu_time"] = args.huhu
        save_scheduler_config(cfg)

    print("=" * 60)
    print("🤖 TIKTOK STREAK AUTONOMOUS DAEMON (TIẾN TRÌNH TỰ ĐỘNG CHẠY NGẦM)")
    print("=" * 60)
    print(f"⏰ Giờ gửi chuỗi ban ngày: {cfg.get('streak_hours', [8, 20])}")
    print(f"🚨 Mốc giờ khẩn cấp Hú Hú: {cfg.get('huhu_time', '23:30')}")
    print("💡 Bot sẽ tự động rà soát đồng hồ và hành động đúng giờ.")
    print("🛑 Bấm Ctrl+C để dừng tiến trình.")
    print("=" * 60)

    scheduler = StreakScheduler(check_interval_sec=args.interval)
    scheduler.start(persist=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Đang dừng bot an toàn...")
        scheduler.stop(persist=False)
        print("✅ Bot đã dừng.")


def main():
    parser = argparse.ArgumentParser(
        description="TikTok Streak Suite CLI & Background Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # send
    p_send = subparsers.add_parser("send", help="Gửi giữ chuỗi tới tất cả bạn bè")
    p_send.add_argument("--force", action="store_true", help="Gửi kể cả khi hôm nay đã gửi")

    # check
    p_check = subparsers.add_parser("check", help="Kiểm tra trạng thái chuỗi & rep của tất cả bạn bè")

    # huhu
    p_huhu = subparsers.add_parser("huhu", help="Kích hoạt Hú Hú khẩn cấp ban đêm")

    # scan
    p_scan = subparsers.add_parser("scan", help="Quét hội thoại từ hộp thư TikTok")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Chạy tiến trình tự động canh gác liên tục")
    p_daemon.add_argument("--huhu", type=str, help="Mốc giờ khẩn cấp Hú Hú (ví dụ: 23:30)")
    p_daemon.add_argument("--interval", type=int, default=30, help="Chu kỳ rà soát đồng hồ (giây)")

    args = parser.parse_args()

    if args.command == "send":
        cmd_send(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "huhu":
        cmd_huhu(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
