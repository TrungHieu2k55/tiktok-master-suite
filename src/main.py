"""
main.py — CLI entry point.

Dùng:
    python -m src.main comments --url URL [--output PATH] [--max-retries N]
    python -m src.main spike    --url URL [--browser chrome|firefox]
"""
import argparse
import sys

from src.utils.logger import get_logger

log = get_logger(__name__)


def cmd_comments(args: argparse.Namespace) -> None:
    from pathlib import Path
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
    except NotImplementedError as e:
        log.error("Chưa implement: %s", e)
        sys.exit(2)
    except ValueError as e:
        log.error("%s", e)
        sys.exit(1)
    except RuntimeError as e:
        log.error("Lỗi fetch: %s", e)
        sys.exit(3)


def cmd_spike(args: argparse.Namespace) -> None:
    from src.utils.spike import main as spike_main
    spike_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiktok-research",
        description="TikTok Research Comment Collector",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- comments ---
    p_comments = sub.add_parser("comments", help="Thu thap binh luan tu video TikTok")
    p_comments.add_argument("--url", required=True, help="URL video TikTok cong khai")
    p_comments.add_argument("--output", default=None, help="Duong dan CSV output (mac dinh: data/comments_<id>.csv)")
    p_comments.add_argument("--max-retries", type=int, default=3, help="So lan retry (mac dinh: 3)")
    p_comments.set_defaults(func=cmd_comments)

    # --- spike ---
    p_spike = sub.add_parser("spike", help="Kham pha API pyktok (chay mot lan)")
    p_spike.add_argument("--url", required=True, help="URL video de test")
    p_spike.add_argument("--browser", default="chrome", choices=["chrome", "firefox"])
    p_spike.set_defaults(func=cmd_spike)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
