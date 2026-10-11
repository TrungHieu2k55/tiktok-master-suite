import os
import runpy
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Chạy trực tiếp app.py trong đúng ngữ cảnh Streamlit đang gọi
app_file = Path(_root) / "app.py"
runpy.run_path(str(app_file), run_name="__main__")
