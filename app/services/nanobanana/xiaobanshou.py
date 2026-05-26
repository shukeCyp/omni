"""小扳手 NanoBanana 图片生成"""

import base64
import os
import re
import time
from typing import Optional

import requests

from ...logger import logger
from .base import NanoBananaBase, NanoBananaResult

XIAOBANSHOU_NANOBANANA_BASE = "https://xibapi.com"
_PENDING_STATUSES = {"pending", "queued", "processing", "running"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}


class NanoBananaXiaobanshou(NanoBananaBase):
    """小扳手 NanoBanana 图片生成"""

    _SIZE_TO_MODEL = {
        "1K": "nano_banana-pro_1K",
        "2K": "nano_banana-pro_1K",
        "4K": "nano_banana-pro_1K",
    }

    @property
    def provider_name(self) -> str:
        return "小扳手 API"

    @property
    def base_url(self) -> str:
        return XIAOBANSHOU_NANOBANANA_BASE

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        **kwargs,
    ) -> NanoBananaResult:
        # 支持 ref_image_path：从磁盘读取图片并转为 base64
        ref_image_path = kwargs.get("ref_image_path")
        if ref_image_path and os.path.isfile(ref_image_path):
            import mimetypes
            mime = mimetypes.guess_type(ref_image_path)[0] or "image/jpeg"
            with open(ref_image_path, "rb") as _f:
                _b64 = base64.b64encode(_f.read()).decode("ascii")
            existing = list(kwargs.get("ref_images") or [])
            existing.insert(0, {"base64": _b64, "mime": mime})
            kwargs = {**kwargs, "ref_images": existing}

        model = self._SIZE_TO_MODEL.get(image_size, "nano_banana_pro-1K")
        ref_images = self._collect_ref_images(kwargs)
        payload = {
            "model": model,
            "prompt": prompt,
            "metadata": {
                "aspectRatio": aspect_ratio,
            },
        }
        if ref_images:
            payload["metadata"]["urls"] = [self._to_data_url(image) for image in ref_images]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.base_url.rstrip('/')}/v1/videos"

        try:
            logger.info(
                f"[{self.provider_name}] NanoBanana 请求 | POST {url} | "
                f"模式={'图生图' if ref_images else '文生图'} | "
                f"比例={aspect_ratio} | 清晰度={image_size} | model={model}"
            )
            logger.info(
                f"[{self.provider_name}] 请求体: model={model!r}, prompt={prompt[:80]!r}, "
                f"aspectRatio={aspect_ratio!r}, ref_count={len(payload['metadata'].get('urls', []))}"
            )

            response = requests.post(url, headers=headers, json=payload, timeout=120)
            logger.info(f"[{self.provider_name}] 响应状态码: {response.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {response.text[:500]}")
            response.raise_for_status()

            data = response.json()
            direct_result = self._extract_result(data)
            if direct_result:
                return direct_result

            task_id = data.get("id") or data.get("task_id")
            if task_id:
                queried = self._poll_task(task_id)
                if queried:
                    return queried

            return NanoBananaResult(success=False, error_message="未从小扳手返回中提取到图片结果")
        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] NanoBanana 请求超时")
            return NanoBananaResult(success=False, error_message="请求超时，请稍后重试")
        except requests.exceptions.HTTPError as exc:
            error_message = self._read_error_message(exc)
            logger.error(f"[{self.provider_name}] NanoBanana HTTP 异常: {error_message}")
            return NanoBananaResult(success=False, error_message=error_message)
        except Exception as exc:
            logger.error(f"[{self.provider_name}] NanoBanana 生成异常: {exc}")
            return NanoBananaResult(success=False, error_message=f"生成失败: {exc}")

    def _poll_task(self, task_id: str, timeout_seconds: int = 180, interval_seconds: int = 3) -> Optional[NanoBananaResult]:
        url = f"{self.base_url.rstrip('/')}/v1/videos/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            response = requests.get(url, headers=headers, timeout=30)
            logger.info(f"[{self.provider_name}] 轮询状态码: {response.status_code}")
            logger.info(f"[{self.provider_name}] 轮询响应: {response.text[:500]}")
            response.raise_for_status()
            data = response.json()

            result = self._extract_result(data)
            if result:
                return result

            status = str(data.get("status") or "").lower()
            if status in _FAILED_STATUSES:
                return NanoBananaResult(
                    success=False,
                    error_message=self._extract_error_message(data) or "任务执行失败",
                )
            if status and status not in _PENDING_STATUSES:
                logger.warning(f"[{self.provider_name}] 未识别状态，继续轮询: {status}")
            time.sleep(interval_seconds)

        return NanoBananaResult(success=False, error_message="轮询图片结果超时")

    def _extract_result(self, data: dict) -> Optional[NanoBananaResult]:
        image_src = self._extract_image_source(data)
        if not image_src:
            return None

        if image_src.startswith("data:"):
            match = re.match(r"data:(image/[^;]+);base64,(.*)", image_src, re.DOTALL)
            if not match:
                return NanoBananaResult(success=False, error_message="无法解析 data URL")
            return NanoBananaResult(
                success=True,
                mime_type=match.group(1),
                image_data=match.group(2).replace("\n", "").replace(" ", "").replace("\r", ""),
            )

        if image_src.startswith("http"):
            response = requests.get(image_src, timeout=60)
            response.raise_for_status()
            mime_type = (response.headers.get("Content-Type") or "image/png").split(";")[0].strip()
            return NanoBananaResult(
                success=True,
                mime_type=mime_type,
                image_data=base64.b64encode(response.content).decode("ascii"),
            )

        return None

    def _extract_image_source(self, data) -> Optional[str]:
        if isinstance(data, str):
            if data.startswith("http") or data.startswith("data:image/"):
                return data
            markdown_match = re.search(r'!\[.*?\]\((.*?)\)', data, re.DOTALL)
            if markdown_match:
                return markdown_match.group(1).strip()
            return None

        if isinstance(data, list):
            for item in data:
                found = self._extract_image_source(item)
                if found:
                    return found
            return None

        if not isinstance(data, dict):
            return None

        for key in ("image_url", "url", "output_url", "video_url"):
            value = data.get(key)
            if isinstance(value, str) and (value.startswith("http") or value.startswith("data:image/")):
                return value

        for key in ("b64_json", "image_base64", "image_data"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return f"data:image/png;base64,{value}"

        for key in ("images", "data", "output", "result"):
            value = data.get(key)
            found = self._extract_image_source(value)
            if found:
                return found

        return None

    def _collect_ref_images(self, kwargs: dict) -> list[dict]:
        ref_images = list(kwargs.get("ref_images") or [])
        legacy_ref_image = kwargs.get("ref_image")
        if legacy_ref_image:
            ref_images.append(
                {
                    "base64": legacy_ref_image,
                    "mime": kwargs.get("ref_mime_type", "image/jpeg"),
                }
            )
        return [image for image in ref_images if image.get("base64")]

    @staticmethod
    def _to_data_url(image: dict) -> str:
        mime_type = image.get("mime", "image/jpeg")
        return f"data:{mime_type};base64,{image.get('base64', '')}"

    @staticmethod
    def _extract_error_message(body: dict) -> str:
        if not isinstance(body, dict):
            return ""
        error = body.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("detail") or str(error)
        return body.get("message") or error or body.get("msg") or ""

    def _read_error_message(self, exc: requests.exceptions.HTTPError) -> str:
        try:
            body = exc.response.json()
            return self._extract_error_message(body) or exc.response.text[:500]
        except Exception:
            return (exc.response.text or str(exc))[:500]
