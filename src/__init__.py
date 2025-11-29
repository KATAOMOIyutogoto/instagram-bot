"""
Instagram API Bot - メインパッケージ
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加（src/から親ディレクトリを参照）
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
