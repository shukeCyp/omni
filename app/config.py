import os
import sys
from pathlib import Path

# 路径配置
if getattr(sys, 'frozen', False):
    # 打包后：数据存放到 APPDATA/Roaming/HetangOmni（Windows）或 ~/Library/Application Support/HetangOmni（macOS）
    _appdata = os.environ.get("APPDATA") or os.path.expanduser("~/Library/Application Support")
    BASE_DIR = Path(_appdata) / "HetangOmni"
    STATIC_DIR = Path(sys._MEIPASS) / "static"
else:
    # 开发环境：项目根目录
    BASE_DIR = Path(__file__).resolve().parent.parent
    STATIC_DIR = BASE_DIR / "static"

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "hetang_omni.db"

# 确保目录存在（parents=True 递归创建父目录）
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 激活密钥
ACTIVATION_SECRET = "HETANG_OMNI_ACTIVATION_DISABLED"
