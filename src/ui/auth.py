"""
ui/auth.py — Hệ thống Xác thực & Phân quyền Người dùng (RBAC) cho TikTok Master Suite.
Hỗ trợ 2 vai trò:
- admin: Toàn quyền truy cập (API Explorer, Giữ chuỗi Streak, Cào dữ liệu, Phân tích).
- guest / member: Chỉ dùng các tính năng công khai (Khám phá API, Phân tích dữ liệu),
                  KHÔNG được can thiệp vào tài khoản giữ chuỗi cá nhân của Admin.

Hỗ trợ lấy cấu hình từ:
1. st.secrets (khi deploy lên Streamlit Cloud)
2. Biến môi trường .env / os.environ
3. Danh sách tài khoản mặc định an toàn
"""
import hashlib
import os
import streamlit as st


def _hash_pw(password: str) -> str:
    """Băm mật khẩu SHA-256 an toàn."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


# Mật khẩu mặc định nếu chưa cấu hình trong .env hay st.secrets:
# admin: admin123
# guest: guest123
DEFAULT_USERS = {
    "admin": {
        "password_hash": _hash_pw(os.getenv("ADMIN_PASSWORD", "admin123")),
        "role": "admin",
        "name": "Quản Trị Viên (Admin)",
    },
    "guest": {
        "password_hash": _hash_pw(os.getenv("GUEST_PASSWORD", "guest123")),
        "role": "guest",
        "name": "Khách Truy Cập (Guest)",
    },
}


def get_current_user():
    """Lấy thông tin người dùng hiện tại từ session state."""
    return st.session_state.get("authenticated_user", None)


def is_authenticated() -> bool:
    """Kiểm tra xem người dùng đã đăng nhập chưa."""
    return st.session_state.get("is_authenticated", False)


def is_admin() -> bool:
    """Kiểm tra quyền Admin."""
    user = get_current_user()
    return bool(user and user.get("role") == "admin")


def logout():
    """Đăng xuất người dùng."""
    st.session_state["is_authenticated"] = False
    st.session_state["authenticated_user"] = None
    st.rerun()


def render_login_screen():
    """Hiển thị màn hình đăng nhập bảo mật hiện đại."""
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.container(border=True):
            st.markdown("""
            <div style="text-align: center; margin-bottom: 1.2rem;">
                <img src="https://upload.wikimedia.org/wikipedia/en/a/a9/TikTok_logo.svg" width="48" style="margin-bottom: 8px;" />
                <h2 style="margin: 0; font-weight: 800; background: linear-gradient(135deg, #FF0050 0%, #00F2FE 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    TikTok Master Suite
                </h2>
                <p style="color: #94A3B8; font-size: 0.9rem; margin-top: 4px;">Hệ thống bảo vệ đa tầng & phân quyền truy cập</p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập:", placeholder="admin hoặc guest").strip().lower()
                password = st.text_input("Mật khẩu:", type="password", placeholder="Nhập mật khẩu truy cập")
                btn_login = st.form_submit_button("🔐 Đăng Nhập Hệ Thống", width="stretch", type="primary")

                if btn_login:
                    if not username or not password:
                        st.error("❌ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
                    else:
                        target_user = DEFAULT_USERS.get(username)
                        input_hash = _hash_pw(password)

                        if target_user and target_user["password_hash"] == input_hash:
                            st.session_state["is_authenticated"] = True
                            st.session_state["authenticated_user"] = {
                                "username": username,
                                "role": target_user["role"],
                                "name": target_user["name"],
                            }
                            st.toast(f"Đăng nhập thành công với vai trò: {target_user['name']}!", icon="🎉")
                            st.rerun()
                        else:
                            st.error("❌ Sai tài khoản hoặc mật khẩu! Vui lòng thử lại.")

            st.markdown("""
            <div style="margin-top: 1rem; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px; font-size: 0.8rem; color: #64748B;">
                <b>🔑 Thông tin tài khoản mặc định:</b><br/>
                • <b>admin</b> / <code>admin123</code>: Toàn quyền truy cập & giữ chuỗi.<br/>
                • <b>guest</b> / <code>guest123</code>: Xem & tra cứu API, phân tích dữ liệu.
            </div>
            """, unsafe_allow_html=True)
