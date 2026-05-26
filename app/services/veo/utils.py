"""VEO 工具函数"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from ...logger import logger


def download_video(
    url: str,
    download_dir: str,
    prefix: str = "veo",
    default_ext: str = ".mp4",
) -> Optional[str]:
    """从远程 URL 下载视频到本地，返回本地文件绝对路径。"""
    target = Path(download_dir)
    target.mkdir(parents=True, exist_ok=True)

    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{default_ext}"
    file_path = target / filename

    try:
        logger.info(f"[VEO/download] 开始下载 | url={url} | dest={file_path}")
        with requests.get(url, timeout=120, stream=True) as resp:
            resp.raise_for_status()
            with open(file_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        logger.info(f"[VEO/download] 下载完成 | {file_path}")
        return str(file_path)
    except Exception as exc:
        logger.error(f"[VEO/download] 下载失败: {exc}")
        return None
