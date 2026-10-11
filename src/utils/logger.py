"""
utils/logger.py — cấu hình logging tập trung cho toàn project.

Dùng:
    from src.utils.logger import get_logger
    log = get_logger(__name__)
"""
import logging
import sys
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """
    Trả về logger đã cấu hình.
    - stdout: UTF-8, level INFO
    - file collector.log: UTF-8, level DEBUG
    """
    logger = logging.getLogger(name)

    # Tránh add handler trùng nếu gọi nhiều lần
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")

    # Handler stdout
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    # Fix encoding Windows terminal
    if hasattr(sh.stream, "reconfigure"):
        try:
            sh.stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    logger.addHandler(sh)

    # Handler file
    log_file = Path("collector.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
