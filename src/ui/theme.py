"""
src/ui/theme.py — Hệ thống Design System SaaS tối giản cho TikTok Suite Master.
Tuân thủ bảng màu chuẩn, typography phân cấp, viền mảnh 1px, responsive 1366x768 & 1920x1080.
"""
import streamlit as st


def inject_css():
    """Nhúng toàn bộ CSS Design System SaaS tối giản cho ứng dụng."""
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* 1. Global Reset & Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #0f1115 !important;
        color: #f3f4f6 !important;
    }

    /* 2. Container Padding chuẩn hóa */
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    /* 3. Header SaaS tối giản */
    .saas-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 0 1.25rem 0;
        margin-bottom: 0.75rem;
        border-bottom: 1px solid #262b36;
    }
    .saas-header-left {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .saas-header-title {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #f9fafb !important;
        letter-spacing: -0.02em;
        margin: 0 !important;
        line-height: 1.2 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .saas-header-desc {
        font-size: 13px !important;
        color: #9aa3b2 !important;
        margin: 0 !important;
    }

    /* 4. Thẻ Metrics SaaS */
    div[data-testid="stMetric"] {
        background: transparent !important;
        padding: 0 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #9aa3b2 !important;
        text-transform: none !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 700 !important;
        color: #f9fafb !important;
        letter-spacing: -0.02em;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 12px !important;
        font-weight: 500 !important;
    }

    /* 5. Khung Thẻ Container (Cards) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #171a21 !important;
        border: 1px solid #262b36 !important;
        border-radius: 12px !important;
        transition: border-color 0.15s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #323846 !important;
    }

    /* 6. Chips & Status Badges Chuẩn Màu 3 Trạng Thái */
    .status-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        line-height: 1.2;
        white-space: nowrap;
    }
    .chip-success {
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.28);
    }
    .chip-warning {
        background: rgba(245, 158, 11, 0.12);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.28);
    }
    .chip-danger {
        background: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.28);
    }
    .chip-neutral {
        background: rgba(154, 163, 178, 0.12);
        color: #9aa3b2;
        border: 1px solid rgba(154, 163, 178, 0.24);
    }

    /* Chấm trạng thái tròn nhỏ */
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-success { background-color: #10b981; }
    .dot-warning { background-color: #f59e0b; }
    .dot-danger { background-color: #ef4444; }
    .dot-neutral { background-color: #9aa3b2; }

    /* 7. Nút Bấm & Button Styling */
    button[data-testid="stBaseButton-primary"] {
        background-color: #fe2c55 !important;
        border: 1px solid #fe2c55 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.15s ease !important;
    }
    button[data-testid="stBaseButton-primary"]:hover {
        background-color: #e0264b !important;
        border-color: #e0264b !important;
    }
    button[data-testid="stBaseButton-secondary"] {
        background-color: transparent !important;
        border: 1px solid #262b36 !important;
        color: #f3f4f6 !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 0.45rem 0.85rem !important;
        transition: all 0.15s ease !important;
    }
    button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #1f232c !important;
        border-color: #3c4454 !important;
        color: #ffffff !important;
    }

    /* 8. Tabs Gọn Gàng */
    button[data-baseweb="tab"] {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #9aa3b2 !important;
        padding-top: 10px !important;
        padding-bottom: 12px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        font-weight: 600 !important;
        border-bottom-color: #fe2c55 !important;
    }

    /* 9. Sidebar Gọn Gàng & Chuyên Nghiệp */
    [data-testid="stSidebar"] {
        background-color: #0d0f13 !important;
        border-right: 1px solid #262b36 !important;
        padding-top: 1rem !important;
    }
    .sidebar-brand-box {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.25rem 0 0.75rem 0;
        margin-bottom: 0.5rem;
    }
    .sidebar-brand-name {
        font-size: 16px;
        font-weight: 700;
        color: #f9fafb;
        letter-spacing: -0.01em;
    }
    .sidebar-brand-ver {
        font-size: 11px;
        color: #9aa3b2;
    }
    .sidebar-section-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        margin: 1rem 0 0.5rem 0;
    }

    /* Dòng trạng thái kết nối có chấm tròn */
    .connection-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 0;
        font-size: 13px;
        color: #e5e7eb;
    }
    .connection-status {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #9aa3b2;
    }

    /* 10. Bảng thẻ hàng bạn bè (Friend Card Row) */
    .friend-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
    }
    .friend-name {
        font-size: 14px;
        font-weight: 600;
        color: #f9fafb;
    }
    .friend-username {
        font-size: 13px;
        color: #9aa3b2;
        margin-left: 6px;
    }
    .friend-meta {
        font-size: 13px;
        color: #9aa3b2;
        margin-top: 3px;
    }

    /* Responsive: Không thanh cuộn ngang */
    * {
        box-sizing: border-box;
    }
</style>
""", unsafe_allow_html=True)
