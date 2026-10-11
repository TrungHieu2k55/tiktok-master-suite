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

    # Nhóm Hẹn giờ tự động
    st.markdown("#### 🌙 Vệ tinh ban đêm")
    auto_sched = st.toggle("Tự động hú hú lúc 23:30", value=global_scheduler.is_running)
    if auto_sched != global_scheduler.is_running:
        if auto_sched:
            global_scheduler.start()
            st.toast("Đã bật tự động hẹn giờ!", icon="🌙")
        else:
            global_scheduler.stop()
            st.toast("Đã tắt tự động hẹn giờ!", icon="🛑")
        st.rerun()

    if global_scheduler.is_running:
        st.success("🟢 Bot đang chạy ngầm (08h, 20h, 23h30)")
    else:
        st.caption("⚪ Chế độ hẹn giờ đang tắt")

    st.write("")

    # Nhóm Phiên đăng nhập
    st.markdown("#### 🔐 Phiên đăng nhập")
    has_cookie = bool(bot.load_session_cookie_string())
    if profile_exists or has_cookie:
        st.success("🟢 Đã có phiên TikTok")
    else:
        st.warning("🟡 Chưa có phiên TikTok")

    c_lg1, c_lg2 = st.columns([1.2, 1])
    with c_lg1:
        if st.button("🔑 Đăng nhập", width="stretch", type="secondary", help="Mở Chrome trên máy tính để đăng nhập"):
            with st.spinner("Đang mở Chrome... Hãy đăng nhập và đóng trình duyệt khi xong."):
                bot.run_login_sync()
                st.success("Đã đồng bộ phiên đăng nhập!")
                st.rerun()
    with c_lg2:
        pop_cookie = st.popover("🍪 Cookie", width="stretch")
        with pop_cookie:
            st.markdown("**Nhập Cookie TikTok**")
            st.caption("Dành riêng khi chạy trên Cloud (không có màn hình mở Chrome).")
            with st.form("cookie_form"):
                cookie_in = st.text_area("Dán chuỗi Cookie hoặc sessionid:", placeholder="sessionid=xxxx; ...", height=80)
                sub_cookie = st.form_submit_button("Lưu Cookie", type="primary", width="stretch")
                if sub_cookie and cookie_in.strip():
                    bot.save_session_cookie_string(cookie_in.strip())
                    st.success("Đã lưu Cookie phiên thành công!")
                    st.toast("Đã nạp Cookie TikTok!", icon="🍪")
                    time.sleep(1)
                    st.rerun()


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

        # Hàng tiêu đề danh sách + Hai nút hành động căn giữa dọc
        col_act1, col_act2, col_act3 = st.columns([3, 1.6, 1.2], vertical_alignment="center")
        with col_act1:
            st.markdown("<h3 style='margin:0; padding:0;'>📋 Danh Sách Mục Tiêu Giữ Chuỗi</h3>", unsafe_allow_html=True)
        with col_act2:
            btn_run_all = st.button("⚡ Gửi giữ chuỗi tất cả", type="primary", width="stretch")
        with col_act3:
            # Nút phụ Xoá hết có popover xác nhận an toàn
            pop_clear = st.popover("🗑️ Xoá hết", width="stretch")
            with pop_clear:
                st.markdown("**Xác nhận xoá toàn bộ?**")
                st.caption("Thao tác này sẽ xoá sạch danh sách bạn bè hiện tại.")
                btn_clear_confirm = st.button("Đồng ý xoá sạch", type="primary", width="stretch")
                if btn_clear_confirm:
                    bot.save_targets([])
                    st.toast("Đã xoá toàn bộ danh sách!", icon="🗑️")
                    st.rerun()

        # Form thêm bạn bè: thu gọn thành 1 hàng Username | Câu nhắn | Nút Lưu
        with st.expander("➕ Thêm bạn bè", expanded=(len(targets) == 0)):
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
                            targets.append({
                                "username": clean_name,
                                "custom_msg": custom_msg_in.strip() if custom_msg_in.strip() else None,
                                "spam_messages": spam_lines,
                                "last_sent": "Chưa gửi",
                                "status": "Ready",
                            })
                            bot.save_targets(targets)
                            st.success(f"Đã thêm @{clean_name} thành công!")
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

        # Hiển thị danh sách bạn bè chuẩn dạng bảng
        st.write("")
        if targets:
            # Hàng tiêu đề cột
            th1, th2, th3, th4, th5 = st.columns([1.8, 2.0, 1.6, 1.8, 2.8], vertical_alignment="center")
            with th1:
                st.markdown("<div class='table-col-header'>Tài Khoản</div>", unsafe_allow_html=True)
            with th2:
                st.markdown("<div class='table-col-header'>Tin Nhắn</div>", unsafe_allow_html=True)
            with th3:
                st.markdown("<div class='table-col-header'>Lần Gửi Cuối</div>", unsafe_allow_html=True)
            with th4:
                st.markdown("<div class='table-col-header'>Trạng Thái</div>", unsafe_allow_html=True)
            with th5:
                st.markdown("<div class='table-col-header' style='text-align:right; padding-right:12px;'>Hành Động</div>", unsafe_allow_html=True)

            for idx, t in enumerate(targets):
                with st.container(border=True):
                    r1, r2, r3, r4, r_check, r5, r6, r7 = st.columns([1.8, 2.0, 1.6, 1.8, 0.9, 0.9, 0.9, 0.4], vertical_alignment="center")

                    # Cột 1: Username
                    with r1:
                        st.markdown(f"**@{t['username']}**")

                    # Cột 2: Tin nhắn
                    with r2:
                        msg_display = t.get("custom_msg") or "Mặc định (Icon 🔥)"
                        st.caption(f"`{msg_display}`")

                    # Cột 3: Lần gửi cuối
                    with r3:
                        st.caption(f"🕒 {t.get('last_sent', 'Chưa gửi')}")

                    # Cột 4: Trạng thái chuẩn màu sắc
                    with r4:
                        status_text = t.get("status", "Ready")
                        if "Thành công" in status_text or "Đã Rep" in status_text:
                            badge_cls = "badge-success"
                        elif "Thất bại" in status_text or "Lỗi" in status_text:
                            badge_cls = "badge-danger"
                        else:
                            badge_cls = "badge-warning"
                        st.markdown(f'<span class="status-badge {badge_cls}">{status_text}</span>', unsafe_allow_html=True)

                    # Nút Soi / Check Chuỗi Tự Động
                    with r_check:
                        if st.button("🔍 Check", key=f"check_{idx}", help="Kiểm tra đối phương đã gửi chuỗi lại chưa", width="stretch"):
                            with st.spinner(f"Đang kiểm tra cuộc trò chuyện với @{t['username']}..."):
                                try:
                                    check_res = bot.run_check_sync(t["username"])
                                    if check_res.get("checked"):
                                        t["status"] = check_res.get("status_desc")
                                        if check_res.get("friend_replied"):
                                            st.success(f"@{t['username']}: {check_res.get('status_desc')}")
                                        else:
                                            st.warning(f"@{t['username']}: {check_res.get('status_desc')}")
                                    else:
                                        st.error(f"Lỗi kiểm tra: {check_res.get('status_desc')}")
                                    bot.save_targets(targets)
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"⚠️ {err}")

                    # Cột 5: Nút Gửi
                    with r5:
                        if st.button("🚀 Gửi", key=f"send_{idx}", width="stretch"):
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

                    # Cột 6: Nút HÚ HÚ
                    with r6:
                        if st.button("📢 HÚ HÚ", key=f"huhu_{idx}", width="stretch"):
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

                    # Cột 7: Nút Xoá dạng icon nhỏ
                    with r7:
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