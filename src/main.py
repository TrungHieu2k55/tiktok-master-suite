import sys
from pathlib import Path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Chạy thẳng app.py bất kể Streamlit gọi theo cách nào
import app
