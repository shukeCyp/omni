"""云雾 API Sora2 生成"""

from typing import List, Optional

import requests

from ...constants import ApiUrls
from ...logger import logger
from .base import Sora2Base, Sora2Task, Sora2TaskStatus

# 云雾 Sora2 接口固定地址
YUNWU_VIDEO_BASE = "https://yunwu.ai"


class Sora2Yunwu(Sora2Base):
    """云雾 API Sora2 生成"""

    @property
    def provider_name(self) -> str:
        return "云雾 API"

    @property
    def base_url(self) -> str:
        return ApiUrls.YUNWU

    def upload_image(self, image_data: bytes, filename: str = "image.png") -> Optional[str]:
        """
        上传图片到云雾图床

        Args:
            image_data: 图片二进制数据
            filename: 文件名

        Returns:
            图片链接，失败返回 None
        """
        # 固定地址，不要修改
        url = "https://imageproxy.zhongzhuan.chat/api/upload"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        files = {
            "file": (filename, image_data),
        }

        try:
            logger.info(f"[{self.provider_name}] 图床上传 | POST {url} | {filename} | {len(image_data)} bytes")
            logger.info(f"[{self.provider_name}] 请求头: {headers}")

            resp = requests.post(url, headers=headers, files=files, timeout=60)
            logger.info(f"[{self.provider_name}] 图床响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 图床响应体: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

            image_url = data.get("data", {}).get("url") or data.get("url") or data.get("data")

            if image_url and isinstance(image_url, str):
                logger.info(f"[{self.provider_name}] 图床上传成功: {image_url}")
                return image_url

            logger.error(f"[{self.provider_name}] 图床上传返回异常: {data}")
            return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"[{self.provider_name}] 图床上传失败 | {e.response.status_code} | {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"[{self.provider_name}] 图床上传异常 | {type(e).__name__}: {e}")
            return None

    def create_task(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        **kwargs
    ) -> Sora2Task:
        """
        创建 Sora2 视频生成任务

        云雾接口直接接受 orientation / duration 参数，无需映射模型名。
        如果传入 image_path，会先上传到图床获取 URL，再以图生视频模式创建任务。

        Args:
            prompt:      视频描述提示词
            orientation: 方向，"portrait"（竖屏）或 "landscape"（横屏）
            duration:    视频时长（秒），通常 10 / 15
            **kwargs:
                image_path: 本地图片路径，传入后自动上传图床
                size:       尺寸 large / small，默认 large
                watermark:  是否水印，默认 False
        """
        image_path: Optional[str] = kwargs.get("image_path")
        size: str = kwargs.get("size", "large")
        watermark = kwargs.get("watermark", False)

        # 如果有图片路径，先上传到图床
        images: List[str] = []
        if image_path:
            import os
            if not os.path.isfile(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")

            filename = os.path.basename(image_path)
            with open(image_path, "rb") as f:
                image_data = f.read()

            logger.info(f"[{self.provider_name}] Sora2 图生视频 | 上传图片: {filename}")
            image_url = self.upload_image(image_data, filename=filename)
            if not image_url:
                raise RuntimeError("图片上传图床失败，无法创建图生视频任务")
            images.append(image_url)

        # 云雾用 model 区分文生/图生，不需要编码时长/方向
        model: str = "sora-2-all" if images else "sora-2"

        url = f"{YUNWU_VIDEO_BASE}/v1/video/create"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "images": images,
            "model": model,
            "orientation": orientation,
            "prompt": prompt,
            "size": size,
            "duration": duration,
            "watermark": watermark,
            "private": True,
        }

        try:
            mode = "图生视频" if images else "文生视频"
            logger.info(
                f"[{self.provider_name}] Sora2 创建任务 | POST {url} | {mode} | "
                f"model={model} | orientation={orientation} | duration={duration}s"
            )
            logger.info(f"[{self.provider_name}] 请求头: {headers}")
            logger.info(f"[{self.provider_name}] 请求体: {payload}")

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("id", "")
            status_str = data.get("status", "pending")

            logger.info(f"[{self.provider_name}] Sora2 任务已创建 | task_id={task_id} | status={status_str}")

            return Sora2Task(
                task_id=task_id,
                status=self._parse_status(status_str),
                prompt=prompt,
            )

        except requests.exceptions.HTTPError as e:
            logger.error(f"[{self.provider_name}] Sora2 创建失败 | {e.response.status_code} | {e.response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"[{self.provider_name}] Sora2 创建异常 | {type(e).__name__}: {e}")
            raise

    def query_task(self, task_id: str) -> Sora2Task:
        """
        查询 Sora2 任务状态

        Args:
            task_id: 任务ID
        """
        url = f"{YUNWU_VIDEO_BASE}/v1/video/query"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        params = {
            "id": task_id,
        }

        try:
            logger.info(f"[{self.provider_name}] Sora2 查询任务 | GET {url} | task_id={task_id}")

            resp = requests.get(url, headers=headers, params=params, timeout=30)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

            status_str = data.get("status", "pending")
            video_url = data.get("video_url")
            enhanced_prompt = data.get("enhanced_prompt", "")

            logger.info(
                f"[{self.provider_name}] Sora2 任务状态 | task_id={task_id} | "
                f"status={status_str} | video_url={'有' if video_url else '无'}"
            )

            return Sora2Task(
                task_id=data.get("id", task_id),
                status=self._parse_status(status_str),
                prompt=enhanced_prompt,
                video_url=video_url,
            )

        except requests.exceptions.HTTPError as e:
            logger.error(f"[{self.provider_name}] Sora2 查询失败 | {e.response.status_code} | {e.response.text[:500]}")
            raise
        except Exception as e:
            if self.is_transient_query_exception(e):
                logger.warning(f"[{self.provider_name}] Sora2 查询网络异常，跳过本次轮询 | {task_id} | {type(e).__name__}: {e}")
                return self.build_transient_query_task(task_id, e)
            logger.error(f"[{self.provider_name}] Sora2 查询异常 | {type(e).__name__}: {e}")
            raise

    @staticmethod
    def _parse_status(status_str: str) -> Sora2TaskStatus:
        """将 API 返回的状态字符串解析为枚举"""
        status_map = {
            "pending": Sora2TaskStatus.PENDING,
            "processing": Sora2TaskStatus.PROCESSING,
            "completed": Sora2TaskStatus.COMPLETED,
            "failed": Sora2TaskStatus.FAILED,
        }
        return status_map.get(status_str, Sora2TaskStatus.PENDING)
