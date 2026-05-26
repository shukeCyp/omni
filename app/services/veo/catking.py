"""CatKing API (api.catking.top) VEO 视频生成（异步任务型）"""

import base64
import mimetypes
import os
import time
from typing import Optional

import requests

from ...logger import logger
from .base import VeoBase, VeoResult
from .utils import download_video

CATKING_BASE = "https://api.catking.top"

_PENDING_STATUSES = {"queued", "processing"}
_FAILED_STATUSES = {"failed", "cancelled"}


def _guess_mime_type(path):
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "image/jpeg"


class VeoCatking(VeoBase):
    """CatKing VEO 视频生成"""

    @property
    def provider_name(self) -> str:
        return "CatKing"

    @property
    def base_url(self) -> str:
        return self._base_url or CATKING_BASE

    def __init__(self, api_key: str, base_url: str = ""):
        super().__init__(api_key)
        self._base_url = (base_url or "").strip().rstrip("/")

    def generate(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        ref_image_path: Optional[str] = None,
        download_dir: Optional[str] = None,
        **kwargs,
    ) -> VeoResult:
        model = kwargs.get("model") or f"ali-veo-3.1-{orientation}-8s-1080p"

        reference_images = self._build_reference_images(ref_image_path)

        task_id = self._submit_task(model, prompt, reference_images)
        if not task_id:
            return VeoResult(success=False, error_message="任务提交失败")

        result = self._poll_task(task_id)
        if not result or not result.success:
            return result or VeoResult(success=False, error_message="任务轮询失败")

        if result.success and result.video_url and download_dir:
            result.file_path = download_video(result.video_url, download_dir, prefix="veo_catking")

        return result

    def _build_reference_images(self, ref_image_path: Optional[str]) -> list:
        if not ref_image_path or not os.path.isfile(ref_image_path):
            return []

        mime_type = _guess_mime_type(ref_image_path)
        with open(ref_image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        return [f"data:{mime_type};base64,{img_b64}"]

    def _submit_task(self, model: str, prompt: str, reference_images: list) -> Optional[str]:
        url = f"{self.base_url}/v1/videos"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "prompt": prompt}
        if reference_images:
            payload["reference_images"] = reference_images

        has_image = bool(reference_images)
        mode_label = "图生视频" if has_image else "文生视频"
        logger.info(
            f"[{self.provider_name}] VEO 请求 | model={model} | 模式={mode_label} | POST {url}"
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info(f"[{self.provider_name}] 响应状态码: {resp.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {resp.text[:500]}")

            if resp.status_code == 402:
                logger.error(f"[{self.provider_name}] 积分不足")
                return None
            if resp.status_code == 429:
                logger.error(f"[{self.provider_name}] 频率限制")
                return None

            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("id")
            if not task_id:
                logger.error(f"[{self.provider_name}] 响应中未找到 id")
                return None

            logger.info(f"[{self.provider_name}] 任务已提交 | id={task_id}")
            return task_id

        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 任务提交超时")
            return None
        except requests.exceptions.HTTPError as exc:
            error_message = self._extract_error_message(exc.response)
            logger.error(f"[{self.provider_name}] 任务提交 HTTP 异常: {error_message}")
            return None
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 任务提交异常: {exc}")
            return None

    def _poll_task(
        self,
        task_id: str,
        timeout_seconds: int = 600,
        interval_seconds: int = 10,
    ) -> Optional[VeoResult]:
        url = f"{self.base_url}/v1/videos/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                logger.info(f"[{self.provider_name}] 轮询状态码: {resp.status_code}")
                logger.info(f"[{self.provider_name}] 轮询响应: {resp.text[:500]}")
                resp.raise_for_status()

                data = resp.json()
                status = str(data.get("status") or "").lower()

                if status == "completed":
                    logger.info(f"[{self.provider_name}] 任务完成 | id={task_id}")
                    return self._extract_result(data, task_id)

                if status in _FAILED_STATUSES:
                    error_msg = data.get("error") or "任务执行失败"
                    logger.error(f"[{self.provider_name}] 任务失败 | id={task_id} | error={error_msg}")
                    return VeoResult(success=False, error_message=str(error_msg))

                if status not in _PENDING_STATUSES and status != "":
                    logger.warning(f"[{self.provider_name}] 未识别状态: {status}")

                time.sleep(interval_seconds)

            except requests.exceptions.Timeout:
                logger.warning(f"[{self.provider_name}] 轮询请求超时，继续重试")
                time.sleep(interval_seconds)
            except Exception as exc:
                logger.error(f"[{self.provider_name}] 轮询异常: {exc}")
                time.sleep(interval_seconds)

        return VeoResult(success=False, error_message="轮询视频结果超时")

    def _extract_result(self, data: dict, task_id: str) -> VeoResult:
        video_url = data.get("url") or ""
        if video_url:
            logger.info(f"[{self.provider_name}] 成功获取视频 URL: {video_url}")
            return VeoResult(success=True, video_url=video_url)
        logger.error(f"[{self.provider_name}] 完成响应中未找到视频 URL")
        return VeoResult(success=False, error_message="完成响应中未找到视频 URL")

    @staticmethod
    def _extract_error_message(response) -> str:
        try:
            body = response.json()
            error = body.get("error")
            if isinstance(error, dict):
                return error.get("message") or error.get("detail") or str(error)
            return body.get("message") or str(error) or response.text[:500]
        except Exception:
            return response.text[:500] if response.text else str(response)
