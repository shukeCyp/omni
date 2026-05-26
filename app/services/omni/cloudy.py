"""Cloudy/HOLO Omni Flash 视频生成。"""

import base64
import mimetypes
import os
import time
from datetime import datetime

import requests

from ...logger import logger
from ..veo.base import VeoResult

CLOUDY_BASE = "https://gpt.lyvideo.top"
_PENDING_STATUSES = {"queued", "processing"}
_FAILED_STATUSES = {"failed", "cancelled", "error"}
_ASPECT_RATIO_BY_ORIENTATION = {
    "landscape": "16:9",
    "portrait": "9:16",
}
_SUPPORTED_DURATIONS = {4, 6, 8, 10}
_RESOLUTION_SUFFIX = {
    "720P": "",
    "720p": "",
    "720": "",
    "1080P": "_1080p",
    "1080p": "_1080p",
    "1080": "_1080p",
    "4K": "_4k",
    "4k": "_4k",
}
_SUPPORTED_MODES = {"text", "components", "edit"}


class OmniCloudy:
    """Cloudy/HOLO Omni Flash 视频渠道。"""

    def __init__(self, api_key: str, base_url: str = ""):
        self.api_key = api_key
        self.base_url = (base_url or "").strip().rstrip("/") or CLOUDY_BASE

    def generate(
        self,
        prompt: str,
        orientation: str = "portrait",
        duration: int = 10,
        resolution: str = "720P",
        ref_image_paths: list[str] | None = None,
        input_video: str | None = None,
        mode: str = "components",
        download_dir: str | None = None,
    ) -> VeoResult:
        mode = (mode or "components").strip().lower()
        if mode not in _SUPPORTED_MODES:
            return VeoResult(success=False, error_message=f"不支持的 Omni 生成方式: {mode}")

        paths = list(ref_image_paths or [])
        if mode in {"components", "edit"} and len(paths) > 3:
            return VeoResult(success=False, error_message="Omni HOLO 最多支持 3 张参考图")
        if mode == "components" and not paths:
            return VeoResult(success=False, error_message="多参考视频需要 1 至 3 张参考图")
        if mode == "edit" and not (input_video or "").strip():
            return VeoResult(success=False, error_message="视频编辑需要填写源视频 URL")
        if paths and any(not os.path.isfile(path) for path in paths):
            return VeoResult(success=False, error_message="参考图文件不存在")

        duration = int(duration or 10)
        if duration not in _SUPPORTED_DURATIONS:
            duration = 10
        resolution_suffix = _RESOLUTION_SUFFIX.get((resolution or "720P").strip(), "")

        payload = {
            "aspect_ratio": _ASPECT_RATIO_BY_ORIENTATION.get(
                orientation,
                _ASPECT_RATIO_BY_ORIENTATION["portrait"],
            ),
            "prompt": prompt,
        }
        if mode == "text":
            payload["model"] = f"omni_flash_{duration}s{resolution_suffix}"
            payload["messages"] = [{"role": "user", "content": prompt}]
        elif mode == "components":
            payload["model"] = f"omni_flash_components_{duration}s{resolution_suffix}"
            payload["messages"] = [{"role": "user", "content": self._build_content(prompt, paths)}]
        else:
            payload["model"] = f"omni_flash_edit{resolution_suffix}"
            payload["input_video"] = input_video.strip()
            payload["seconds"] = duration
            content = self._build_content(prompt, paths) if paths else prompt
            payload["messages"] = [{"role": "user", "content": content}]

        result = self._submit_and_poll(payload)
        if result.success and result.video_url and download_dir:
            result.file_path = self._download_video(result.video_url, download_dir)
        return result

    def _build_content(self, prompt: str, paths: list[str]) -> list[dict]:
        content = []
        for path in paths:
            mime_type = mimetypes.guess_type(path)[0] or "image/jpeg"
            with open(path, "rb") as handle:
                image_data = base64.b64encode(handle.read()).decode()
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                }
            )
        content.append({"type": "text", "text": prompt})
        return content

    def _submit_and_poll(self, payload: dict) -> VeoResult:
        url = f"{self.base_url}/v1/generate"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        logger.info(
            "[Omni/Cloudy] 提交视频任务 | "
            f"model={payload.get('model')} | POST {url}"
        )
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            logger.info(f"[Omni/Cloudy] 创建响应: {response.status_code} | {response.text[:500]}")
            response.raise_for_status()
            body = response.json()
            task_id = body.get("task_id") or body.get("id")
            if not task_id:
                return VeoResult(success=False, error_message="响应中未找到 task_id")
            return self._poll_task(task_id)
        except requests.exceptions.HTTPError as exc:
            return VeoResult(success=False, error_message=self._extract_http_error(exc.response))
        except Exception as exc:
            logger.error(f"[Omni/Cloudy] 提交视频任务失败: {exc}")
            return VeoResult(success=False, error_message=str(exc))

    def _poll_task(
        self,
        task_id: str,
        timeout_seconds: int = 600,
        interval_seconds: int = 10,
    ) -> VeoResult:
        deadline = time.time() + timeout_seconds
        url = f"{self.base_url}/v1/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        while time.time() < deadline:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                logger.info(f"[Omni/Cloudy] 查询响应: {response.status_code} | {response.text[:500]}")
                response.raise_for_status()
                payload = response.json()
                status = str(payload.get("status") or "").lower()
                if status == "completed":
                    return self._extract_result(payload, task_id)
                if status in _FAILED_STATUSES:
                    return VeoResult(
                        success=False,
                        error_message=str(payload.get("error") or "任务执行失败"),
                    )
                if status not in _PENDING_STATUSES and status:
                    logger.warning(f"[Omni/Cloudy] 未识别状态: {status}")
                time.sleep(interval_seconds)
            except requests.exceptions.Timeout:
                time.sleep(interval_seconds)
            except Exception as exc:
                logger.error(f"[Omni/Cloudy] 轮询失败: {exc}")
                time.sleep(interval_seconds)

        return VeoResult(success=False, error_message="轮询视频结果超时")

    def _extract_result(self, payload: dict, task_id: str) -> VeoResult:
        result = payload.get("result") or {}
        video_url = result.get("url") or result.get("video_url")
        if not video_url:
            file_url = result.get("file_url") or f"/v1/tasks/{task_id}/file"
            video_url = f"{self.base_url}{file_url}" if file_url.startswith("/") else file_url
        return VeoResult(success=True, video_url=video_url)

    def _download_video(self, video_url: str, download_dir: str) -> str | None:
        try:
            os.makedirs(download_dir, exist_ok=True)
            filename = f"omni_cloudy_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.mp4"
            file_path = os.path.join(download_dir, filename)
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with requests.get(video_url, headers=headers, timeout=120, stream=True) as response:
                response.raise_for_status()
                with open(file_path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            handle.write(chunk)
            return file_path
        except Exception as exc:
            logger.error(f"[Omni/Cloudy] 视频下载失败: {exc}")
            return None

    @staticmethod
    def _extract_http_error(response) -> str:
        try:
            body = response.json()
            error = body.get("error")
            if isinstance(error, dict):
                return error.get("message") or error.get("detail") or str(error)
            return body.get("message") or str(error) or response.text[:500]
        except Exception:
            return response.text[:500] if response.text else str(response)
