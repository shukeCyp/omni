"""公用线程池"""

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Callable

from .logger import logger

_pool: Optional[ThreadPoolExecutor] = None


def init_pool(size: int = 10) -> None:
    """初始化线程池"""
    global _pool
    if _pool is not None:
        logger.warning("[ThreadPool] 线程池已存在, 先关闭旧的")
        _pool.shutdown(wait=False)
    _pool = ThreadPoolExecutor(max_workers=size)
    logger.info(f"[ThreadPool] 线程池已初始化, max_workers={size}")


def get_pool() -> Optional[ThreadPoolExecutor]:
    """获取线程池实例"""
    return _pool


def submit_task(fn: Callable, *args, **kwargs) -> Optional[Future]:
    """提交任务到线程池"""
    if _pool is None:
        logger.error("[ThreadPool] 线程池未初始化, 无法提交任务")
        return None
    future = _pool.submit(fn, *args, **kwargs)
    logger.debug(f"[ThreadPool] 已提交任务: {fn.__name__}")
    return future


def shutdown_pool() -> None:
    """关闭线程池"""
    global _pool
    if _pool:
        logger.info("[ThreadPool] 正在关闭线程池...")
        _pool.shutdown(wait=False)
        logger.info("[ThreadPool] 线程池已关闭")
        _pool = None
