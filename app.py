"""
app.py — TikTok Suite Master 🔥 (All-in-One Dashboard)
- TikTok Streak Automation & Smart Hú Hú Spam
- TikTok Full API Explorer & RAW JSON Inspector
- Fast & Headless Data Collector (Comments & Metadata)
- Interactive Data Analytics & Export
"""
import json
import os
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
from src.ui.theme import inject_css
from src.ui.auth import render_login_screen, is_authenticated, is_admin, get_current_user, logout, update_admin_password
from src.utils.validators import extract_video_id, is_valid_video_url

# 1. Cấu hình trang với layout wide
st.set_page_config(
    page_title="TikTok Suite Master",
    page_icon=":material/bolt:",
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

bot = TikTokStreakBot(headless=True)
profile_exists = (SESSION_DIR / "chrome_tiktok_profile").exists()

# ---------------------------------------------------------------------------
# SIDEBAR: CÀI ĐẶT & TRẠNG THÁI TÀI KHOẢN
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-box">
        <img src="https://upload.wikimedia.org/wikipedia/en/a/a9/TikTok_logo.svg" width="28" />
        <div>
            <div class="sidebar-brand-name">TikTok Suite</div>
            <div class="sidebar-brand-ver">v2.8 • Dashboard tối giản</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KHỐI 1: TÀI KHOẢN
    st.markdown('<div class="sidebar-section-title">Tài khoản</div>', unsafe_allow_html=True)
    with st.container(border=True):
        c_acc_l, c_acc_r = st.columns([3, 2], vertical_alignment="center")
        with c_acc_l:
            st.markdown(f"**{user_name}**")
            chip_role = "chip-success" if is_admin() else "chip-neutral"
            st.markdown(f'<span class="status-chip {chip_role}">{user_role.upper()}</span>', unsafe_allow_html=True)
        with c_acc_r:
            pop_user = st.popover("Cài đặt", use_container_width=True)
            with pop_user:
                st.markdown("**Tài khoản**")
                if st.button("Đăng xuất", use_container_width=True, type="secondary", icon=":material/logout:"):
                    logout()
                if is_admin():
                    st.divider()
                    st.markdown("**Đổi mật khẩu Admin**")
                    with st.form("change_admin_pw_form", clear_on_submit=True):
                        new_pw = st.text_input("Mật khẩu mới:", type="password")
                        confirm_pw = st.text_input("Nhập lại mật khẩu:", type="password")
                        sub_pw = st.form_submit_button("Lưu mật khẩu", type="primary", use_container_width=True)
                        if sub_pw:
                            if not new_pw or len(new_pw) < 6:
                                st.error("Mật khẩu phải từ 6 ký tự trở lên!")
                            elif new_pw != confirm_pw:
                                st.error("Mật khẩu xác nhận không khớp!")
                            else:
                                if update_admin_password(new_pw):
                                    st.success("Đổi mật khẩu thành công!")
                                    st.toast("Đã lưu mật khẩu Admin mới!", icon=":material/key:")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Lỗi khi lưu mật khẩu mới!")

    st.write("")

    # KHỐI 2: GIỜ HẸN & BÁO ĐỘNG
    from src.streak.scheduler import load_scheduler_config, save_scheduler_config
    sched_cfg = load_scheduler_config()
    st.markdown('<div class="sidebar-section-title">Giờ hẹn tự động</div>', unsafe_allow_html=True)
    with st.container(border=True):
        auto_sched = st.toggle("Canh gác ngầm", value=global_scheduler.is_running)
        if auto_sched != global_scheduler.is_running:
            if auto_sched:
                global_scheduler.start()
                st.toast("Đã kích hoạt canh gác ngầm!", icon=":material/alarm_on:")
            else:
                global_scheduler.stop()
                st.toast("Đã tạm dừng canh gác!", icon=":material/alarm_off:")
            st.rerun()

        hrs_str = ", ".join([f"{h:02d}h" for h in sched_cfg.get("streak_hours", [8, 20])])
        hh_str = sched_cfg.get("huhu_time", "23:30")
        if global_scheduler.is_running:
            st.markdown(f'<div class="connection-status"><span class="status-dot dot-success"></span> Đang chạy: {hrs_str} • Hú {hh_str}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="connection-status"><span class="status-dot dot-neutral"></span> Đang tạm dừng</div>', unsafe_allow_html=True)

        with st.expander("Cài đặt khung giờ"):
            with st.form("custom_sched_form"):
                h1 = st.number_input("Khung giờ sáng:", min_value=0, max_value=23, value=sched_cfg.get("streak_hours", [8, 20])[0] if len(sched_cfg.get("streak_hours", [8, 20])) > 0 else 8, step=1)
                h2 = st.number_input("Khung giờ tối:", min_value=0, max_value=23, value=sched_cfg.get("streak_hours", [8, 20])[1] if len(sched_cfg.get("streak_hours", [8, 20])) > 1 else 20, step=1)
                huhu_time_val = st.text_input("Giờ khẩn cấp Hú Hú:", value=sched_cfg.get("huhu_time", "23:30"))
                sub_sched = st.form_submit_button("Lưu cài đặt", use_container_width=True, type="primary")
                if sub_sched:
                    sched_cfg["streak_hours"] = sorted(list(set([int(h1), int(h2)])))
                    sched_cfg["huhu_time"] = huhu_time_val.strip() if huhu_time_val.strip() else "23:30"
                    save_scheduler_config(sched_cfg)
                    st.success("Đã cập nhật khung giờ!")
                    time.sleep(0.5)
                    st.rerun()

    st.write("")

    # KHỐI 3: KẾT NỐI (TIKTOK & SUPABASE)
    st.markdown('<div class="sidebar-section-title">Kết nối dịch vụ</div>', unsafe_allow_html=True)
    with st.container(border=True):
        saved_cookie = bot.load_session_cookie_string()
        health_res = bot.check_session_health() if saved_cookie else {"status": "none", "valid": False, "expired": False}
        is_cloud_env = bool(os.environ.get("STREAMLIT_SERVER_PORT") or (os.name != "nt"))

        # Dòng 1: TikTok Session Status
        if health_res.get("expired"):
            tk_dot = "dot-danger"
            tk_text = "Hết hạn"
        elif health_res.get("valid"):
            tk_dot = "dot-success"
            u_tag = health_res.get("username")
            tk_text = f"Hoạt động (@{u_tag})" if u_tag else "Hoạt động"
        elif profile_exists:
            tk_dot = "dot-success"
            tk_text = "Chrome Local"
        else:
            tk_dot = "dot-warning"
            tk_text = "Chưa kết nối"

        st.markdown(f'''
        <div class="connection-row">
            <span>TikTok Session</span>
            <span class="connection-status"><span class="status-dot {tk_dot}"></span> {tk_text}</span>
        </div>
        ''', unsafe_allow_html=True)

        col_tk1, col_tk2 = st.columns([1, 1])
        with col_tk1:
            pop_cookie = st.popover("Quản lý phiên", use_container_width=True)
            with pop_cookie:
                st.markdown("**Phiên đăng nhập TikTok**")
                if health_res.get("expired"):
                    st.error("Phiên hiện tại đã hết hạn (Session Expired). Vui lòng cập nhật sessionid mới:")
                elif health_res.get("valid"):
                    u_n = health_res.get("username", "")
                    st.success(f"Tài khoản kết nối: **@{u_n}**")
                    if st.button("Xóa phiên này", use_container_width=True, type="secondary"):
                        bot.save_session_cookie_string("")
                        st.rerun()
                elif saved_cookie:
                    preview = (saved_cookie[:25] + "...") if len(saved_cookie) > 25 else saved_cookie
                    st.info(f"Đang dùng: `{preview}`")
                    if st.button("Xóa phiên này", use_container_width=True, type="secondary"):
                        bot.save_session_cookie_string("")
                        st.rerun()
                else:
                    st.caption("Chưa có cookie phiên.")

                with st.form("cookie_form"):
                    cookie_in = st.text_area("Chuỗi Cookie / sessionid:", placeholder="sessionid=xxxx; ...", height=70)
                    sub_cookie = st.form_submit_button("Lưu phiên mới", type="primary", use_container_width=True)
                    if sub_cookie and cookie_in.strip():
                        bot.save_session_cookie_string(cookie_in.strip())
                        health_chk = bot.check_session_health()
                        if health_chk.get("valid"):
                            st.toast(f"Đã kết nối tài khoản @{health_chk.get('username')}!", icon=":material/check:")
                        st.rerun()

                with st.expander("Cách lấy sessionid (10 giây)"):
                    st.markdown('''
1. Mở [tiktok.com](https://www.tiktok.com) trên trình duyệt đã đăng nhập.
2. Bấm phím **F12** -> chọn tab **Application**.
3. Cột trái: **Cookies** -> `https://www.tiktok.com`.
4. Tìm dòng **sessionid** -> Copy toàn bộ chuỗi Value.
5. Dán vào ô trên và bấm **Lưu phiên mới**.
''')
        with col_tk2:
            if is_cloud_env:
                st.button("Đăng nhập", use_container_width=True, type="secondary", disabled=True, help="Đăng nhập tự động chỉ chạy trên máy tính cá nhân")
            else:
                if st.button("Đăng nhập", use_container_width=True, type="secondary", help="Mở Chrome trên máy để đăng nhập"):
                    with st.spinner("Đang mở Chrome..."):
                        bot.run_login_sync()
                        st.rerun()

        st.divider()

        # Dòng 2: Supabase Status
        from src.storage.supabase_client import (
            get_supabase_config,
            save_supabase_config,
            is_supabase_configured,
            test_supabase_connection,
        )
        supa_ok = is_supabase_configured()
        supa_dot = "dot-success" if supa_ok else "dot-neutral"
        supa_text = "Đã kết nối" if supa_ok else "Chưa cấu hình"

        st.markdown(f'''
        <div class="connection-row">
            <span>Supabase Cloud</span>
            <span class="connection-status"><span class="status-dot {supa_dot}"></span> {supa_text}</span>
        </div>
        ''', unsafe_allow_html=True)

        pop_supa = st.popover("Cấu hình Supabase", use_container_width=True)
        with pop_supa:
            st.markdown("**Supabase Cloud Database**")
            st.caption("Lưu trữ danh sách chuỗi, cookie và cấu hình an toàn trên Cloud.")
            cur_u, cur_k = get_supabase_config()
            with st.form("supa_form"):
                new_u = st.text_input("Project URL:", value=cur_u, placeholder="https://xxx.supabase.co")
                new_k = st.text_input("Anon Key:", value=cur_k, type="password", placeholder="eyJhbGciOi...")
                sub_supa = st.form_submit_button("Lưu cấu hình", use_container_width=True, type="primary")
                if sub_supa:
                    save_supabase_config(new_u, new_k)
                    st.success("Đã lưu thông tin!")
                    time.sleep(0.5)
                    st.rerun()

            if is_supabase_configured():
                if st.button("Kiểm tra kết nối", use_container_width=True, type="secondary"):
                    with st.spinner("Đang kiểm tra kết nối..."):
                        ok_conn, msg_conn = test_supabase_connection()
                        if ok_conn:
                            st.success(msg_conn)
                        else:
                            st.warning(msg_conn)

            with st.expander("Lệnh SQL khởi tạo bảng"):
                st.code('''create table if not exists tiktok_suite_storage (
    key text primary key,
    value jsonb,
    updated_at timestamp with time zone default now()
);
alter table tiktok_suite_storage enable row level security;
create policy "Allow all operations for anon" on tiktok_suite_storage for all using (true) with check (true);''', language="sql")


# ---------------------------------------------------------------------------
# TIÊU ĐỀ CHÍNH: GIAO DIỆN SAAS TỐI GIẢN
# ---------------------------------------------------------------------------
bot_status_chip = '<span class="status-chip chip-success"><span class="status-dot dot-success"></span> Đang canh gác</span>' if global_scheduler.is_running else '<span class="status-chip chip-neutral"><span class="status-dot dot-neutral"></span> Tạm dừng</span>'

st.markdown(f'''
<div class="saas-header">
    <div class="saas-header-left">
        <h1 class="saas-header-title">TikTok Streak Suite</h1>
        <p class="saas-header-desc">Hệ thống tự động hoá giữ chuỗi TikTok & Phân tích dữ liệu API</p>
    </div>
    <div>
        {bot_status_chip}
    </div>
</div>
''', unsafe_allow_html=True)

tabs = st.tabs([
    "Quản lý giữ chuỗi",
    "Thu thập dữ liệu",
    "Thống kê & Phân tích",
    "Nâng cao (RAW JSON)",
])

# ---------------------------------------------------------------------------
# TAB 0: QUẢN LÝ GIỮ CHUỖI STREAK
# ---------------------------------------------------------------------------
with tabs[0]:
    if not is_admin():
        st.warning("🔒 **Khu vực giới hạn quyền hạn!**")
        st.info("Tính năng **Giữ Chuỗi & Hú Hú Cá Nhân** chỉ dành riêng cho tài khoản **Admin** để đảm bảo bảo mật tài khoản Chrome cá nhân. Bạn đang đăng nhập với tư cách **Khách (Guest)** nên chỉ có thể dùng các tính năng tra cứu API và Phân tích ở Tab khác.")
    else:
        targets = bot.load_targets()


        # Hàng 4 Thẻ Metric SaaS đồng đều
        k1, k2, k3, k4 = st.columns(4)
        total_friends = len(targets)
        today_str = datetime.now().strftime("%Y-%m-%d")
        sent_today = sum(1 for t in targets if t.get("last_sent", "").startswith(today_str))
        pending_today = total_friends - sent_today

        with k1:
            with st.container(border=True):
                st.metric("Mục tiêu đang theo dõi", f"{total_friends}", f"{total_friends} bạn bè", delta_color="normal")
        with k2:
            with st.container(border=True):
                delta_k2 = f"{sent_today}/{total_friends} hoàn thành" if total_friends else "Chưa có mục tiêu"
                st.metric("Đã gửi hôm nay", f"{sent_today}", delta_k2, delta_color="normal" if sent_today > 0 else "off")
        with k3:
            with st.container(border=True):
                if pending_today > 0:
                    delta_k3 = f"Còn {pending_today} cần gửi"
                    delta_color = "inverse"
                else:
                    delta_k3 = "Đã gửi toàn bộ"
                    delta_color = "normal"
                st.metric("Chưa gửi hôm nay", f"{pending_today}", delta_k3, delta_color=delta_color)
        with k4:
            with st.container(border=True):
                val_k4 = "Đang chạy" if global_scheduler.is_running else "Đang tắt"
                delta_k4 = "Tự động 23:30" if global_scheduler.is_running else "Tạm dừng"
                st.metric("Canh gác ban đêm", val_k4, delta_k4, delta_color="normal" if global_scheduler.is_running else "off")

        st.write("")

        st.write("")
        c_title_l, c_title_r = st.columns([1, 1], vertical_alignment="center")
        with c_title_l:
            st.markdown("#### Mục tiêu giữ chuỗi")
        with c_title_r:
            pass

        # Thanh công cụ SaaS: Gửi tất cả là nút chính nổi bật, các nút còn lại là outline/menu
        col_act_main, col_act_scan, col_act_check_all, col_act_more = st.columns([1.4, 1.4, 1.3, 0.9], vertical_alignment="center")
        with col_act_main:
            btn_run_all = st.button("Gửi tất cả", type="primary", use_container_width=True, icon=":material/send:")
        with col_act_scan:
            btn_scan_all = st.button("Quét hộp thư", type="secondary", use_container_width=True, icon=":material/sync:", help="Tự động quét danh sách hội thoại từ hộp thư TikTok")
        with col_act_check_all:
            btn_check_all = st.button("Kiểm tra tất cả", type="secondary", use_container_width=True, icon=":material/fact_check:", help="Kiểm tra trạng thái rep 2 chiều toàn bộ danh sách")
        with col_act_more:
            pop_more = st.popover("Thêm", use_container_width=True)
            with pop_more:
                st.markdown("**Sao lưu & Khôi phục**")
                json_data = json.dumps(targets, indent=2, ensure_ascii=False)
                st.download_button(
                    label="Tải file sao lưu (.json)",
                    data=json_data,
                    file_name="streak_targets_backup.json",
                    mime="application/json",
                    use_container_width=True,
                    icon=":material/download:",
                )
                st.caption("Khôi phục dữ liệu từ file backup:")
                up_f = st.file_uploader("Chọn file json:", type=["json"], label_visibility="collapsed")
                if up_f is not None:
                    try:
                        restored = json.load(up_f)
                        if isinstance(restored, list):
                            if st.button("Nạp danh sách này", type="primary", use_container_width=True):
                                bot.save_targets(restored)
                                st.success("Khôi phục thành công!")
                                st.rerun()
                        else:
                            st.error("File JSON không hợp lệ.")
                    except Exception as ef:
                        st.error(f"Lỗi: {ef}")
                st.divider()
                st.markdown("**Xoá toàn bộ danh sách**")
                st.caption("Thao tác này sẽ xoá toàn bộ mục tiêu hiện tại.")
                btn_clear_confirm = st.button("Xác nhận xoá sạch", type="secondary", use_container_width=True, icon=":material/delete:")
                if btn_clear_confirm:
                    bot.save_targets([])
                    st.toast("Đã xoá toàn bộ danh sách!", icon=":material/delete:")
                    st.rerun()

        # Xử lý khi bấm nút Quét Hộp Thư Tin Nhắn
        if btn_scan_all or st.session_state.get("trigger_scan_now"):
            if "trigger_scan_now" in st.session_state:
                del st.session_state["trigger_scan_now"]
            with st.spinner("🔄 Đang quét danh sách hội thoại từ hộp thư TikTok (Headless ngầm)..."):
                discovered = bot.scan_inbox_conversations()
                if discovered:
                    st.session_state["scanned_inbox_candidates"] = discovered
                    st.toast(f"Đã tìm thấy {len(discovered)} bạn bè trong hộp thư!", icon="🔍")
                else:
                    st.warning("⚠️ Không tìm thấy cuộc hội thoại nào hoặc phiên Cookie hết hạn. Vui lòng kiểm tra lại sessionid.")

        # HỘP CHỌN BẠN BÈ VỪA QUÉT ĐƯỢC (SELECTIVE IMPORT)
        if "scanned_inbox_candidates" in st.session_state and st.session_state["scanned_inbox_candidates"]:
            candidates = st.session_state["scanned_inbox_candidates"]
            with st.container(border=True):
                st.markdown(f"#### 🎯 Chọn Bạn Bè Cần Giữ Chuỗi (Phát hiện {len(candidates)} người)")
                st.caption("Tick chọn những người bạn muốn giữ chuỗi (bỏ qua các tài khoản shop/quảng cáo), có thể chỉnh số chuỗi ban đầu rồi bấm **Thêm vào danh sách**.")

                col_sa1, col_sa2 = st.columns([1, 1])
                with col_sa1:
                    select_all_btn = st.button("Chọn tất cả", key="btn_sel_all", type="secondary")
                with col_sa2:
                    deselect_all_btn = st.button("Bỏ chọn tất cả", key="btn_desel_all", type="secondary")

                existing_unames = {t.get("username", "").lower() for t in targets}
                selected_data = []

                for idx, c in enumerate(candidates):
                    u = c.get("username", "")
                    nick = c.get("nickname", u)
                    last_msg = c.get("last_msg", "")
                    rep = c.get("friend_replied", False)
                    i_sent = c.get("i_sent", False)
                    is_kept_today = c.get("is_kept_today", False)
                    sc_init = int(c.get("streak_count", 0) or 0)
                    is_already_added = u.lower() in existing_unames

                    # Mặc định tick nếu chưa có và có dấu hiệu chuỗi hoặc người thật
                    def_val = not is_already_added
                    if select_all_btn:
                        def_val = True
                    elif deselect_all_btn:
                        def_val = False

                    col_c1, col_c2, col_c3, col_c4 = st.columns([0.6, 2.5, 3.5, 1.4], vertical_alignment="center")
                    with col_c1:
                        checked = st.checkbox("", value=def_val, key=f"chk_cand_{idx}_{u}", label_visibility="collapsed")
                    with col_c2:
                        if is_kept_today:
                            rep_badge = " • <span style='color:#10b981;font-weight:700;'>Hai bên đã rep, đã giữ chuỗi hôm nay! 🎉✅</span>"
                        elif i_sent and not rep:
                            rep_badge = " • <span style='color:#3b82f6;font-weight:600;'>Bạn đã gửi, chờ bạn kia rep 💬</span>"
                        elif not i_sent and rep:
                            rep_badge = " • <span style='color:#f59e0b;font-weight:600;'>Bạn kia đã rep, bạn chưa gửi! ⚠️</span>"
                        else:
                            rep_badge = " • <span style='color:#6b7280;font-weight:600;'>Cả hai chưa rep hôm nay 💬</span>"

                        already_tag = " <span style='color:#6366f1;font-size:11px;'>(Đã có trong list)</span>" if is_already_added else ""
                        st.markdown(f"**{nick}** (@{u}){already_tag}<br><small>{rep_badge}</small>", unsafe_allow_html=True)
                    with col_c3:
                        msg_preview = last_msg[:50] + "..." if len(last_msg) > 50 else (last_msg or "*(Không có tin nhắn gần)*")
                        st.caption(f"💬 *{msg_preview}*")
                    with col_c4:
                        streak_in = st.number_input("Số chuỗi 🔥:", min_value=0, max_value=9999, value=sc_init, step=1, key=f"num_cand_{idx}_{u}")

                    if checked:
                        selected_data.append({
                            "username": u,
                            "nickname": nick,
                            "streak_count": streak_in,
                            "friend_replied": rep,
                            "i_sent": i_sent,
                            "is_kept_today": is_kept_today,
                            "last_msg": last_msg,
                        })

                col_btn_apply, col_btn_cancel = st.columns([2, 1])
                with col_btn_apply:
                    if st.button(f"✅ Thêm {len(selected_data)} bạn bè đã chọn vào danh sách giữ chuỗi", type="primary", use_container_width=True):
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        added_count = 0
                        updated_count = 0
                        for sel in selected_data:
                            uname = sel["username"]
                            exist = next((t for t in targets if t.get("username", "").lower() == uname.lower()), None)
                            sc = sel["streak_count"]
                            rep = sel["friend_replied"]
                            i_sent = sel.get("i_sent", False)
                            is_kept = sel.get("is_kept_today", False)
                            if is_kept:
                                desc = f"Đang giữ chuỗi {sc} ngày 🔥 • Hai bên đã rep qua lại, đã giữ chuỗi hôm nay! 🎉✅"
                            elif i_sent:
                                desc = f"Đang giữ chuỗi {sc} ngày 🔥 • Bạn đã gửi hôm nay! ✅ • Đang chờ đối phương gửi lại 💬"
                            elif rep:
                                desc = f"Chuỗi {sc} ngày 🔥 • Đối phương đã rep! 💬 • Bạn chưa gửi chuỗi, cần rep trước 23:59! ⚠️"
                            else:
                                desc = f"Chuỗi {sc} ngày 🔥 • Cả hai chưa rep hôm nay • Cần gửi chuỗi trước 23:59! ⚠️"

                            if exist:
                                exist["streak_count"] = sc
                                exist["friend_replied"] = rep
                                exist["nickname"] = sel["nickname"]
                                exist["last_checked"] = now_str
                                exist["status"] = desc
                                updated_count += 1
                            else:
                                targets.append({
                                    "username": uname,
                                    "nickname": sel["nickname"],
                                    "custom_msg": None,
                                    "streak_count": sc,
                                    "friend_replied": rep,
                                    "last_sent": "Chưa gửi",
                                    "status": desc + " [Đã chọn ⚡]",
                                    "last_checked": now_str,
                                    "is_friend": True,
                                })
                                added_count += 1

                        bot.save_targets(targets)
                        del st.session_state["scanned_inbox_candidates"]
                        st.toast(f"Đã thêm {added_count} bạn mới, cập nhật {updated_count} bạn!", icon="🎉")
                        st.success(f"🎉 **Đã lưu thành công!** Đã thêm **{added_count}** bạn mới và cập nhật **{updated_count}** bạn bè vào danh sách giữ chuỗi.")
                        time.sleep(1.2)
                        st.rerun()

                with col_btn_cancel:
                    if st.button("❌ Đóng bảng", use_container_width=True):
                        del st.session_state["scanned_inbox_candidates"]
                        st.rerun()

        # Form thêm bạn bè: thu gọn thành 1 hàng Username | Câu nhắn | Nút Lưu
        with st.expander("➕ Thêm bạn bè & Quét tự động từ TikTok", expanded=(len(targets) == 0)):
            btn_auto_scan_friends = st.button(
                "⚡ Tự Động Quét & Hiện Bảng Chọn Bạn Bè Từ Hộp Thư TikTok (1 Click)",
                type="primary",
                use_container_width=True,
                help="Tự động trích xuất toàn bộ hội thoại từ hộp thư TikTok và hiện bảng cho bạn chọn",
            )
            if btn_auto_scan_friends:
                st.session_state["trigger_scan_now"] = True
                st.rerun()
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

        # Hiển thị danh sách bạn bè dạng Bảng-Thẻ SaaS tối giản
        st.write("")
        if targets:
            now_dt = datetime.now()
            today_prefix = now_dt.strftime("%Y-%m-%d")
            end_of_day_dt = datetime(now_dt.year, now_dt.month, now_dt.day, 23, 59, 59)
            rem_sec_today = max(0, int((end_of_day_dt - now_dt).total_seconds()))
            rem_h = rem_sec_today // 3600
            rem_m = (rem_sec_today % 3600) // 60
            countdown_tag = f"Còn {rem_h}h {rem_m}p"

            for idx, t in enumerate(targets):
                with st.container(border=True):
                    col_user, col_chip, col_primary_act, col_menu = st.columns([3.5, 3.8, 1.4, 0.8], vertical_alignment="center")

                    # Cột 1: Tên hiển thị (đậm) + @username (phụ)
                    with col_user:
                        disp_name = t.get("nickname") or t["username"]
                        user_uname = t["username"]
                        sc = t.get("streak_count", 0)
                        streak_badge = f" • <span style='color:#fe2c55;font-weight:600;'>{sc} ngày</span>" if sc else ""
                        st.markdown(
                            f'<div class="friend-name">{disp_name}<span class="friend-username">@{user_uname}</span>{streak_badge}</div>',
                            unsafe_allow_html=True
                        )
                        msg_display = t.get("custom_msg") or "Mặc định (Icon 🔥)"
                        last_sent_val = t.get("last_sent", "Chưa gửi")
                        st.markdown(
                            f'<div class="friend-meta">Tin: {msg_display} • Gửi cuối: {last_sent_val}</div>',
                            unsafe_allow_html=True
                        )

                    # Cột 2: Chip trạng thái (Đã gửi hôm nay / Chưa gửi / Đối phương đã rep) + Đếm ngược
                    with col_chip:
                        status_str = t.get("status", "")
                        last_sent_str = t.get("last_sent", "")
                        has_sent_today = last_sent_str.startswith(today_prefix) or ("hôm nay! ✅" in status_str) or ("Thành công" in status_str)
                        friend_rep = t.get("friend_replied", False) or ("Đối phương đã rep" in status_str) or ("hai bên đã rep" in status_str.lower())

                        if "hai bên đã rep" in status_str.lower():
                            chip_html = '<span class="status-chip chip-success"><span class="status-dot dot-success"></span> Đã giữ chuỗi hôm nay</span>'
                        elif has_sent_today:
                            if friend_rep:
                                chip_html = '<span class="status-chip chip-success"><span class="status-dot dot-success"></span> Đã gửi • Đối phương đã rep</span>'
                            else:
                                chip_html = '<span class="status-chip chip-success"><span class="status-dot dot-success"></span> Bạn đã gửi hôm nay</span>'
                        elif friend_rep:
                            chip_html = f'<span class="status-chip chip-warning"><span class="status-dot dot-warning"></span> Đối phương đã rep • {countdown_tag}</span>'
                        else:
                            chip_html = f'<span class="status-chip chip-warning"><span class="status-dot dot-warning"></span> Chưa gửi hôm nay • {countdown_tag}</span>'

                        st.markdown(chip_html, unsafe_allow_html=True)

                    # Cột 3: Một nút chính theo ngữ cảnh ("Đã gửi" hoặc "Gửi ngay")
                    with col_primary_act:
                        if has_sent_today:
                            st.button("Đã xong", key=f"done_{idx}", disabled=True, use_container_width=True, icon=":material/check:")
                        else:
                            if st.button("Gửi", key=f"send_main_{idx}", type="primary", use_container_width=True, icon=":material/send:", help="Gửi chuỗi tự động"):
                                with st.spinner(f"Đang gửi tới @{t['username']}..."):
                                    ok = bot.run_send_sync(t["username"], t.get("custom_msg"))
                                    if ok:
                                        t["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        t["status"] = "Đang giữ chuỗi • Bạn đã gửi hôm nay! ✅"
                                        bot.save_targets(targets)
                                        st.toast(f"Đã gửi tới @{t['username']}!", icon=":material/check:")
                                        st.rerun()
                                    else:
                                        st.error("Gửi thất bại!")

                    # Cột 4: Menu tác vụ ba chấm gọn gàng (Check, Gửi lại, Đã gửi tay, Hú Hú, Xoá có xác nhận)
                    with col_menu:
                        pop_item = st.popover("⋯", use_container_width=True)
                        with pop_item:
                            st.markdown(f"**Tác vụ: @{t['username']}**")
                            # Check trạng thái
                            if st.button("Kiểm tra chuỗi", key=f"sub_chk_{idx}", use_container_width=True, icon=":material/refresh:"):
                                with st.spinner("Đang kiểm tra..."):
                                    try:
                                        chk_res = bot.run_check_sync(t["username"])
                                        if chk_res.get("checked"):
                                            t["status"] = chk_res.get("status_desc")
                                            if "streak_count" in chk_res:
                                                t["streak_count"] = chk_res["streak_count"]
                                            if chk_res.get("friend_replied"):
                                                t["friend_replied"] = True
                                        bot.save_targets(targets)
                                        st.rerun()
                                    except Exception as ex_c:
                                        st.error(f"Lỗi: {ex_c}")

                            # Đánh dấu đã gửi bằng tay trên điện thoại
                            if st.button("Đã gửi trên điện thoại", key=f"sub_man_{idx}", use_container_width=True, icon=":material/done_all:"):
                                res_m = bot.mark_manual_send(t["username"])
                                if res_m.get("success"):
                                    st.toast(f"Đã ghi nhận gửi tới @{t['username']}!", icon=":material/check:")
                                    st.rerun()

                            # Hú Hú spam nhắc nhở
                            if st.button("Báo động Hú Hú", key=f"sub_hu_{idx}", use_container_width=True, icon=":material/notifications_active:"):
                                custom_spams = t.get("spam_messages")
                                with st.spinner("Đang kích hoạt Hú Hú..."):
                                    result = bot.run_spam_huhu_sync(t["username"], custom_spam_list=custom_spams, max_rounds=8)
                                    sent_num = result.get("sent", 0)
                                    if result.get("replied"):
                                        t["status"] = f"Đã Rep sau {sent_num} tin! 🎉"
                                    else:
                                        t["status"] = f"Đã Hú ({sent_num} tin)"
                                    bot.save_targets(targets)
                                    st.rerun()

                            # Xoá có popover/xác nhận
                            st.divider()
                            del_confirm = st.checkbox("Xác nhận xoá bạn này", key=f"chk_del_confirm_{idx}")
                            if st.button("Xoá khỏi danh sách", key=f"sub_del_{idx}", use_container_width=True, type="secondary", disabled=not del_confirm, icon=":material/delete:"):
                                targets.pop(idx)
                                bot.save_targets(targets)
                                st.toast(f"Đã xoá @{t['username']}", icon=":material/delete:")
                                st.rerun()
        else:
            st.info("Danh sách theo dõi hiện đang trống. Sử dụng nút 'Quét hộp thư' hoặc thêm bạn bè ở bên dưới để bắt đầu.")


# ---------------------------------------------------------------------------
# TAB 1: THU THẬP DỮ LIỆU TIKTOK (CẢI TIẾN TRỰC QUAN & HIỆN LOG CHI TIẾT TRÊN UI)
# ---------------------------------------------------------------------------
with tabs[1]:
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
# TAB 2: THỐNG KÊ & PHÂN TÍCH
# ---------------------------------------------------------------------------
with tabs[2]:
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
        st.info("Chưa có tệp CSV nào trong thư mục data/. Hãy thực hiện cào dữ liệu ở Tab bên cạnh trước!")# ---------------------------------------------------------------------------
# TAB 3: NÂNG CAO (RAW JSON)
# ---------------------------------------------------------------------------
with tabs[3]:
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

