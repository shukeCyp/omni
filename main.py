import os
import platform
import sys

import webview

from app import Api, logger
from app.config import STATIC_DIR, DB_PATH, LOGS_DIR
from app.database import init_db, get_setting
from app.thread_pool import init_pool


def _on_closed():
    """窗口关闭回调：强制终止进程，避免后台线程阻塞退出"""
    logger.info("窗口已关闭, 强制退出进程")
    os._exit(0)


def main() -> None:
    # 初始化数据库
    init_db()

    logger.info("=" * 50)
    logger.info("荷塘omni 启动")
    logger.info(f"Python: {sys.version}")
    logger.info(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    logger.info(f"数据库: {DB_PATH}")
    logger.info(f"日志目录: {LOGS_DIR}")
    logger.info("=" * 50)

    # 初始化线程池
    pool_size = int(get_setting("thread_pool_size") or "10")
    logger.info(f"线程池大小配置: {pool_size}")
    init_pool(pool_size)

    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        logger.error(f"前端资源不存在: {index_path}")
        raise FileNotFoundError(
            "static/index.html not found. Run `npm run build` in frontend first."
        )

    logger.info(f"加载前端页面: {index_path}")

    api = Api()
    window = webview.create_window(
        "荷塘omni",
        index_path.as_uri(),
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
    )
    window.events.closed += _on_closed
    logger.info("窗口已创建, 启动 webview...")
    webview.start()
    logger.info("荷塘omni 已退出")


if __name__ == "__main__":
    main()
