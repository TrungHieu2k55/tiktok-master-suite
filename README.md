# TikTok Comment Collector

Tool thu thập bình luận từ video TikTok công khai, phục vụ mục đích nghiên cứu.

## Yêu cầu

- Python 3.10+
- Một trình duyệt đã đăng nhập TikTok (Chrome hoặc Firefox) trên máy chạy script

## Cài đặt

\\\ash
pip install -r requirement.txt
playwright install chromium
\\\

> **Lưu ý về phiên bản pyktok:** Trước khi cài, kiểm tra bản mới nhất:
> \pip index versions pyktok\
> rồi pin vào requirement.txt (ví dụ \pyktok==0.0.x\).

## Cách dùng

\\\ash
python src/main.py --url "https://www.tiktok.com/@user/video/1234567890" --output data/comments.csv
\\\

### Tham số

| Tham số | Bắt buộc | Mô tả |
|---------|----------|-------|
| \--url\ | ✅ | URL video TikTok công khai |
| \--output\ | ✅ | Đường dẫn file CSV đầu ra |
| \--browser\ | ❌ | Trình duyệt để lấy cookie: \chrome\ (mặc định) hoặc \irefox\ |
| \--max-retries\ | ❌ | Số lần retry khi thất bại (mặc định: 3) |

## Cấu trúc output CSV

> ⚠️ Tên cột chính xác phụ thuộc vào phiên bản pyktok. Chạy \help(pyk.save_tiktok_comments)\
> và in \df.columns\ sau khi cài để xác nhận, rồi cập nhật phần này.

Các cột dự kiến sau khi ẩn danh hóa:

| Cột | Mô tả |
|-----|-------|
| \ideo_id\ | ID video |
| \comment_id\ | ID bình luận (dùng để lọc trùng) |
| \uthor_id_hashed\ | ID tác giả đã băm SHA-256 (không thể đảo ngược) |
| \created_at\ | Thời gian tạo (ISO 8601) |
| \	ext\ | Nội dung bình luận |
| \like_count\ | Số lượt thích |
| \eply_count\ | Số lượt trả lời |
| \collected_at\ | Thời điểm thu thập |

Các cột PII bị loại bỏ: username gốc, avatar URL, bio, follower count.

## Lưu ý đạo đức & pháp lý

- Chỉ thu thập video **công khai**.
- Không dùng cho mục đích thương mại hoặc theo dõi cá nhân.
- Tuân thủ [TikTok Terms of Service](https://www.tiktok.com/legal/terms-of-service).
- Dữ liệu cần được ẩn danh trước khi lưu trữ hoặc chia sẻ.

## Trạng thái

- [ ] Skeleton cấu trúc project
- [ ] URL validation + retry logic
- [ ] Logging
- [ ] Xác nhận API pyktok (cần cài và chạy thật)
- [ ] Anonymization theo tên cột thật
- [ ] Unit tests
