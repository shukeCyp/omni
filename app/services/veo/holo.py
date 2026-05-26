"""HOLO API (api.dealonhorizon.us) VEO 视频生成（异步任务型）"""

import base64
import mimetypes
import os
import time
from typing import Optional

import requests

from ...logger import logger
from .base import VeoBase, VeoResult
from .utils import download_video

HOLO_BASE = "https://api.dealonhorizon.us"

_PENDING_STATUSES = {"queued", "processing"}
_FAILED_STATUSES = {"failed", "cancelled"}


def _guess_mime_type(path):
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "image/jpeg"


class VeoHolo(VeoBase):
    """HOLO VEO 视频生成"""

    @property
    def provider_name(self) -> str:
        return "HOLO"

    @property
    def base_url(self) -> str:
        return self._base_url or HOLO_BASE

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
        mode = "i2v" if (ref_image_path and os.path.isfile(ref_image_path)) else "t2v"
        tier = kwargs.get("tier", "fast")
        model = kwargs.get("model") or f"veo_3_1_{mode}_{tier}_{orientation}"

        messages = self._build_messages(prompt, ref_image_path)

        task_id = self._submit_task(model, messages)
        if not task_id:
            return VeoResult(success=False, error_message="任务提交失败")

        result = self._poll_task(task_id)
        if not result or not result.success:
            return result or VeoResult(success=False, error_message="任务轮询失败")

        if result.success and result.video_url and download_dir:
            result.file_path = self._download_video(result.video_url, download_dir)

        return result

    def _build_messages(self, prompt: str, ref_image_path: Optional[str]) -> list:
        if not ref_image_path or not os.path.isfile(ref_image_path):
            return [{"role": "user", "content": prompt}]

        mime_type = _guess_mime_type(ref_image_path)
        with open(ref_image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        return [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}},
                {"type": "text", "text": prompt},
            ],
        }]

    def _submit_task(self, model: str, messages: list) -> Optional[str]:
        url = f"{self.base_url}/v1/generate"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}

        has_image = isinstance(messages[0].get("content"), list)
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
            task_id = data.get("task_id")
            if not task_id:
                logger.error(f"[{self.provider_name}] 响应中未找到 task_id")
                return None

            logger.info(f"[{self.provider_name}] 任务已提交 | task_id={task_id}")
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
        url = f"{self.base_url}/v1/tasks/{task_id}"
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
                    logger.info(f"[{self.provider_name}] 任务完成 | task_id={task_id}")
                    return self._extract_result(data, task_id)

                if status in _FAILED_STATUSES:
                    error_msg = data.get("error") or "任务执行失败"
                    logger.error(f"[{self.provider_name}] 任务失败 | task_id={task_id} | error={error_msg}")
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
        result = data.get("result", {})
        file_url = result.get("file_url") or f"/v1/tasks/{task_id}/file"
        video_url = f"{self.base_url}{file_url}"
        logger.info(f"[{self.provider_name}] 成功获取视频 URL: {video_url}")
        return VeoResult(success=True, video_url=video_url)

    def _download_video(self, video_url: str, download_dir: str) -> Optional[str]:
        """下载视频（带认证头）"""
        try:
            os.makedirs(download_dir, exist_ok=True)
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(video_url, headers=headers, timeout=120, stream=True)
            resp.raise_for_status()

            from datetime import datetime

            filename = f"veo_holo_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.mp4"
            file_path = os.path.join(download_dir, filename)
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"[{self.provider_name}] 视频已下载: {file_path}")
            return file_path
        except Exception as exc:
            logger.error(f"[{self.provider_name}] 视频下载失败: {exc}")
            return None

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
