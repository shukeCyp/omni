"""小扳手 GPT-image-2 图片生成（/v1/videos 异步接口）"""

import base64
import os
import re
import time
from typing import Optional

import requests

from ...constants import ApiUrls
from ...logger import logger
from ..nanobanana.base import NanoBananaResult

_PENDING_STATUSES = {"pending", "queued", "in_progress", "processing", "running"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}

_RATIO_TO_SIZE = {
    "1:1": "1024x1024",
    "16:9": "1920x1080",
    "4:3": "1920x1080",
    "9:16": "1080x1920",
    "3:4": "1080x1920",
}

_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class GptImageXiaobanshou:
    """小扳手 gpt-image-2 图片生成"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "小扳手 GPT 图片"

    @property
    def base_url(self) -> str:
        return ApiUrls.XIAOBANSHOU_VEO

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        image_size: str = "1K",
        **kwargs,
    ) -> NanoBananaResult:
        ref_images = self._collect_ref_images(kwargs)
        download_dir = kwargs.get("download_dir")
        urls = [self._to_image_value(image) for image in ref_images[:5]]

        payload = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "metadata": {
                "size": self._resolve_size(aspect_ratio),
                "urls": urls,
            },
        }

        result = self._submit(payload)
        if result and result.success and result.image_data and download_dir:
            result.file_path = self._save_to_dir(
                result.image_data,
                result.mime_type or "image/png",
                str(download_dir),
            )
        return result or NanoBananaResult(success=False, error_message="未从小扳手 GPT 图片返回中提取到结果")

    def _submit(self, payload: dict) -> Optional[NanoBananaResult]:
        url = f"{self.base_url.rstrip('/')}/v1/videos"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        ref_count = len(payload.get("metadata", {}).get("urls", []))
        mode = f"图生图({ref_count}张)" if ref_count else "文生图"

        try:
            logger.info(
                f"[{self.provider_name}] 请求 | POST {url} | "
                f"model={payload.get('model')} | size={payload.get('metadata', {}).get('size')} | 模式={mode}"
            )
            response = requests.post(url, headers=headers, json=payload, timeout=300)
            logger.info(f"[{self.provider_name}] 响应状态码: {response.status_code}")
            logger.info(f"[{self.provider_name}] 响应体: {response.text[:500]}")
            response.raise_for_status()
            data = response.json()

            direct_result = self._extract_result(data)
            if direct_result:
                return direct_result

            task_id = data.get("id") or data.get("task_id")
            if task_id:
                return self._poll_task(str(task_id))
            return None
        except requests.exceptions.HTTPError as exc:
            error_message = self._extract_http_error(exc)
            logger.error(f"[{self.provider_name}] HTTP 异常: {error_message}")
            return NanoBananaResult(success=False, error_message=error_message)
        except requests.exceptions.Timeout:
            logger.error(f"[{self.provider_name}] 请求超时")
            return NanoBananaResult(success=False, error_message="请求超时，请稍后重试")
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 生成异常: {exc}")
            return NanoBananaResult(success=False, error_message=f"生成失败: {exc}")

    def _poll_task(self, task_id: str, timeout_seconds: int = 300, interval_seconds: int = 5) -> NanoBananaResult:
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
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.provider_name}] 轮询请求超时，继续重试")
                time.sleep(interval_seconds)
            except requests.exceptions.HTTPError as exc:
                logger.error(f"[{self.provider_name}] 轮询 HTTP 异常: {self._extract_http_error(exc)}")
                time.sleep(interval_seconds)
            except Exception as exc:
                logger.error(f"[{self.provider_name}] 轮询异常: {exc}")
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
                image_data=match.group(2).replace("\n", "").replace("\r", "").replace(" ", ""),
            )

        if image_src.startswith("http"):
            try:
                response = requests.get(image_src, timeout=60)
                response.raise_for_status()
                mime_type = (response.headers.get("Content-Type") or "image/png").split(";")[0].strip()
                return NanoBananaResult(
                    success=True,
                    mime_type=mime_type,
                    image_data=base64.b64encode(response.content).decode("ascii"),
                )
            except Exception as exc:
                return NanoBananaResult(success=False, error_message=f"下载图片失败: {exc}")

        return None

    def _extract_image_source(self, data) -> Optional[str]:
        if isinstance(data, str):
            if data.startswith("http") or data.startswith("data:image/"):
                return data
            markdown_match = re.search(r"!\[.*?\]\((.*?)\)", data, re.DOTALL)
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

        for key in ("b64_json", "image_base64", "image_data"):
            value = data.get(key)
            if isinstance(value, str) and value:
                if value.startswith("data:image/"):
                    return value
                return f"data:image/png;base64,{value}"

        for key in ("url", "image_url", "output_url", "video_url"):
            value = data.get(key)
            if isinstance(value, str) and (value.startswith("http") or value.startswith("data:image/")):
                return value

        for key in ("data", "images", "output", "result"):
            found = self._extract_image_source(data.get(key))
            if found:
                return found

        return None

    def _to_image_value(self, image: dict) -> str:
        image_url = image.get("url") or image.get("image_url")
        if image_url:
            return str(image_url)
        return self._to_data_url(image)

    @staticmethod
    def _to_data_url(image: dict) -> str:
        mime_type = image.get("mime", "image/jpeg")
        return f"data:{mime_type};base64,{image.get('base64', '')}"

    @staticmethod
    def _collect_ref_images(kwargs: dict) -> list[dict]:
        ref_images = list(kwargs.get("ref_images") or [])
        legacy = kwargs.get("ref_image")
        if legacy:
            ref_images.append(
                {"base64": legacy, "mime": kwargs.get("ref_mime_type", "image/jpeg")}
            )
        return [
            image for image in ref_images
            if image.get("base64") or image.get("url") or image.get("image_url")
        ]

    @staticmethod
    def _resolve_size(aspect_ratio: str) -> str:
        return _RATIO_TO_SIZE.get(aspect_ratio, "1024x1792")

    @staticmethod
    def _extract_error_message(body: dict) -> str:
        if not isinstance(body, dict):
            return ""
        error = body.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("detail") or str(error)
        return body.get("message") or body.get("msg") or str(error or "")

    def _extract_http_error(self, exc: requests.exceptions.HTTPError) -> str:
        try:
            return self._extract_error_message(exc.response.json()) or exc.response.text[:500]
        except Exception:
            return (getattr(exc.response, "text", "") or str(exc))[:500]

    @staticmethod
    def _save_to_dir(image_data: str, mime_type: str, download_dir: str) -> str:
        os.makedirs(download_dir, exist_ok=True)
        ext = _MIME_TO_EXT.get(mime_type, ".png")

        from datetime import datetime
        import uuid

        filename = f"gpt_image_xbs_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
        file_path = os.path.join(download_dir, filename)
        raw = base64.b64decode(image_data)
        with open(file_path, "wb") as handle:
            handle.write(raw)
        logger.info(f"[小扳手 GPT 图片] 图片已保存: {file_path} ({len(raw)} bytes)")
        return file_path
