import logging
from datetime import datetime

from .config import LOGS_DIR

# 日志文件名按启动时间命名
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"
log_path = LOGS_DIR / log_filename

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 创建 logger
logger = logging.getLogger("hetang_omni")
logger.setLevel(logging.DEBUG)

# 文件 handler: DEBUG 及以上全部写入
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

# 控制台 handler: INFO 及以上输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 防止日志向上传播导致重复输出
logger.propagate = False
