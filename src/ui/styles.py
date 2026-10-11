"""
ui/styles.py — CSS tập trung và đồng bộ cho toàn bộ giao diện TikTok Suite Master.
Thiết kế chuẩn Modern Dark Theme, căn lề 1.5rem, chuẩn typography, badge trạng thái và nút bấm.
"""
import streamlit as st


def inject_css():
    """Nhúng toàn bộ CSS tuỳ biến cho ứng dụng."""
    st.markdown("""
<style>
    /* 1. Giảm padding-top của .block-container còn 1.5rem */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    /* 2. Tiêu đề trang gọn gàng, cân đối */
    .hero-banner {
        margin-bottom: 1rem;
    }
    .hero-title {
        background: linear-gradient(135deg, #FF0050 0%, #00F2FE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1.2;
        margin: 0;
    }
    .hero-desc {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 0.25rem;
        margin-bottom: 0;
    }

    /* 3. Metric Containers đồng bộ chiều cao và padding */
    div[data-testid="stMetric"] {
        padding: 0 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        color: #94A3B8 !important;
    }

    /* Chip trạng thái metric cột 4 */
    .metric-status-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 4px;
    }

    /* 4. Badges trạng thái cho danh sách bạn bè */
    .status-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
        white-space: nowrap;
        text-align: center;
        line-height: 1.2;
    }
    .badge-success {
        background-color: rgba(34, 197, 94, 0.16);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.35);
    }
    .badge-warning {
        background-color: rgba(234, 179, 8, 0.16);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.35);
    }
    .badge-danger {
        background-color: rgba(239, 68, 68, 0.16);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }

    /* 5. Hàng tiêu đề cột trong bảng */
    .table-col-header {
        color: #94A3B8;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0.2rem 0.2rem;
    }

    /* 6. Sidebar tinh chỉnh */
    [data-testid="stSidebar"] {
        padding-top: 1rem !important;
    }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.25rem;
    }
    .sidebar-brand-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #F8FAFC;
        line-height: 1.2;
    }

    /* 7. Nút bấm không bị xuống dòng */
    button[data-testid="stBaseButton-secondary"],
    button[data-testid="stBaseButton-primary"] {
        white-space: nowrap !important;
    }

    /* 8. Spacing đồng đều giữa các khối */
    .block-gap {
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)
