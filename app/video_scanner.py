"""视频任务扫描器 - 后台线程持续扫描待处理任务并交给统一视频生成器。"""

import base64
import mimetypes
import threading
import time
from pathlib import Path

from .api import get_media_download_dir
from .constants import SettingKeys
from .database import (
    get_all_settings,
    get_pending_video_tasks,
    get_processing_video_tasks,
    update_video_task,
)
from .logger import logger
from .services.media_generation import VideoGenerationRequest, media_generation_registry
from .thread_pool import get_pool


def _resolve_task_generator(settings: dict):
    """为旧视频队列选择默认视频生成器。

    该队列历史上只用于 Sora2，因此这里优先遵循设置页中的全局 Sora2 渠道。
    """
    return media_generation_registry.resolve_video_generator(
        settings,
        "sora2",
        settings.get(SettingKeys.SORA2_MODEL, ""),
    )


def _read_ref_images(image_path: str) -> list:
    path = Path((image_path or "").strip())
    if not path.is_file():
        return []

    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    try:
        return [{
            "base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            "mime": mime_type,
        }]
    except Exception as exc:
        logger.warning(f"[Scanner] 读取参考图失败 {path}: {exc}")
        return []


def _build_request(generator, task, settings: dict) -> VideoGenerationRequest:
    if generator.platform == "sora2":
        orientation = settings.get(SettingKeys.SORA2_ORIENTATION, "portrait") or "portrait"
        duration = int(settings.get(SettingKeys.SORA2_DURATION, "10") or 10)
    else:
        orientation = settings.get(SettingKeys.HETANG_VEO_ORIENTATION, "portrait") or "portrait"
        duration = 10

    return VideoGenerationRequest(
        prompt=task.prompt or "",
        ref_images=_read_ref_images(task.image_path or ""),
        orientation=orientation,
        duration=duration,
        download_dir=get_media_download_dir("video"),
    )


def _process_task(task) -> None:
    """处理单个视频任务（带重试）。"""
    task_db_id = task.id
    logger.info(f"[Scanner] 开始处理视频任务 id={task_db_id}")

    try:
        settings = get_all_settings()
        auto_retry = settings.get(SettingKeys.AUTO_RETRY, "false") == "true"
        max_retry = int(settings.get(SettingKeys.VIDEO_MAX_RETRY, "3")) if auto_retry else 0

        generator, platform, provider = _resolve_task_generator(settings)
        if not generator:
            logger.error(f"[Scanner] 未找到视频生成器: {platform}/{provider}")
            update_video_task(task_db_id, status="failed")
            return

        request = _build_request(generator, task, settings)

        attempt = 0
        while attempt <= max_retry:
            if attempt > 0:
                logger.info(f"[Scanner] 视频任务重试 id={task_db_id} | 第 {attempt}/{max_retry} 次重试")

            result = generator.generate(request, settings)
            if result.success and result.video_url:
                update_video_task(
                    task_db_id,
                    status="completed",
                    remote_task_id="",
                    video_url=result.video_url,
                    video_path=result.file_path or "",
                )
                logger.info(
                    f"[Scanner] 任务完成 id={task_db_id} | "
                    f"generator={platform}/{provider} | "
                    f"video_url={result.video_url[:80]}"
                )
                return

            error_message = result.error_message or "视频生成失败"
            logger.error(f"[Scanner] 任务失败 id={task_db_id} | generator={platform}/{provider} | {error_message}")
            attempt += 1
            if attempt <= max_retry:
                time.sleep(5)

        logger.error(f"[Scanner] 视频任务最终失败 id={task_db_id} (已重试 {max_retry} 次)")
        update_video_task(task_db_id, status="failed", remote_task_id="")

    except Exception as exc:
        logger.error(f"[Scanner] 处理任务异常 id={task_db_id}: {type(exc).__name__}: {exc}")
        update_video_task(task_db_id, status="failed", remote_task_id="")


def _resume_processing_tasks() -> None:
    """启动时将处理中任务重置为 pending，交由统一生成器重新处理。"""
    try:
        tasks = get_processing_video_tasks()
        if not tasks:
            logger.info("[Scanner] 无需恢复的处理中任务")
            return

        for task in tasks:
            update_video_task(task.id, status="pending", remote_task_id="")

        logger.info(f"[Scanner] 已将 {len(tasks)} 个处理中任务重置为 pending")
    except Exception as exc:
        logger.error(f"[Scanner] 恢复处理中任务异常: {type(exc).__name__}: {exc}")


def start_scanner() -> None:
    """启动后台扫描线程。"""
    _resume_processing_tasks()

    def _scan_loop():
        logger.info("[Scanner] 视频任务扫描器已启动, 扫描间隔: 5秒")
        scan_count = 0
        while True:
            try:
                scan_count += 1
                tasks = get_pending_video_tasks()
                pool = get_pool()
                if tasks and pool:
                    logger.info(f"[Scanner] 第{scan_count}轮扫描, 发现 {len(tasks)} 个待处理任务")
                    for task in tasks:
                        update_video_task(task.id, status="processing")
                        pool.submit(_process_task, task)
                        logger.info(f"[Scanner] 已提交任务 id={task.id} 到线程池")
                elif scan_count % 60 == 0:
                    logger.debug(f"[Scanner] 第{scan_count}轮扫描, 无待处理任务")
            except Exception as exc:
                logger.error(f"[Scanner] 扫描异常: {type(exc).__name__}: {exc}")

            time.sleep(5)

    t = threading.Thread(target=_scan_loop, daemon=True, name="VideoScanner")
    t.start()
    logger.info("[Scanner] 扫描线程已启动")
