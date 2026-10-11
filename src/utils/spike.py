"""
utils/spike.py — script chạy một lần để khám phá API pyktok thật.

Chạy trên máy có mạng SAU KHI cài:
    pip install pyktok pandas playwright
    playwright install chromium

Cách dùng:
    python -m src.utils.spike --url "https://www.tiktok.com/@user/video/ID"

Kết quả in ra:
    - help(pyk.save_tiktok_comments)
    - df.columns
    - df.dtypes
    - df.head(2)

Sau đó paste output vào anonymize.py và csv_writer.py để điền tên cột thật.
KHÔNG dùng file này trong production pipeline.
"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Spike: khám phá API pyktok")
    parser.add_argument("--url", required=True, help="URL video TikTok để test")
    parser.add_argument(
        "--browser", default="chrome", choices=["chrome", "firefox"],
        help="Trình duyệt (mặc định: chrome)"
    )
    args = parser.parse_args()

    # --- Import pyktok ---
    try:
        import pyktok as pyk
    except ImportError:
        print(
            "LỖI: pyktok chưa cài.\n"
            "Chạy: pip install pyktok playwright && playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    import pandas as pd

    # --- In signature ---
    print("=" * 60)
    print("HELP: pyk.save_tiktok_comments")
    print("=" * 60)
    help(pyk.save_tiktok_comments)

    # --- Thử gọi ---
    print("\n" + "=" * 60)
    print(f"Gọi save_tiktok_comments với URL: {args.url}")
    print("=" * 60)

    # TODO: Sau khi đọc help() ở trên, điều chỉnh cách gọi bên dưới.
    # Khả năng A — hàm trả về DataFrame (return_comments=True):
    #   df = pyk.save_tiktok_comments(args.url, return_comments=True)
    #
    # Khả năng B — hàm chỉ ghi file:
    #   import tempfile, os
    #   tmp = tempfile.mktemp(suffix=".csv")
    #   pyk.save_tiktok_comments(args.url, save_as=tmp)
    #   df = pd.read_csv(tmp)
    #   os.remove(tmp)
    #
    # Hiện tại để raise để nhắc mày điền vào:
    raise NotImplementedError(
        "Mở spike.py, đọc help() output, rồi uncomment đúng cách gọi bên trên."
    )

    # --- In kết quả (phần này chạy sau khi bỏ raise) ---
    print("\ndf.columns:")
    print(list(df.columns))

    print("\ndf.dtypes:")
    print(df.dtypes)

    print("\ndf.head(2):")
    print(df.head(2).to_string())

    print("\n✅ Paste output này vào:")
    print("   - src/utils/anonymize.py  (AUTHOR_ID_COLUMNS, PII_COLUMNS_TO_DROP, TIMESTAMP_COLUMNS)")
    print("   - src/storage/csv_writer.py  (COMMENT_ID_COL)")


if __name__ == "__main__":
    main()
