import os
import sys
from pathlib import Path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Nếu Streamlit Cloud chạy nhầm vào file này, tự động chuyển tiếp chạy thẳng app.py
if "STREAMLIT_SERVER_PORT" in os.environ or any("streamlit" in arg.lower() for arg in sys.argv):
    import app
    # app.py đã chạy toàn bộ giao diện Streamlit
else:
    import argparse
    from src.utils.logger import get_logger

    log = get_logger(__name__)

    def cmd_comments(args: argparse.Namespace) -> None:
        from src.research.comments import collect_comments
        output = Path(args.output) if args.output else None
        try:
            n = collect_comments(
                url=args.url,
                output_path=output,
                max_retries=args.max_retries,
            )
            if n:
                log.info("Hoàn thành — đã ghi %d bình luận mới.", n)
            else:
                log.info("Hoàn thành — không có bình luận mới.")
        except Exception as e:
            log.error("Lỗi: %s", e)
            sys.exit(1)

    def cmd_spike(args: argparse.Namespace) -> None:
        from src.utils.spike import main as spike_main
        spike_main()

    def build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="tiktok-research",
            description="TikTok Research Comment Collector",
        )
        sub = parser.add_subparsers(dest="command", required=False)
        p_comments = sub.add_parser("comments", help="Thu thap binh luan tu video TikTok")
        p_comments.add_argument("--url", required=True, help="URL video TikTok cong khai")
        p_comments.add_argument("--output", default=None, help="Duong dan CSV output")
        p_comments.add_argument("--max-retries", type=int, default=3, help="So lan retry")
        p_comments.set_defaults(func=cmd_comments)

        p_spike = sub.add_parser("spike", help="Kham pha API pyktok")
        p_spike.add_argument("--url", required=True, help="URL video de test")
        p_spike.add_argument("--browser", default="chrome", choices=["chrome", "firefox"])
        p_spike.set_defaults(func=cmd_spike)
        return parser

    def main() -> None:
        parser = build_parser()
        args = parser.parse_args()
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()

    if __name__ == "__main__":
        main()
