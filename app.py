"""
app.py — TikTok Suite Master 🔥 (All-in-One Dashboard)
- TikTok Streak Automation & Smart Hú Hú Spam
- TikTok Full API Explorer & RAW JSON Inspector
- Fast & Headless Data Collector (Comments & Metadata)
- Interactive Data Analytics & Export
"""
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import OUTPUT_DIR
from src.research.comments import collect_comments
from src.research.video_info import fetch_video_info, save_video_info
from src.research.tiktok_api_hub import (
    query_video_full_api,
    query_comments_full_api,
    query_comment_replies_api,
    query_user_profile_api,
    query_search_api,
    query_live_room_api,
)
from src.streak.bot import TikTokStreakBot
from src.streak.config import DEFAULT_MESSAGES, HU_HU_SPAM_MESSAGES, SESSION_DIR, STREAK_CONFIG_FILE
from src.streak.scheduler import global_scheduler
from src.ui.styles import inject_css
from src.ui.auth import render_login_screen, is_authenticated, is_admin, get_current_user, logout, update_admin_password
from src.utils.validators import extract_video_id, is_valid_video_url

# 1. Cấu hình trang với layout wide
st.set_page_config(
    page_title="TikTok Streak Master 🔥",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Nhúng CSS tập trung duy nhất
inject_css()

# 3. Kiểm tra xác thực trước khi cho phép vào hệ thống
if not is_authenticated():
    render_login_screen()
    st.stop()

# Lấy thông tin user hiện tại
current_user = get_current_user() or {}
user_role = current_user.get("role", "guest")
user_name = current_user.get("name", "Người dùng")

bot = TikTokStreakBot(headless=False)
profile_exists = (SESSION_DIR / "chrome_tiktok_profile").exists()

# ---------------------------------------------------------------------------
# SIDEBAR: CÀI ĐẶT & TRẠNG THÁI TÀI KHOẢN
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <img src="https://upload.wikimedia.org/wikipedia/en/a/a9/TikTok_logo.svg" width="36" />
        <div>
            <div class="sidebar-brand-title">TikTok Streak Bot</div>
            <div style="font-size: 0.8rem; color: #94A3B8;">v2.7 • Live Log UI Suite</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Hiển thị tài khoản đang đăng nhập & Nút Đăng xuất
    with st.container(border=True):
        st.markdown(f"👤 **{user_name}**")
        role_badge = "badge-success" if is_admin() else "badge-warning"
        st.markdown(f'<span class="status-badge {role_badge}">Vai trò: {user_role.upper()}</span>', unsafe_allow_html=True)
        st.write("")
        c_so1, c_so2 = st.columns([1, 1])
        with c_so1:
            if st.button("🚪 Đăng xuất", width="stretch", type="secondary"):
                logout()
        with c_so2:
            if is_admin():
                pop_pw = st.popover("🔑 Đổi pass", width="stretch")
                with pop_pw:
                    st.markdown("**Đổi mật khẩu Admin**")
                    with st.form("change_admin_pw_form", clear_on_submit=True):
                        new_pw = st.text_input("Mật khẩu mới:", type="password")
                        confirm_pw = st.text_input("Nhập lại mật khẩu:", type="password")
                        sub_pw = st.form_submit_button("Lưu mật khẩu", type="primary", width="stretch")
                        if sub_pw:
                            if not new_pw or len(new_pw) < 6:
                                st.error("Mật khẩu phải từ 6 ký tự trở lên!")
                            elif new_pw != confirm_pw:
                                st.error("Mật khẩu xác nhận không khớp!")
                            else:
                                if update_admin_password(new_pw):
                                    st.success("Đổi mật khẩu thành công!")
                                    st.toast("Đã lưu mật khẩu Admin mới!", icon="🔑")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Lỗi khi lưu mật khẩu mới!")

    st.write("")

    # Nhóm Hẹn giờ tự động linh hoạt (Custom Cron / Hours)
    from src.streak.scheduler import load_scheduler_config, save_scheduler_config
    sched_cfg = load_scheduler_config()
    st.markdown("#### 🌙 Vệ tinh hẹn giờ & Hú Hú")
    auto_sched = st.toggle("Kích hoạt chạy ngầm tự động", value=global_scheduler.is_running)
    if auto_sched != global_scheduler.is_running:
        if auto_sched:
            global_scheduler.start()
            st.toast("Đã bật chạy ngầm tự động!", icon="🌙")
        else:
            global_scheduler.stop()
            st.toast("Đã tắt chạy ngầm!", icon="🛑")
        st.rerun()

    pop_sched_cfg = st.popover("⚙️ Cài đặt khung giờ", width="stretch")
    with pop_sched_cfg:
        st.markdown("**Cấu Hình Khung Giờ Chạy Ngầm**")
        st.caption("Tự động gửi giữ chuỗi ban ngày & kích hoạt Hú Hú báo động ban đêm.")
        with st.form("custom_sched_form"):
            h1 = st.number_input("Khung giờ gửi #1 (Sáng):", min_value=0, max_value=23, value=sched_cfg.get("streak_hours", [8, 20])[0] if len(sched_cfg.get("streak_hours", [8, 20])) > 0 else 8, step=1)
            h2 = st.number_input("Khung giờ gửi #2 (Tối):", min_value=0, max_value=23, value=sched_cfg.get("streak_hours", [8, 20])[1] if len(sched_cfg.get("streak_hours", [8, 20])) > 1 else 20, step=1)
            huhu_time_val = st.text_input("Giờ khẩn cấp HÚ HÚ (HH:MM):", value=sched_cfg.get("huhu_time", "23:30"), help="Ví dụ: 23:30 hoặc 23:45")
            sub_sched = st.form_submit_button("💾 Lưu Cài Đặt Giờ", width="stretch", type="primary")
            if sub_sched:
                sched_cfg["streak_hours"] = sorted(list(set([int(h1), int(h2)])))
                sched_cfg["huhu_time"] = huhu_time_val.strip() if huhu_time_val.strip() else "23:30"
                save_scheduler_config(sched_cfg)
                st.success("Đã cập nhật khung giờ thành công!")
                time.sleep(0.5)
                st.rerun()

    if global_scheduler.is_running:
        hrs_str = ", ".join([f"{h:02d}h" for h in sched_cfg.get("streak_hours", [8, 20])])
        hh_str = sched_cfg.get("huhu_time", "23:30")
        st.success(f"🟢 Đang canh gác: Gửi ({hrs_str}) • Hú Hú ({hh_str})")
    else:
        st.caption("⚪ Chế độ hẹn giờ đang tắt")

    st.write("")

    # Nhóm Phiên đăng nhập (Live Health Check)
    st.markdown("#### 🔐 Phiên đăng nhập")
    saved_cookie = bot.load_session_cookie_string()
    health_res = bot.check_session_health() if saved_cookie else {"status": "none", "valid": False, "expired": False}

    if health_res.get("expired"):
        st.error("🔴 Phiên TikTok đã hết hạn!")
        st.caption("⚠️ Token TikTok đã hết hạn. Hãy bấm nút đỏ bên dưới để cập nhật sessionid mới.")
        cookie_label = "🔴 Hết hạn"
    elif health_res.get("valid"):
        u_tag = health_res.get("username")
        tag_str = f" (@{u_tag})" if u_tag else ""
        st.success(f"🟢 Phiên TikTok hoạt động{tag_str}")
        cookie_label = "🟢 Đã nạp"
    elif profile_exists:
        st.success("🟢 Phiên Chrome Local")
        cookie_label = "🟢 Đã nạp"
    else:
        st.warning("🟡 Chưa có phiên TikTok")
        cookie_label = "🍪 Nạp Cookie"

    is_cloud_env = bool(os.environ.get("STREAMLIT_SERVER_PORT") or (os.name != "nt"))
    c_lg1, c_lg2 = st.columns([1.1, 1.1])
    with c_lg1:
        if is_cloud_env:
            st.button("🔑 Đăng nhập", width="stretch", type="secondary", disabled=True, help="Đăng nhập tự động chỉ chạy trên localhost máy tính cá nhân")
        else:
            if st.button("🔑 Đăng nhập", width="stretch", type="secondary", help="Mở Chrome trên máy tính để đăng nhập"):
                with st.spinner("Đang mở Chrome... Hãy đăng nhập và đóng trình duyệt khi xong."):
                    bot.run_login_sync()
                    st.success("Đã đồng bộ phiên đăng nhập!")
                    st.rerun()
    with c_lg2:
        pop_cookie = st.popover(cookie_label, width="stretch")
        with pop_cookie:
            st.markdown("**Quản Lý Phiên TikTok**")
            if health_res.get("expired"):
                st.error("❌ Cookie hiện tại đã hết hạn (Session Expired)!")
                st.caption("TikTok đã vô hiệu hóa token này. Vui lòng copy sessionid mới từ trình duyệt và lưu lại bên dưới:")
            elif health_res.get("valid"):
                u_n = health_res.get("username", "")
                st.success(f"🟢 Đã kết nối tài khoản: **@{u_n}**")
                if st.button("🗑️ Xóa phiên đăng nhập", width="stretch"):
                    bot.save_session_cookie_string("")
                    st.rerun()
            elif saved_cookie:
                preview = (saved_cookie[:25] + "...") if len(saved_cookie) > 25 else saved_cookie
                st.success(f"🟢 Đang kết nối: `{preview}`")
                if st.button("🗑️ Xóa phiên đăng nhập", width="stretch"):
                    bot.save_session_cookie_string("")
                    st.rerun()
            else:
                st.info("⚪ Chưa có cookie phiên")

            st.caption("Dán sessionid hoặc Cookie mới vào đây:")
            with st.form("cookie_form"):
                cookie_in = st.text_area("Chuỗi Cookie / sessionid:", placeholder="sessionid=xxxx; ...", height=70)
                sub_cookie = st.form_submit_button("💾 Lưu Phiên Mới", type="primary", width="stretch")
                if sub_cookie and cookie_in.strip():
                    bot.save_session_cookie_string(cookie_in.strip())
                    health_chk = bot.check_session_health()
                    if health_chk.get("valid"):
                        st.toast(f"Đã kết nối tài khoản @{health_chk.get('username')}!", icon="🟢")
                        st.success(f"🎉 Kết nối thành công tài khoản @{health_chk.get('username')}!")
                    else:
                        st.warning(f"⚠️ {health_chk.get('msg')}")
                    time.sleep(0.8)
                    st.rerun()

            with st.expander("💡 Cách lấy sessionid nhanh (10 giây)"):
                st.markdown("""
1. Mở [tiktok.com](https://www.tiktok.com) trên trình duyệt máy tính đã đăng nhập.
2. Bấm phím **F12** -> chọn tab **Application** (Ứng dụng).
3. Cột bên trái: **Cookies** -> `https://www.tiktok.com`.
4. Tìm dòng tên **sessionid** -> Copy toàn bộ chuỗi **Value**.
5. Dán vào ô trên rồi bấm **Lưu Phiên Mới**!
""")

            if not is_cloud_env:
                st.divider()
                st.caption("Hoặc trích xuất tự động (nếu chạy Local Chrome):")
                if st.button("⚡ Tự Động Lấy Cookie từ Chrome", width="stretch"):
                    with st.spinner("Đang trích xuất phiên từ Chrome..."):
                        c_res = bot.auto_sync_local_cookies()
                        if c_res:
                            st.success("🎉 Đã lấy Cookie thành công!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning("Chưa tìm thấy phiên. Hãy bấm 'Đăng nhập' trước!")
            else:
                st.caption("💡 *Đang chạy trên Streamlit Cloud: Vui lòng dán sessionid vào ô trên rồi bấm 'Lưu Phiên Mới'.*")

            st.divider()
            st.caption("Hoặc trích xuất tự động (nếu chạy Local Chrome):")
            if st.button("⚡ Tự Động Lấy Cookie từ Chrome", width="stretch"):
                with st.spinner("Đang trích xuất phiên từ Chrome..."):
                    c_res = bot.auto_sync_local_cookies()
                    if c_res:
                        st.success("🎉 Đã lấy Cookie thành công!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning("Chưa tìm thấy phiên. Hãy bấm 'Đăng nhập' trước!")

    st.write("")
    st.markdown("#### ☁️ Supabase Cloud DB")
    from src.storage.supabase_client import (
        get_supabase_config,
        save_supabase_config,
        is_supabase_configured,
        test_supabase_connection,
    )
    supa_ok = is_supabase_configured()
    supa_badge = "🟢 Đã kết nối" if supa_ok else "⚪ Chưa cấu hình"
    pop_supa = st.popover(f"☁️ Supabase ({supa_badge})", width="stretch")
    with pop_supa:
        st.markdown("**Kết Nối Supabase Database**")
        st.caption("Lưu trữ danh sách chuỗi, cookie và mật khẩu vĩnh viễn trên Cloud.")
        cur_u, cur_k = get_supabase_config()
        with st.form("supa_form"):
            new_u = st.text_input("Project URL:", value=cur_u, placeholder="https://xxx.supabase.co")
            new_k = st.text_input("Anon / Public Key:", value=cur_k, type="password", placeholder="eyJhbGciOi...")
            sub_supa = st.form_submit_button("💾 Lưu Cấu Hình", width="stretch", type="primary")
            if sub_supa:
                save_supabase_config(new_u, new_k)
                st.success("Đã lưu thông tin Supabase!")
                time.sleep(0.5)
                st.rerun()

        if is_supabase_configured():
            if st.button("🔌 Kiểm tra kết nối", width="stretch"):
                with st.spinner("Đang ping Supabase..."):
                    ok_conn, msg_conn = test_supabase_connection()
                    if ok_conn:
                        st.success(msg_conn)
                    else:
                        st.warning(msg_conn)

        with st.expander("📋 Lệnh SQL tạo bảng (Chỉ cần chạy 1 lần)"):
            st.code("""create table if not exists tiktok_suite_storage (
    key text primary key,
    value jsonb,
    updated_at timestamp with time zone default now()
);
alter table tiktok_suite_storage enable row level security;
create policy "Allow all operations for anon" on tiktok_suite_storage for all using (true) with check (true);""", language="sql")


# ---------------------------------------------------------------------------
# TIÊU ĐỀ CHÍNH: GỌN GÀNG, KHÔNG ĐẨY SÂU NỘI DUNG
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <h1 class="hero-title">TikTok Streak Master 🔥</h1>
    <p class="hero-desc">Bảng điều khiển tự động giữ chuỗi TikTok & Thu thập dữ liệu video, bình luận thông minh</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "🌐 Khám Phá Full API - RAW JSON",
    "🔥 Quản Lý Giữ Chuỗi (Streak & Hú Hú)",
    "📥 Cào Dữ Liệu Video & Bình Luận",
    "📊 Thống Kê & Phân Tích Dữ Liệu",
])

# ---------------------------------------------------------------------------
# TAB 0: API EXPLORER
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("🌐 TikTok Full API Explorer - Trích Xuất & Xuất RAW JSON")
    st.caption("Truy vấn trực tiếp toàn bộ Endpoint API chính thống & gateway công khai của TikTok. Hiển thị cây JSON đầy đủ và tải file JSON chỉ với 1 cú click.")

    api_choice = st.selectbox(
        "Chọn Endpoint API TikTok cần lấy JSON:",
        [
            "1. Item Detail (Video full specs, MP4 no-watermark, Music MP3, Stats)",
            "2. Comment List (Toàn bộ bình luận, Tác giả, Like count, Cursor)",
            "3. Comment Reply (Bình luận con / Phản hồi tầng 2)",
            "4. User Profile (Hồ sơ Creator, Tích xanh, Lượt follow, Giỏ hàng Shop)",
            "5. Search API (Tìm kiếm Video hoặc Creator theo từ khoá)",
            "6. Live Room Webcast (Thông tin Livestream, Phòng Live)",
        ],
    )

    c_p1, c_p2 = st.columns([3, 1], vertical_alignment="bottom")
    with c_p1:
        if "4." in api_choice:
            placeholder_text = "ví dụ: khaby.lame hoặc @khaby.lame"
        elif "5." in api_choice:
            placeholder_text = "ví dụ: nấu ăn, hài hước, trending"
        elif "6." in api_choice:
            placeholder_text = "ví dụ: username live hoặc room_id"
        else:
            placeholder_text = "ví dụ: https://www.tiktok.com/@scout2015/video/6718335390845095173 hoặc 6718335390845095173"
        in_val = st.text_input("Nhập tham số (URL Video / Video ID / Username / Từ khoá):", placeholder=placeholder_text)
    with c_p2:
        b_call = st.button("🚀 Lấy API & Xuất JSON", type="primary", width="stretch")

    if b_call:
        if not in_val.strip():
            st.error("❌ Vui lòng nhập tham số!")
        else:
            with st.spinner("⏳ Đang gửi request tới TikTok API Hub..."):
                raw_res = {}
                p_clean = in_val.strip()
                if "1." in api_choice:
                    raw_res = query_video_full_api(p_clean)
                elif "2." in api_choice:
                    raw_res = query_comments_full_api(p_clean, count=50)
                elif "3." in api_choice:
                    raw_res = query_comment_replies_api(p_clean, count=20)
                elif "4." in api_choice:
                    raw_res = query_user_profile_api(p_clean)
                elif "5." in api_choice:
                    raw_res = query_search_api(p_clean)
                elif "6." in api_choice:
                    raw_res = query_live_room_api(p_clean)

            if raw_res.get("status") in ["success", "success_oembed"]:
                st.success("✅ Đã nhận thành công dữ liệu JSON từ TikTok!")
            elif raw_res.get("status") == "info":
                st.info(raw_res.get("message", "Đã xử lý yêu cầu."))
            else:
                st.warning(f"⚠️ Kết quả: {raw_res.get('message', 'Không lấy được dữ liệu chi tiết')}")

            cj1, cj2 = st.columns([3, 1], vertical_alignment="center")
            with cj1:
                st.markdown("#### 🌳 Cấu trúc Dữ liệu JSON:")
            with cj2:
                j_bytes = json.dumps(raw_res, ensure_ascii=False, indent=2).encode("utf-8")
                st.download_button("📥 Tải File JSON", data=j_bytes, file_name="tiktok_api_response.json", mime="application/json", width="stretch")

            st.json(raw_res)

# ---------------------------------------------------------------------------
# TAB 1: QUẢN LÝ GIỮ CHUỖI STREAK
# ---------------------------------------------------------------------------
with tabs[1]:
    if not is_admin():
        st.warning("🔒 **Khu vực giới hạn quyền hạn!**")
        st.info("Tính năng **Giữ Chuỗi & Hú Hú Cá Nhân** chỉ dành riêng cho tài khoản **Admin** để đảm bảo bảo mật tài khoản Chrome cá nhân. Bạn đang đăng nhập với tư cách **Khách (Guest)** nên chỉ có thể dùng các tính năng tra cứu API và Phân tích ở Tab khác.")
    else:
        targets = bot.load_targets()


        # Hàng 4 Metric: đồng đều chiều cao với st.container(border=True)
        k1, k2, k3, k4 = st.columns(4)
        total_friends = len(targets)
        today_str = datetime.now().strftime("%Y-%m-%d")
        sent_today = sum(1 for t in targets if t.get("last_sent", "").startswith(today_str))
        pending_today = total_friends - sent_today

        with k1:
            with st.container(border=True):
                st.metric("Tổng Bạn Bè Giữ Chuỗi", f"{total_friends} người", f"{total_friends} bạn bè")
        with k2:
            with st.container(border=True):
                delta_k2 = f"Đạt {sent_today}/{total_friends}" if total_friends else "Chưa có bạn"
                st.metric("Mình Đã Gửi Hôm Nay", f"{sent_today} người", delta_k2)
        with k3:
            with st.container(border=True):
                if pending_today > 0:
                    delta_k3 = f"Còn {pending_today} người"
                    delta_color = "inverse"
                else:
                    delta_k3 = "Không còn ai chờ"
                    delta_color = "normal"
                st.metric("Chưa Gửi Hôm Nay", f"{pending_today} người", delta_k3, delta_color=delta_color)
        with k4:
            with st.container(border=True):
                val_k4 = "Kích hoạt" if global_scheduler.is_running else "Đang tắt"
                delta_k4 = "Canh gác 23:30" if global_scheduler.is_running else "Chưa bật"
                st.metric("Vệ Tinh 23h30 Đêm", val_k4, delta_k4)

        st.write("")

        # Tiêu đề danh sách
        st.markdown("<h3 style='margin:0 0 8px 0;'>📋 Danh Sách Mục Tiêu Giữ Chuỗi</h3>", unsafe_allow_html=True)

        # Thanh nút hành động nhanh đồng đều và thoáng mắt
        col_act_scan, col_act_check_all, col_act2, col_act_backup, col_act3 = st.columns([1.5, 1.3, 1.2, 1.0, 0.8], vertical_alignment="center")
        with col_act_scan:
            btn_scan_all = st.button("🔄 Quét Bạn Bè (API)", type="secondary", width="stretch", help="Tự động quét danh sách bạn bè và check chuỗi trực tiếp từ TikTok API")
        with col_act_check_all:
            btn_check_all = st.button("🔍 Check tất cả", width="stretch", help="Quét và cập nhật trạng thái toàn bộ danh sách từ TikTok API")
        with col_act2:
            btn_run_all = st.button("⚡ Gửi tất cả", type="primary", width="stretch")
        with col_act_backup:
            pop_bak = st.popover("💾 Sao lưu", width="stretch")
            with pop_bak:
                st.markdown("**Sao Lưu & Khôi Phục Dữ Liệu**")
                st.caption("Dùng khi deploy lại hoặc tải về máy cá nhân.")
                json_data = json.dumps(targets, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Tải file Backup (.json)",
                    data=json_data,
                    file_name="streak_targets_backup.json",
                    mime="application/json",
                    width="stretch",
                )
                st.divider()
                st.markdown("**Khôi phục từ file Backup:**")
                up_f = st.file_uploader("Chọn file json backup:", type=["json"], label_visibility="collapsed")
                if up_f is not None:
                    try:
                        restored = json.load(up_f)
                        if isinstance(restored, list):
                            if st.button("Nạp danh sách này", type="primary", width="stretch"):
                                bot.save_targets(restored)
                                st.success("Khôi phục thành công!")
                                st.rerun()
                        else:
                            st.error("File JSON không hợp lệ.")
                    except Exception as ef:
                        st.error(f"Lỗi đọc file: {ef}")
        with col_act3:
            # Nút phụ Xoá hết có popover xác nhận an toàn
            pop_clear = st.popover("🗑️ Xoá", width="stretch")
            with pop_clear:
                st.markdown("**Xác nhận xoá toàn bộ?**")
                st.caption("Thao tác này sẽ xoá sạch danh sách bạn bè hiện tại.")
                btn_clear_confirm = st.button("Đồng ý xoá sạch", type="primary", width="stretch")
                if btn_clear_confirm:
                    bot.save_targets([])
                    st.toast("Đã xoá toàn bộ danh sách!", icon="🗑️")
                    st.rerun()

        if btn_scan_all:
            with st.spinner("🔄 Đang kết nối TikTok API để quét danh sách bạn bè & check chuỗi..."):
                scan_res = bot.run_scan_friends_sync()
                if scan_res.get("success"):
                    tot = scan_res.get("total_scanned", 0)
                    new_n = scan_res.get("new_added", 0)
                    upd_n = scan_res.get("updated", 0)
                    st.toast(f"Đã quét thành công {tot} bạn bè từ TikTok API!", icon="🔥")
                    st.success(f"🎉 **Đã quét thành công từ TikTok API!** Phát hiện **{tot}** bạn bè (Thêm mới: **{new_n}**, Cập nhật chuỗi: **{upd_n}**).")
                    time.sleep(1.2)
                    st.rerun()
                else:
                    reason = scan_res.get("reason", "Vui lòng kiểm tra Cookie / Session ID.")
                    st.warning(f"⚠️ Không thể quét từ TikTok API: {reason}")

        # Form thêm bạn bè: thu gọn thành 1 hàng Username | Câu nhắn | Nút Lưu
        with st.expander("➕ Thêm bạn bè & Quét tự động từ TikTok API", expanded=(len(targets) == 0)):
            btn_auto_scan_friends = st.button(
                "⚡ Tự Động Quét & Nhận Diện Chuỗi Toàn Bộ Bạn Bè Từ TikTok API (1 Click)",
                type="primary",
                use_container_width=True,
                help="Tự động trích xuất toàn bộ bạn bè và chuỗi streak từ TikTok API vào danh sách",
            )
            if btn_auto_scan_friends:
                with st.spinner("🔄 Đang kết nối TikTok API để quét danh sách bạn bè & check chuỗi..."):
                    scan_res = bot.run_scan_friends_sync()
                    if scan_res.get("success"):
                        tot = scan_res.get("total_scanned", 0)
                        new_n = scan_res.get("new_added", 0)
                        upd_n = scan_res.get("updated", 0)
                        st.toast(f"Đã cập nhật {tot} bạn bè từ TikTok API!", icon="🔥")
                        st.success(f"🎉 **Đã quét thành công từ TikTok API!** Phát hiện **{tot}** bạn bè (Thêm mới: **{new_n}**, Cập nhật chuỗi: **{upd_n}**).")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        reason = scan_res.get("reason", "Vui lòng kiểm tra Cookie / Session ID.")
                        st.warning(f"⚠️ Không thể quét từ TikTok API: {reason}")
            st.divider()
            with st.form("add_friend_form", clear_on_submit=True):
                fc1, fc2, fc3 = st.columns([2.5, 3.5, 1.5], vertical_alignment="bottom")
                with fc1:
                    username_in = st.text_input("Username TikTok (không cần @):", placeholder="ví dụ: ban_than_123")
                with fc2:
                    custom_msg_in = st.text_input("Tin nhắn hàng ngày (mặc định gửi icon 🔥):", placeholder="Ví dụ: Giữ chuỗi nè bạn ơi 🔥")
                with fc3:
                    submit_add = st.form_submit_button("Thêm ngay", type="primary", width="stretch")

                # Mẫu hú hú mở rộng tuỳ chọn nếu muốn tuỳ biến sâu
                with st.expander("⚙️ Cài đặt mẫu câu spam hú hú riêng (Mỗi câu 1 dòng - không bắt buộc)"):
                    st.caption("💡 *Nếu để trống, bot sẽ tự động lấy kho 16 câu hú hú thông minh mặc định (từ nhắc nhẹ đến đe dọa troll hài hước).*")
                    sample_placeholder = (
                        "HÚ HÚ gửi chuỗi đi má ơi 🔥🔥🔥\n"
                        "Sắp qua 12h đêm rồi má ơi mau gửi chuỗi đi 🔥😱\n"
                        "Đứt chuỗi là tao qua nhà kiếm chuyện đó nha 🚨👊\n"
                        "Dậy gửi chuỗi rồi ngủ tiếp người anh em ơi 😴🔥\n"
                        "Chỉ cần gửi 1 dấu chấm thôi cũng được cứu chuỗi đi! 🆘🔥"
                    )
                    custom_spams_in = st.text_area(
                        "Mẫu hú hú riêng:",
                        placeholder=sample_placeholder,
                        height=95,
                        label_visibility="collapsed",
                    )

                if submit_add:
                    clean_name = username_in.strip().replace("@", "")
                    if clean_name:
                        if any(t["username"].lower() == clean_name.lower() for t in targets):
                            st.warning(f"@{clean_name} đã có trong danh sách!")
                        else:
                            spam_lines = [s.strip() for s in custom_spams_in.split("\n") if s.strip()] if custom_spams_in else None
                            new_entry = {
                                "username": clean_name,
                                "custom_msg": custom_msg_in.strip() if custom_msg_in.strip() else None,
                                "spam_messages": spam_lines,
                                "streak_count": 0,
                                "friend_replied": False,
                                "last_sent": "Chưa gửi",
                                "status": "Ready",
                            }
                            # Tự động soi và kiểm tra chuỗi ngay lập tức khi vừa thêm
                            try:
                                check_res = bot.run_check_sync(clean_name)
                                if check_res.get("checked"):
                                    new_entry["status"] = check_res.get("status_desc")
                                    if "streak_count" in check_res:
                                        new_entry["streak_count"] = check_res["streak_count"]
                                    if "friend_replied" in check_res:
                                        new_entry["friend_replied"] = check_res["friend_replied"]
                            except Exception as ex:
                                log.debug("Tự động check khi thêm bạn gặp lỗi: %s", ex)

                            targets.append(new_entry)
                            bot.save_targets(targets)
                            st.success(f"🎉 Đã thêm @{clean_name} và tự động nhận diện chuỗi thành công!")
                            st.rerun()

        if btn_check_all:
            if not targets:
                st.warning("Chưa có bạn bè nào trong danh sách!")
            else:
                progress_holder = st.empty()
                status_holder = st.empty()
                progress = progress_holder.progress(0)

                for idx, t in enumerate(targets):
                    u = t["username"]
                    status_holder.info(f"🔍 Đang check chuỗi từ TikTok API với **@{u}** ({idx+1}/{len(targets)})...")
                    try:
                        res = bot.run_check_sync(u)
                        if res.get("checked"):
                            t["status"] = res.get("status_desc")
                            if "streak_count" in res:
                                t["streak_count"] = res["streak_count"]
                            if "friend_replied" in res:
                                t["friend_replied"] = res["friend_replied"]
                    except Exception as ex:
                        log.warning("Check all error @%s: %s", u, ex)
                    progress.progress((idx + 1) / len(targets))

                bot.save_targets(targets)
                status_holder.success("🎉 Đã kiểm tra xong toàn bộ bạn bè từ TikTok API!")
                time.sleep(1)
                st.rerun()

        if btn_run_all:
            if not targets:
                st.warning("Chưa có bạn bè nào trong danh sách!")
            else:
                progress_holder = st.empty()
                status_holder = st.empty()
                progress = progress_holder.progress(0)

                for idx, t in enumerate(targets):
                    u = t["username"]
                    m = t.get("custom_msg")
                    status_holder.info(f"⏳ Đang gửi tin nhắn giữ chuỗi tới **@{u}** ({idx+1}/{len(targets)})...")
                    try:
                        success = bot.run_send_sync(u, m)
                        if success:
                            t["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            t["status"] = "Thành công 🔥"
                            st.toast(f"Đã gửi chuỗi tới @{u}", icon="🔥")
                        else:
                            t["status"] = "Thất bại ❌"
                    except Exception as ex:
                        t["status"] = f"Lỗi: {ex}"

                    progress.progress((idx + 1) / len(targets))
                    time.sleep(1)

                bot.save_targets(targets)
                status_holder.success("🎉 Đã hoàn tất đợt gửi chuỗi!")
                time.sleep(1)
                st.rerun()

        # Hiển thị danh sách bạn bè dạng thẻ Card chuyên nghiệp (Responsive & Không tràn viền)
        st.write("")
        if targets:
            for idx, t in enumerate(targets):
                with st.container(border=True):
                    col_info, col_actions = st.columns([5.2, 4.8], vertical_alignment="center")

                    # Phần 1: Thông tin người dùng & Trạng thái
                    with col_info:
                        sc = t.get("streak_count", 0)
                        flame = f" 🔥`{sc} ngày`" if sc else ""
                        status_text = t.get("status", "Ready")
                        if any(k in status_text for k in ["Thành công", "Đã Rep", "Đang giữ chuỗi", "Đang có chuỗi", "Đã kết nối", "hôm nay! ✅"]):
                            badge_cls = "badge-success"
                        elif any(k in status_text for k in ["Thất bại", "Lỗi", "gián đoạn", "Không tìm thấy"]):
                            badge_cls = "badge-danger"
                        else:
                            badge_cls = "badge-warning"

                        nick_disp = f" ({t.get('nickname')})" if t.get("nickname") and t.get("nickname") != t["username"] else ""
                        st.markdown(
                            f"<div style='display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:4px;'>"
                            f"<span style='font-size:1.05rem; font-weight:700;'>@{t['username']}{nick_disp}</span>"
                            f"{flame}"
                            f"<span class='status-badge {badge_cls}'>{status_text}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        msg_display = t.get("custom_msg") or "Mặc định (Icon 🔥)"
                        last_sent_val = t.get("last_sent", "Chưa gửi")
                        st.caption(f"💬 Tin: `{msg_display}` • 🕒 Lần gửi cuối: `{last_sent_val}`")

                    # Phần 2: 5 nút hành động rộng rãi, không bao giờ bị cắt chữ
                    with col_actions:
                        b_chk, b_snd, b_man, b_hu, b_del = st.columns([1.1, 1.0, 1.2, 1.2, 0.5], vertical_alignment="center")
                        with b_chk:
                            if st.button("🔍 Check", key=f"check_{idx}", help="Kiểm tra chuỗi từ TikTok API", width="stretch"):
                                with st.spinner(f"Đang check chuỗi từ TikTok API với @{t['username']}..."):
                                    try:
                                        check_res = bot.run_check_sync(t["username"])
                                        if check_res.get("checked"):
                                            t["status"] = check_res.get("status_desc")
                                            if "streak_count" in check_res:
                                                t["streak_count"] = check_res["streak_count"]
                                            if check_res.get("friend_replied"):
                                                st.toast(f"@{t['username']}: Đã rep lại!", icon="🎉")
                                                st.success(f"@{t['username']}: {check_res.get('status_desc')}")
                                            else:
                                                st.info(f"@{t['username']}: {check_res.get('status_desc')}")
                                        else:
                                            st.warning(f"@{t['username']}: {check_res.get('status_desc')}")
                                        bot.save_targets(targets)
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as err:
                                        st.error(f"⚠️ {err}")

                        with b_snd:
                            if st.button("🚀 Gửi", key=f"send_{idx}", width="stretch", help="Gửi tự động qua bot"):
                                with st.spinner(f"Đang gửi tới @{t['username']}..."):
                                    ok = bot.run_send_sync(t["username"], t.get("custom_msg"))
                                    if ok:
                                        t["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        t["status"] = "Thành công 🔥"
                                        bot.save_targets(targets)
                                        st.toast(f"Đã gửi thành công tới @{t['username']}!", icon="🔥")
                                        st.rerun()
                                    else:
                                        st.error("Gửi thất bại!")

                        with b_man:
                            if st.button("✋ Đã gửi", key=f"manual_{idx}", help="Bấm vào đây nếu bạn đã gửi chuỗi bằng tay trên điện thoại", width="stretch"):
                                res_m = bot.mark_manual_send(t["username"])
                                if res_m.get("success"):
                                    st.toast(f"Đã ghi nhận bạn gửi chuỗi tới @{t['username']}!", icon="🔥")
                                    st.success(f"@{t['username']}: {res_m.get('status_desc')}")
                                    time.sleep(0.5)
                                    st.rerun()

                        with b_hu:
                            if st.button("📢 HÚ HÚ", key=f"huhu_{idx}", width="stretch", help="Spam nhắc nhở giữ chuỗi"):
                                custom_spams = t.get("spam_messages")
                                with st.spinner(f"🚨 Đang HÚ HÚ @{t['username']}..."):
                                    result = bot.run_spam_huhu_sync(t["username"], custom_spam_list=custom_spams, max_rounds=8)
                                    sent_num = result.get("sent", 0)
                                    replied = result.get("replied", False)
                                    if replied:
                                        t["status"] = f"Đã Rep sau {sent_num} tin! 🎉"
                                        st.balloons()
                                        st.success(f"🎉 Cứu chuỗi thành công! @{t['username']} đã rep sau {sent_num} tin!")
                                    else:
                                        t["status"] = f"Đã Hú ({sent_num} tin) 📢"
                                        st.info(f"Đã gửi {sent_num} tin hú hú tới @{t['username']}.")
                                    bot.save_targets(targets)
                                    time.sleep(1)
                                    st.rerun()

                        with b_del:
                            if st.button("✕", key=f"del_{idx}", help="Xoá bạn này khỏi danh sách", width="stretch"):
                                targets.pop(idx)
                                bot.save_targets(targets)
                                st.toast(f"Đã xoá @{t['username']}", icon="🗑️")
                                st.rerun()
        else:
            st.info("👋 Danh sách hiện đang trống. Hãy thêm bạn bè ở khung phía trên để bắt đầu giữ chuỗi!")


# ---------------------------------------------------------------------------
# TAB 2: CÀO DỮ LIỆU TIKTOK (CẢI TIẾN TRỰC QUAN & HIỆN LOG CHI TIẾT TRÊN UI)
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("📥 Thu thập Dữ liệu TikTok (Bình luận & Video)")

    col_u1, col_u2 = st.columns([3, 1], vertical_alignment="bottom")
    with col_u1:
        target_url = st.text_input("TikTok Video URL", placeholder="https://www.tiktok.com/@username/video/1234567890...")
    with col_u2:
        crawl_target = st.selectbox("Dữ liệu cần cào:", ["Cả Bình Luận & Metadata Video", "Chỉ Bình Luận", "Chỉ Metadata Video"])

    if st.button("🚀 Bắt đầu cào dữ liệu", type="primary"):
        if not target_url or not is_valid_video_url(target_url):
            st.error("❌ URL không hợp lệ! Hãy đảm bảo link có dạng https://www.tiktok.com/@username/video/1234567890")
        else:
            vid_id = extract_video_id(target_url)
            log_container = st.container()
            with log_container:
                st.markdown("##### 📜 Tiến trình cào dữ liệu trực tiếp:")
                status_box = st.empty()
                log_box = st.empty()
                logs_history = []

                def ui_callback(msg: str):
                    logs_history.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                    log_box.code("\n".join(logs_history[-10:]), language="bash")
                    status_box.info(msg)

                # 1. Cào Metadata Video nếu chọn
                if "Metadata Video" in crawl_target:
                    try:
                        ui_callback("🎬 Đang trích xuất chỉ số Video (Views, Likes, Shares)...")
                        vinfo = fetch_video_info(target_url)
                        vpath = save_video_info(vinfo)
                        ui_callback(f"✅ Đã lưu Metadata video vào {vpath.name}!")
                    except Exception as ev:
                        ui_callback(f"⚠️ Lỗi lấy metadata video: {ev}")

                # 2. Cào Bình Luận nếu chọn
                if "Bình Luận" in crawl_target:
                    cpath = OUTPUT_DIR / f"comments_{vid_id}.csv"
                    try:
                        ui_callback("💬 Bắt đầu cào bình luận bằng Chrome...")
                        num_saved = collect_comments(target_url, output_path=cpath, max_retries=3, status_callback=ui_callback)
                        if num_saved > 0:
                            status_box.success(f"🎉 Thành công! Đã cào và ẩn danh {num_saved} bình luận vào `{cpath.name}`.")
                            df_new_comments = pd.read_csv(cpath)
                            st.dataframe(df_new_comments.head(20), width="stretch")
                        else:
                            status_box.warning("⚠️ Không tìm thấy bình luận nào (Video có thể đã tắt bình luận hoặc bị TikTok chặn bot ẩn danh. Hãy thử đăng nhập TikTok ở Sidebar trước!).")
                    except Exception as ec:
                        status_box.error(f"❌ Lỗi: {ec}")

# ---------------------------------------------------------------------------
# TAB 3: PHÂN TÍCH
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("📊 Thống Kê & Phân Tích Dữ Liệu Đã Cào")
    st.caption("Xem bảng dữ liệu, các chỉ số tương tác và tải file CSV để nghiên cứu.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfiles = sorted(list(OUTPUT_DIR.glob("*.csv")), key=lambda p: p.stat().st_mtime, reverse=True)
    if cfiles:
        col_f1, col_f2 = st.columns([3, 1], vertical_alignment="bottom")
        with col_f1:
            chosen = st.selectbox("Chọn tệp dữ liệu CSV đã lưu:", [f.name for f in cfiles])
        with col_f2:
            chosen_path = OUTPUT_DIR / chosen
            csv_data = chosen_path.read_bytes()
            st.download_button(
                "📥 Tải file CSV",
                data=csv_data,
                file_name=chosen,
                mime="text/csv",
                width="stretch",
            )

        df = pd.read_csv(chosen_path)
        m1, m2, m3 = st.columns(3)
        with m1:
            with st.container(border=True):
                st.metric("Tổng Số Dòng / Bản Ghi", f"{len(df):,} dòng")
        with m2:
            with st.container(border=True):
                st.metric("Dung Lượng File", f"{len(csv_data) / 1024:.1f} KB")
        with m3:
            with st.container(border=True):
                st.metric("Số Cột Thuộc Tính", f"{len(df.columns)} cột")

        st.dataframe(df, width="stretch")
    else:
        st.info("Chưa có tệp CSV nào trong thư mục data/. Hãy thực hiện cào dữ liệu ở Tab bên cạnh trước!")