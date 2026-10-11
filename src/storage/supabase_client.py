"""
storage/supabase_client.py — Kết nối Supabase REST API để lưu trữ dữ liệu bền vững (Persistent Cloud Storage).
Không phụ thuộc SDK nặng, dùng PostgREST trực tiếp qua `requests`.
"""
import json
import os
from pathlib import Path
from typing import Any, Optional
import requests

from src.utils.logger import get_logger

log = get_logger(__name__)

SUPABASE_CONFIG_FILE = Path("data/supabase_config.json")


def get_supabase_config() -> tuple[str, str]:
    """
    Lấy Supabase URL và Supabase Anon Key theo thứ tự ưu tiên:
    1. Streamlit Secrets: st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    2. File cấu hình local: data/supabase_config.json
    3. Biến môi trường: SUPABASE_URL, SUPABASE_KEY
    """
    # 1. Streamlit Secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "supabase" in st.secrets:
                cfg = st.secrets["supabase"]
                u = str(cfg.get("url", "")).strip()
                k = str(cfg.get("key", "")).strip()
                if u and k:
                    return u, k
            u = str(st.secrets.get("SUPABASE_URL", "")).strip()
            k = str(st.secrets.get("SUPABASE_KEY", "")).strip()
            if u and k:
                return u, k
    except Exception:
        pass

    # 2. File cấu hình local
    if SUPABASE_CONFIG_FILE.exists():
        try:
            data = json.loads(SUPABASE_CONFIG_FILE.read_text(encoding="utf-8"))
            u = str(data.get("url", "")).strip()
            k = str(data.get("key", "")).strip()
            if u and k:
                return u, k
        except Exception as e:
            log.warning("Lỗi đọc supabase_config.json: %s", e)

    # 3. Biến môi trường
    u = os.getenv("SUPABASE_URL", "").strip()
    k = os.getenv("SUPABASE_KEY", "").strip()
    if u and k:
        return u, k

    # 4. Dự phòng mặc định của dự án
    default_u = "https://khjergeqkpcudoziibbr.supabase.co"
    default_k = "sb_publishable_mwjS6y7d8KVBQU-_80MGXg_UjaOFEuG"
    return default_u, default_k


def save_supabase_config(url: str, key: str) -> bool:
    """Lưu URL và Key vào data/supabase_config.json để dùng lại."""
    try:
        SUPABASE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"url": url.strip(), "key": key.strip()}
        SUPABASE_CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        log.error("Lỗi ghi supabase_config.json: %s", e)
        return False


def is_supabase_configured() -> bool:
    u, k = get_supabase_config()
    return bool(u and k)


def test_supabase_connection() -> tuple[bool, str]:
    """Kiểm tra kết nối tới Supabase và bảng tiktok_suite_storage."""
    u, k = get_supabase_config()
    if not u or not k:
        return False, "Chưa cấu hình Supabase URL hoặc Key"

    url = u.rstrip("/") + "/rest/v1/tiktok_suite_storage?limit=1"
    headers = {
        "apikey": k,
        "Authorization": f"Bearer {k}",
    }
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200:
            return True, "Kết nối thành công tới Supabase! 🟢"
        elif r.status_code == 404 or "relation" in r.text or "does not exist" in r.text:
            return False, "Đã kết nối Supabase nhưng chưa tạo bảng 'tiktok_suite_storage' trong SQL Editor."
        else:
            return False, f"Lỗi phản hồi HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, f"Lỗi kết nối tới Supabase: {e}"


def supabase_get(key: str, default: Any = None) -> Any:
    """Đọc dữ liệu từ Supabase Cloud Table theo key."""
    u, k = get_supabase_config()
    if not u or not k:
        return default

    url = f"{u.rstrip('/')}/rest/v1/tiktok_suite_storage?key=eq.{key}&select=value"
    headers = {
        "apikey": k,
        "Authorization": f"Bearer {k}",
    }
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            rows = r.json()
            if rows and isinstance(rows, list) and len(rows) > 0:
                return rows[0].get("value", default)
    except Exception as e:
        log.debug("Lỗi đọc Supabase key '%s': %s", key, e)
    return default


def supabase_set(key: str, value: Any) -> bool:
    """Lưu/Upsert dữ liệu lên Supabase Cloud Table theo key."""
    u, k = get_supabase_config()
    if not u or not k:
        return False

    url = f"{u.rstrip('/')}/rest/v1/tiktok_suite_storage"
    headers = {
        "apikey": k,
        "Authorization": f"Bearer {k}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = {
        "key": key,
        "value": value,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=5)
        if r.status_code in [200, 201, 204]:
            log.info("☁️ Đã đồng bộ key '%s' lên Supabase thành công!", key)
            return True
        else:
            log.warning("Supabase set thất bại [%d]: %s", r.status_code, r.text[:120])
            return False
    except Exception as e:
        log.warning("Lỗi ghi Supabase key '%s': %s", key, e)
        return False