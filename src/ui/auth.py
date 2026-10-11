from src.storage.supabase_client import supabase_get, supabase_set
"""
ui/auth.py — Hệ thống Xác thực & Phân quyền Người dùng (RBAC) cho TikTok Master Suite.
Bảo mật nâng cao:
1. Chống Brute-force (khóa tạm nếu nhập sai quá 5 lần).
2. Hỗ trợ cấu hình mật khẩu từ:
   - File lưu trữ riêng: data/auth_config.json (cho phép Admin tự đổi mật khẩu ngay trên UI)
   - Streamlit Secrets: st.secrets["passwords"]["admin"]
   - Biến môi trường: ADMIN_PASSWORD trong file .env
   - Mặc định: admin123
"""
import hashlib
import json
import os
import time
from pathlib import Path
import streamlit as st

AUTH_CONFIG_FILE = Path("data/auth_config.json")
MAX_ATTEMPTS = 5
LOCK_SECONDS = 60


def _hash_pw(password: str) -> str:
    """Băm mật khẩu SHA-256 kèm salt cố định."""
    salt = "tiktok_suite_secure_salt_2026"
    return hashlib.sha256((password.strip() + salt).encode("utf-8")).hexdigest()


def update_admin_password(new_password: str) -> bool:
    """Đổi mật khẩu admin và lưu bền vững vào data/auth_config.json và Supabase."""
    try:
        pw_hash = _hash_pw(new_password)
        AUTH_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if AUTH_CONFIG_FILE.exists():
            try:
                data = json.loads(AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["admin_password_hash"] = pw_hash
        AUTH_CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            supabase_set("admin_password_hash", pw_hash)
        except Exception:
            pass
        return True
    except Exception:
        return False


def get_admin_password_hash() -> str:
    """Lấy hash mật khẩu Admin theo thứ tự ưu tiên."""
    # 0. Kiểm tra Supabase Cloud Database (Bền vững sau redeploy)
    try:
        supa_hash = supabase_get("admin_password_hash")
        if supa_hash and isinstance(supa_hash, str) and len(supa_hash) == 64:
            return supa_hash
    except Exception:
        pass

    # 1. Kiểm tra file cấu hình lưu trên máy
    if AUTH_CONFIG_FILE.exists():
        try:
            data = json.loads(AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
            if "admin_password_hash" in data:
                return data["admin_password_hash"]
        except Exception:
            pass

    # 2. Kiểm tra Streamlit Secrets
    try:
        if hasattr(st, "secrets") and "passwords" in st.secrets:
            if "admin" in st.secrets["passwords"]:
                return _hash_pw(str(st.secrets["passwords"]["admin"]))
    except Exception:
        pass

    # 3. Kiểm tra biến môi trường .env
    env_pw = os.getenv("ADMIN_PASSWORD", "admin123")
    return _hash_pw(env_pw)


def get_guest_password_hash() -> str:
    """Lấy hash mật khẩu Guest."""
    try:
        if hasattr(st, "secrets") and "passwords" in st.secrets:
            if "guest" in st.secrets["passwords"]:
                return _hash_pw(str(st.secrets["passwords"]["guest"]))
    except Exception:
        pass
    env_pw = os.getenv("GUEST_PASSWORD", "guest123")
    return _hash_pw(env_pw)


def get_users_store() -> dict:
    return {
        "admin": {
            "password_hash": get_admin_password_hash(),
            "role": "admin",
            "name": "Quản Trị Viên (Admin)",
        },
        "guest": {
            "password_hash": get_guest_password_hash(),
            "role": "guest",
            "name": "Khách Truy Cập (Guest)",
        },
    }


def get_current_user():
    return st.session_state.get("authenticated_user", None)


def is_authenticated() -> bool:
    return st.session_state.get("is_authenticated", False)


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and user.get("role") == "admin")


def logout():
    st.session_state["is_authenticated"] = False
    st.session_state["authenticated_user"] = None
    st.rerun()


def render_login_screen():
    """Hiển thị màn hình đăng nhập bảo mật có chống brute-force."""
    col1, col2, col3 = st.columns([1, 1.8, 1])

    if "login_failed_attempts" not in st.session_state:
        st.session_state["login_failed_attempts"] = 0
    if "lock_until_time" not in st.session_state:
        st.session_state["lock_until_time"] = 0

    now = time.time()
    is_locked = now < st.session_state["lock_until_time"]

    with col2:
        with st.container(border=True):
            st.markdown("""
            <div style="text-align: center; margin-bottom: 1.2rem;">
                <img src="https://upload.wikimedia.org/wikipedia/en/a/a9/TikTok_logo.svg" width="48" style="margin-bottom: 8px;" />
                <h2 style="margin: 0; font-weight: 800; background: linear-gradient(135deg, #FF0050 0%, #00F2FE 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    TikTok Master Suite
                </h2>
                <p style="color: #94A3B8; font-size: 0.9rem; margin-top: 4px;">Hệ thống bảo vệ đa tầng & xác thực bảo mật</p>
            </div>
            """, unsafe_allow_html=True)

            if is_locked:
                remaining = int(st.session_state["lock_until_time"] - now)
                st.error(f"🚨 Bạn đã nhập sai quá {MAX_ATTEMPTS} lần! Hệ thống tạm khóa trong **{remaining} giây** để chống dò mật khẩu.")
                time.sleep(1)
                st.rerun()
                return

            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập:", placeholder="admin hoặc guest").strip().lower()
                password = st.text_input("Mật khẩu:", type="password", placeholder="Nhập mật khẩu truy cập")
                btn_login = st.form_submit_button("🔐 Đăng Nhập Hệ Thống", width="stretch", type="primary")

                if btn_login:
                    if not username or not password:
                        st.error("❌ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
                    else:
                        users = get_users_store()
                        target_user = users.get(username)
                        input_hash = _hash_pw(password)

                        if target_user and target_user["password_hash"] == input_hash:
                            st.session_state["is_authenticated"] = True
                            st.session_state["login_failed_attempts"] = 0
                            st.session_state["authenticated_user"] = {
                                "username": username,
                                "role": target_user["role"],
                                "name": target_user["name"],
                            }
                            st.toast(f"Đăng nhập thành công với vai trò: {target_user['name']}!", icon="🎉")
                            st.rerun()
                        else:
                            st.session_state["login_failed_attempts"] += 1
                            attempts_left = MAX_ATTEMPTS - st.session_state["login_failed_attempts"]
                            if attempts_left <= 0:
                                st.session_state["lock_until_time"] = time.time() + LOCK_SECONDS
                                st.error("🚨 Nhập sai quá 5 lần. Đã kích hoạt khóa tạm thời!")
                                st.rerun()
                            else:
                                st.error(f"❌ Sai tài khoản hoặc mật khẩu! Còn {attempts_left} lần thử.")

            st.markdown("""
            <div style="margin-top: 1rem; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px; font-size: 0.8rem; color: #64748B;">
                <b>🔑 Lưu ý đăng nhập:</b><br/>
                • Tài khoản <b>admin</b> có toàn quyền quản trị & giữ chuỗi cá nhân.<br/>
                • Tài khoản <b>guest</b> (mật khẩu: <code>guest123</code>) chỉ tra cứu API và phân tích dữ liệu.
            </div>
            """, unsafe_allow_html=True)
