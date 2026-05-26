"""ZYG 渠道 VEO 生成（异步任务型）"""

import mimetypes
import os
import time
import uuid
from typing import Optional

import requests

from ...constants import ApiUrls
from ...logger import logger
from .base import VeoBase, VeoResult
from .utils import download_video

_PENDING_STATUSES = {"queued", "in_progress", "processing", "running"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}
_SIZE_BY_ORIENTATION = {
    "portrait": "720x1280",
    "landscape": "1280x720",
}


class VeoZyg(VeoBase):
    """ZYG VEO 视频生成"""

    @property
    def provider_name(self) -> str:
        return "ZYG API"

    @property
    def base_url(self) -> str:
        return ApiUrls.ZYG

    def generate(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        ref_image_path: Optional[str] = None,
        download_dir: Optional[str] = None,
        **kwargs,
    ) -> VeoResult:
        """生成视频并轮询结果。"""
        del duration  # ZYG 文档未暴露时长参数，当前仅保留接口兼容。

        has_reference = bool(ref_image_path and os.path.isfile(ref_image_path))
        size = str(kwargs.get("size") or _SIZE_BY_ORIENTATION.get(orientation, _SIZE_BY_ORIENTATION["portrait"]))
        model = "veo_3_1-fast-fl" if has_reference else "veo_3_1-fast"

        task_id = self._submit_task(
            prompt=prompt,
            model=model,
            size=size,
            ref_image_path=ref_image_path if has_reference else None,
        )
        if not task_id:
            return VeoResult(success=False, error_message="任务提交失败")

        result = self._poll_task(task_id)
        if not result or not result.success:
            return result or VeoResult(success=False, error_message="任务轮询失败")

        if result.video_url and download_dir:
            result.file_path = download_video(result.video_url, download_dir, "veo_zyg")
        return result

    def _submit_task(
        self,
        prompt: str,
        model: str,
        size: str,
        ref_image_path: Optional[str] = None,
    ) -> Optional[str]:
        url = f"{self.base_url.rstrip('/')}/v1/videos"
        body, content_type = self._build_multipart_body(
            fields=[
                ("model", model),
                ("prompt", prompt),
                ("size", size),
            ],
            ref_image_path=ref_image_path,
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": content_type,
        }
        try:
            logger.info(
                f"[{self.provider_name}] VEO 请求 | model={model} | "
                f"模式={'图生视频' if ref_image_path else '文生视频'} | size={size} | POST {url}"
            )
            logger.info(
                f"[{self.provider_name}] 提交策略=manual_multipart_utf8 | "
                f"body_type={type(body).__name__} | body_len={len(body)} | "
                f"content_type={content_type}"
            )

            response = requests.post(url, headers=headers, data=body, timeout=120)
            logger.info(f"[{self.provider_name}] 响应状态码: {response.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {response.text[:500]}")
            response.raise_for_status()

            data = response.json()
            task_id = data.get("id") or data.get("task_id")
            if not task_id:
                logger.error(f"[{self.provider_name}] 响应中未找到任务 ID")
                return None
            return task_id
        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 任务提交超时")
            return None
        except requests.exceptions.HTTPError as exc:
            error_message = self._extract_error_message(exc.response)
            logger.error(f"[{self.provider_name}] 任务提交 HTTP 异常: {error_message}")
            return None
        except Exception as exc:
            logger.exception(f"[{self.provider_name}] 任务提交异常 traceback")
            logger.error(f"[{self.provider_name}] 任务提交异常: {exc}")
            return None

    @staticmethod
    def _encode_form_value(value: object) -> bytes:
        return str(value or "").encode("utf-8")

    @classmethod
    def _build_multipart_body(
        cls,
        fields: list[tuple[str, object]],
        ref_image_path: Optional[str] = None,
    ) -> tuple[bytes, str]:
        boundary = f"glin-{uuid.uuid4().hex}"
        body = bytearray()

        for name, value in fields:
            body.extend(f"--{boundary}\r\n".encode("ascii"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n'.encode("ascii"))
            body.extend(b"Content-Type: text/plain; charset=utf-8\r\n\r\n")
            body.extend(cls._encode_form_value(value))
            body.extend(b"\r\n")

        if ref_image_path and os.path.isfile(ref_image_path):
            mime = mimetypes.guess_type(ref_image_path)[0] or "image/jpeg"
            file_name = os.path.basename(ref_image_path)
            with open(ref_image_path, "rb") as file_handle:
                file_bytes = file_handle.read()

            body.extend(f"--{boundary}\r\n".encode("ascii"))
            body.extend(
                (
                    'Content-Disposition: form-data; name="input_reference[]"; '
                    f'filename="{file_name}"\r\n'
                ).encode("utf-8")
            )
            body.extend(f"Content-Type: {mime}\r\n\r\n".encode("ascii"))
            body.extend(file_bytes)
            body.extend(b"\r\n")

        body.extend(f"--{boundary}--\r\n".encode("ascii"))
        return bytes(body), f"multipart/form-data; boundary={boundary}"

    def _poll_task(
        self,
        task_id: str,
        timeout_seconds: int = 600,
        interval_seconds: int = 5,
    ) -> Optional[VeoResult]:
        url = f"{self.base_url.rstrip('/')}/v1/videos/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                logger.info(f"[{self.provider_name}] 轮询状态码: {response.status_code}")
                logger.info(f"[{self.provider_name}] 轮询响应: {response.text[:500]}")
                response.raise_for_status()

                data = response.json()
                status = str(data.get("status") or "").lower()

                if status == "completed":
                    video_url = data.get("url") or data.get("video_url")
                    if video_url:
                        return VeoResult(success=True, video_url=video_url)
                    return VeoResult(success=False, error_message="任务已完成，但未返回视频地址")

                if status in _FAILED_STATUSES:
                    return VeoResult(
                        success=False,
                        error_message=self._extract_error_from_response(data) or "任务执行失败",
                    )

                if status and status not in _PENDING_STATUSES:
                    logger.warning(f"[{self.provider_name}] 未识别状态，继续轮询: {status}")
                time.sleep(interval_seconds)
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.provider_name}] 轮询请求超时，继续重试")
                time.sleep(interval_seconds)
            except Exception as exc:
                logger.error(f"[{self.provider_name}] 轮询异常: {exc}")
                time.sleep(interval_seconds)

        return VeoResult(success=False, error_message="轮询视频结果超时")

    @staticmethod
    def _extract_error_message(response) -> str:
        try:
            body = response.json()
        except Exception:
            return (response.text or "未知错误")[:500]
        return VeoZyg._extract_error_from_response(body)

    @staticmethod
    def _extract_error_from_response(data: dict) -> str:
        if not isinstance(data, dict):
            return str(data or "未知错误")
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("detail") or error)
        if isinstance(error, str) and error:
            return error
        return str(data.get("message") or data.get("msg") or "未知错误")
